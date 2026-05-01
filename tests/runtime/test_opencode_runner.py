from __future__ import annotations

import subprocess
from pathlib import Path

from synto.runtime.opencode_runner import (
    AgentExecutionSpec,
    OpenCodeSessionRunner,
)


def _completed(cmd, returncode=0, stdout="", stderr=""):
    return subprocess.CompletedProcess(cmd, returncode, stdout, stderr)


def test_builds_opencode_command_with_json_format_title_context_and_dir(
    tmp_path: Path,
    monkeypatch,
):
    calls: list[tuple[list[str], Path | None, int | None]] = []

    def fake_run(cmd, *, cwd=None, capture_output=True, text=True, timeout=None):
        calls.append((list(cmd), cwd, timeout))
        if cmd[:3] == ["git", "status", "--short"]:
            return _completed(cmd, stdout="")
        if cmd[:3] == ["git", "diff", "--binary"]:
            return _completed(cmd, stdout="")
        return _completed(cmd, stdout='{"type":"message"}\n')

    monkeypatch.setattr("synto.runtime.opencode_runner.subprocess.run", fake_run)

    spec = AgentExecutionSpec(
        run_id="run-123",
        agent_id="TDDAgent",
        task_id="TASK-001",
        task_prompt="Write failing tests for login",
        workdir=tmp_path,
        context_markdown="# Context\nUse TDD.",
        opencode_agent="build",
        timeout_seconds=123,
    )

    result = OpenCodeSessionRunner(opencode_bin="opencode").run(spec)

    opencode_call = next(cmd for cmd, _, _ in calls if cmd[:2] == ["opencode", "run"])
    context_path = tmp_path / ".synto/runs/run-123/context/TDDAgent.md"

    assert opencode_call == [
        "opencode",
        "run",
        "--format",
        "json",
        "--agent",
        "build",
        "--title",
        "synto:run-123:TDDAgent:TASK-001",
        "-f",
        str(context_path),
        "--dir",
        str(tmp_path),
        "Write failing tests for login",
    ]
    assert context_path.read_text() == "# Context\nUse TDD."
    assert result.status == "success"
    assert result.stdout_path.exists()
    assert result.stderr_path.exists()
    assert result.events_path.exists()


def test_generates_patch_and_reports_changed_files_when_git_status_changes(
    tmp_path: Path,
    monkeypatch,
):
    status_calls = 0

    def fake_run(cmd, *, cwd=None, capture_output=True, text=True, timeout=None):
        nonlocal status_calls
        if cmd[:3] == ["git", "status", "--short"]:
            status_calls += 1
            stdout = "" if status_calls == 1 else "M src/app.py\n?? tests/test_app.py\n"
            return _completed(cmd, stdout=stdout)
        if cmd[:3] == ["git", "diff", "--binary"]:
            return _completed(cmd, stdout="diff --git a/src/app.py b/src/app.py\n")
        return _completed(cmd, stdout="ok")

    monkeypatch.setattr("synto.runtime.opencode_runner.subprocess.run", fake_run)

    spec = AgentExecutionSpec(
        run_id="run-1",
        agent_id="BackendImplementer",
        task_id="TASK-002",
        task_prompt="Implement endpoint",
        workdir=tmp_path,
        context_markdown="context",
    )

    result = OpenCodeSessionRunner(opencode_bin="opencode").run(spec)

    assert result.status == "success"
    assert result.files_changed == ("src/app.py", "tests/test_app.py")
    assert result.patch_path is not None
    assert result.patch_path.read_text() == "diff --git a/src/app.py b/src/app.py\n"


def test_reports_only_files_changed_after_opencode_not_preexisting_worktree_changes(
    tmp_path: Path,
    monkeypatch,
):
    status_calls = 0

    def fake_run(cmd, *, cwd=None, capture_output=True, text=True, timeout=None):
        nonlocal status_calls
        if cmd[:3] == ["git", "status", "--short"]:
            status_calls += 1
            stdout = "M preexisting.py\n" if status_calls == 1 else "M preexisting.py\nM src/new.py\n"
            return _completed(cmd, stdout=stdout)
        if cmd[:3] == ["git", "diff", "--binary"]:
            return _completed(cmd, stdout="diff --git a/src/new.py b/src/new.py\n")
        return _completed(cmd, stdout="ok")

    monkeypatch.setattr("synto.runtime.opencode_runner.subprocess.run", fake_run)

    spec = AgentExecutionSpec(
        run_id="run-1",
        agent_id="BackendImplementer",
        task_id="TASK-003",
        task_prompt="Implement endpoint",
        workdir=tmp_path,
        context_markdown="context",
    )

    result = OpenCodeSessionRunner(opencode_bin="opencode").run(spec)

    assert result.status == "success"
    assert result.files_changed == ("src/new.py",)


