from __future__ import annotations

import asyncio
import fnmatch
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

AgentRunStatus = Literal["success", "failed", "timeout"]
AgentRunMode = Literal["read_only", "write", "test_only"]


@dataclass(frozen=True)
class AgentExecutionSpec:
    """Execution request for a single Synto agent backed by OpenCode."""

    run_id: str
    agent_id: str
    task_id: str
    task_prompt: str
    workdir: Path
    context_markdown: str
    opencode_agent: str = "build"
    model: str | None = None
    mode: AgentRunMode = "write"
    timeout_seconds: int = 900
    allowed_paths: tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class AgentRunResult:
    """Verified result of an OpenCode-backed agent execution."""

    run_id: str
    agent_id: str
    task_id: str
    status: AgentRunStatus
    exit_code: int | None
    files_changed: tuple[str, ...]
    stdout_path: Path
    stderr_path: Path
    events_path: Path
    patch_path: Path | None
    summary: str


class OpenCodeSessionRunner:
    """Run bounded OpenCode sessions and verify their filesystem effects."""

    def __init__(self, opencode_bin: str | None = None) -> None:
        self.opencode_bin = opencode_bin or self._resolve_opencode_bin()

    def run(self, spec: AgentExecutionSpec) -> AgentRunResult:
        workdir = Path(spec.workdir)
        run_root = workdir / ".synto" / "runs" / spec.run_id
        context_path = run_root / "context" / f"{spec.agent_id}.md"
        output_dir = run_root / "opencode" / spec.agent_id
        patch_dir = run_root / "patches"
        stdout_path = output_dir / "stdout.txt"
        stderr_path = output_dir / "stderr.txt"
        events_path = output_dir / "events.jsonl"

        context_path.parent.mkdir(parents=True, exist_ok=True)
        output_dir.mkdir(parents=True, exist_ok=True)
        patch_dir.mkdir(parents=True, exist_ok=True)
        context_path.write_text(spec.context_markdown, encoding="utf-8")

        before_files = set(_parse_git_status_files(self._git_status(workdir)))
        cmd = self._build_command(spec, context_path)

        try:
            completed = subprocess.run(
                cmd,
                cwd=workdir,
                capture_output=True,
                text=True,
                timeout=spec.timeout_seconds,
            )
        except subprocess.TimeoutExpired as exc:
            stdout = self._safe_text(exc.output)
            stderr = self._safe_text(exc.stderr)
            stdout_path.write_text(stdout, encoding="utf-8")
            stderr_path.write_text(stderr, encoding="utf-8")
            events_path.write_text(stdout, encoding="utf-8")
            return AgentRunResult(
                run_id=spec.run_id,
                agent_id=spec.agent_id,
                task_id=spec.task_id,
                status="timeout",
                exit_code=None,
                files_changed=(),
                stdout_path=stdout_path,
                stderr_path=stderr_path,
                events_path=events_path,
                patch_path=None,
                summary=f"OpenCode session timed out after {spec.timeout_seconds}s.",
            )

        stdout = completed.stdout or ""
        stderr = completed.stderr or ""
        stdout_path.write_text(stdout, encoding="utf-8")
        stderr_path.write_text(stderr, encoding="utf-8")
        events_path.write_text(stdout, encoding="utf-8")

        after_status = self._git_status(workdir)
        after_files = _parse_git_status_files(after_status)
        files_changed = tuple(path for path in after_files if path not in before_files)
        patch_path = self._write_patch_if_needed(workdir, patch_dir, spec.agent_id, files_changed)

        status: AgentRunStatus = "success" if completed.returncode == 0 else "failed"
        summary = self._default_summary(completed.returncode, stdout, stderr)

        guard_failure = self._validate_mode_constraints(spec, files_changed)
        if guard_failure:
            status = "failed"
            summary = guard_failure

        return AgentRunResult(
            run_id=spec.run_id,
            agent_id=spec.agent_id,
            task_id=spec.task_id,
            status=status,
            exit_code=completed.returncode,
            files_changed=files_changed,
            stdout_path=stdout_path,
            stderr_path=stderr_path,
            events_path=events_path,
            patch_path=patch_path,
            summary=summary,
        )

    async def run_async(self, spec: AgentExecutionSpec) -> AgentRunResult:
        return await asyncio.to_thread(self.run, spec)

    def _build_command(self, spec: AgentExecutionSpec, context_path: Path) -> list[str]:
        cmd = [
            self.opencode_bin,
            "run",
            "--format",
            "json",
            "--agent",
            spec.opencode_agent,
            "--title",
            f"synto:{spec.run_id}:{spec.agent_id}:{spec.task_id}",
            "-f",
            str(context_path),
            "--dir",
            str(Path(spec.workdir)),
        ]
        if spec.model:
            cmd.extend(["--model", spec.model])
        cmd.append(spec.task_prompt)
        return cmd

    def _git_status(self, workdir: Path) -> str:
        completed = subprocess.run(
            ["git", "status", "--short"],
            cwd=workdir,
            capture_output=True,
            text=True,
            timeout=30,
        )
        return completed.stdout or ""

    def _write_patch_if_needed(
        self,
        workdir: Path,
        patch_dir: Path,
        agent_id: str,
        files_changed: tuple[str, ...],
    ) -> Path | None:
        if not files_changed:
            return None
        cmd = ["git", "diff", "--binary", "--", *files_changed]
        completed = subprocess.run(
            cmd,
            cwd=workdir,
            capture_output=True,
            text=True,
            timeout=30,
        )
        patch_path = patch_dir / f"{agent_id}.patch"
        patch_path.write_text(completed.stdout or "", encoding="utf-8")
        return patch_path

    def _validate_mode_constraints(
        self,
        spec: AgentExecutionSpec,
        files_changed: tuple[str, ...],
    ) -> str | None:
        if spec.mode == "read_only" and files_changed:
            return "Read-only mode changed files; refusing to mark session successful."

        if spec.mode == "test_only":
            production_files = [path for path in files_changed if not _is_test_path(path)]
            if production_files:
                return (
                    "Test-only mode changed production files; refusing to mark "
                    f"session successful: {', '.join(production_files)}"
                )

        if spec.allowed_paths:
            outside_scope = [
                path for path in files_changed if not _matches_any_allowed_path(path, spec.allowed_paths)
            ]
            if outside_scope:
                return (
                    "Files changed outside allowed paths; refusing to mark "
                    f"session successful: {', '.join(outside_scope)}"
                )

        return None

    def _default_summary(self, exit_code: int, stdout: str, stderr: str) -> str:
        if exit_code == 0:
            return _first_non_empty_line(stdout) or "OpenCode session completed successfully."
        return _first_non_empty_line(stderr) or _first_non_empty_line(stdout) or "OpenCode session failed."

    def _resolve_opencode_bin(self) -> str:
        pinned = Path.home() / ".opencode" / "bin" / "opencode"
        return str(pinned) if pinned.exists() else "opencode"

    def _safe_text(self, value: bytes | str | None) -> str:
        if value is None:
            return ""
        if isinstance(value, bytes):
            return value.decode("utf-8", errors="replace")
        return value