def test_read_only_mode_fails_if_files_change(tmp_path: Path, monkeypatch):
    status_calls = 0

    def fake_run(cmd, *, cwd=None, capture_output=True, text=True, timeout=None):
        nonlocal status_calls
        if cmd[:3] == ["git", "status", "--short"]:
            status_calls += 1
            stdout = "" if status_calls == 1 else "M src/app.py\n"
            return _completed(cmd, stdout=stdout)
        if cmd[:3] == ["git", "diff", "--binary"]:
            return _completed(cmd, stdout="diff")
        return _completed(cmd, stdout="review complete")

    monkeypatch.setattr("synto.runtime.opencode_runner.subprocess.run", fake_run)

    spec = AgentExecutionSpec(
        run_id="run-1",
        agent_id="Reviewer",
        task_id="review",
        task_prompt="Review diff",
        workdir=tmp_path,
        context_markdown="context",
        mode="read_only",
    )

    result = OpenCodeSessionRunner(opencode_bin="opencode").run(spec)

    assert result.status == "failed"
    assert "read-only" in result.summary.lower()
    assert result.files_changed == ("src/app.py",)


def test_test_only_mode_rejects_production_file_changes(tmp_path: Path, monkeypatch):
    status_calls = 0

    def fake_run(cmd, *, cwd=None, capture_output=True, text=True, timeout=None):
        nonlocal status_calls
        if cmd[:3] == ["git", "status", "--short"]:
            status_calls += 1
            stdout = "" if status_calls == 1 else "M tests/test_auth.py\nM src/auth.py\n"
            return _completed(cmd, stdout=stdout)
        if cmd[:3] == ["git", "diff", "--binary"]:
            return _completed(cmd, stdout="diff")
        return _completed(cmd, stdout="tests written")

    monkeypatch.setattr("synto.runtime.opencode_runner.subprocess.run", fake_run)

    spec = AgentExecutionSpec(
        run_id="run-1",
        agent_id="TDDAgent",
        task_id="tdd",
        task_prompt="Write tests",
        workdir=tmp_path,
        context_markdown="context",
        mode="test_only",
    )

    result = OpenCodeSessionRunner(opencode_bin="opencode").run(spec)

    assert result.status == "failed"
    assert "test-only" in result.summary.lower()
    assert result.files_changed == ("tests/test_auth.py", "src/auth.py")


def test_write_mode_rejects_files_outside_allowed_paths(tmp_path: Path, monkeypatch):
    status_calls = 0

    def fake_run(cmd, *, cwd=None, capture_output=True, text=True, timeout=None):
        nonlocal status_calls
        if cmd[:3] == ["git", "status", "--short"]:
            status_calls += 1
            stdout = "" if status_calls == 1 else "M backend/api.py\nM frontend/app.tsx\n"
            return _completed(cmd, stdout=stdout)
        if cmd[:3] == ["git", "diff", "--binary"]:
            return _completed(cmd, stdout="diff")
        return _completed(cmd, stdout="implemented")

    monkeypatch.setattr("synto.runtime.opencode_runner.subprocess.run", fake_run)

    spec = AgentExecutionSpec(
        run_id="run-1",
        agent_id="BackendImplementer",
        task_id="backend",
        task_prompt="Implement backend",
        workdir=tmp_path,
        context_markdown="context",
        mode="write",
        allowed_paths=("backend/**", "tests/backend/**"),
    )

    result = OpenCodeSessionRunner(opencode_bin="opencode").run(spec)

    assert result.status == "failed"
    assert "allowed paths" in result.summary.lower()
    assert result.files_changed == ("backend/api.py", "frontend/app.tsx")


def test_timeout_returns_timeout_status_and_writes_logs(tmp_path: Path, monkeypatch):
    def fake_run(cmd, *, cwd=None, capture_output=True, text=True, timeout=None):
        if cmd[:3] == ["git", "status", "--short"]:
            return _completed(cmd, stdout="")
        if cmd[:2] == ["opencode", "run"]:
            raise subprocess.TimeoutExpired(cmd=cmd, timeout=timeout, output="partial", stderr="slow")
        return _completed(cmd, stdout="")

    monkeypatch.setattr("synto.runtime.opencode_runner.subprocess.run", fake_run)

    spec = AgentExecutionSpec(
        run_id="run-1",
        agent_id="BackendImplementer",
        task_id="timeout",
        task_prompt="Long task",
        workdir=tmp_path,
        context_markdown="context",
        timeout_seconds=1,
    )

    result = OpenCodeSessionRunner(opencode_bin="opencode").run(spec)

    assert result.status == "timeout"
    assert result.exit_code is None
    assert "partial" in result.stdout_path.read_text()
    assert "slow" in result.stderr_path.read_text()