def _parse_git_status_files(status_output: str) -> tuple[str, ...]:
    files: list[str] = []
    for raw_line in status_output.splitlines():
        line = raw_line.rstrip()
        if not line:
            continue
        if len(line) >= 3 and line[2] == " ":
            # Standard porcelain: two status columns plus a separator.
            path = line[3:]
        else:
            # Tolerate compact test fixtures or human-style short status: "M path".
            parts = line.split(maxsplit=1)
            path = parts[1] if len(parts) == 2 else parts[0]
        if " -> " in path:
            path = path.split(" -> ", 1)[1]
        files.append(path.strip())
    return tuple(files)


def _is_test_path(path: str) -> bool:
    normalized = path.replace("\\", "/")
    name = normalized.rsplit("/", 1)[-1]
    return (
        normalized.startswith("tests/")
        or normalized.startswith("test/")
        or "/tests/" in normalized
        or "/test/" in normalized
        or "/__tests__/" in normalized
        or name.startswith("test_")
        or ".test." in name
        or ".spec." in name
        or name in {"pytest.ini", "playwright.config.ts", "vitest.config.ts", "jest.config.js"}
    )


def _matches_any_allowed_path(path: str, patterns: tuple[str, ...]) -> bool:
    normalized = path.replace("\\", "/")
    return any(_matches_allowed_path(normalized, pattern) for pattern in patterns)


def _matches_allowed_path(path: str, pattern: str) -> bool:
    normalized_pattern = pattern.replace("\\", "/")
    if normalized_pattern.endswith("/**"):
        prefix = normalized_pattern[:-3].rstrip("/")
        return path == prefix or path.startswith(f"{prefix}/")
    return fnmatch.fnmatch(path, normalized_pattern)


def _first_non_empty_line(text: str) -> str:
    for line in text.splitlines():
        if line.strip():
            return line.strip()
    return ""
