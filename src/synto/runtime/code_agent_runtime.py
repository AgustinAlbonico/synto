from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any, Literal

import yaml

CodeFlowKind = Literal["new_project", "existing_project"]
OpenCodeMode = Literal["read_only", "write", "test_only"]

REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_CODE_AGENT_RUNTIME_PATH = REPO_ROOT / "config" / "code-agent-runtime.yaml"

_CODE_KEYWORDS = {
    "api",
    "app",
    "backend",
    "bug",
    "build",
    "code",
    "component",
    "endpoint",
    "feature",
    "fix",
    "frontend",
    "implement",
    "login",
    "refactor",
    "repo",
    "test",
    "ui",
    "web",
    "arregl",
    "código",
    "codigo",
    "compilar",
    "componente",
    "desarroll",
    "endpoint",
    "feature",
    "frontend",
    "implementar",
    "program",
    "refactor",
    "test",
}

_RESEARCH_KEYWORDS = {
    "apps similares",
    "aplicaciones similares",
    "competidores",
    "investiga",
    "investigar",
    "mercado",
    "research",
    "similar apps",
}

_DEVOPS_KEYWORDS = {
    "cloudflare",
    "deploy",
    "docker",
    "infra",
    "kubernetes",
    "servidor",
}


def load_code_agent_runtime(path: str | Path | None = None) -> dict[str, Any]:
    """Load the Code-domain runtime contract consumed by the workflow."""

    runtime_path = Path(path or DEFAULT_CODE_AGENT_RUNTIME_PATH)
    return _load_code_agent_runtime_cached(str(runtime_path.resolve()))


@lru_cache(maxsize=8)
def _load_code_agent_runtime_cached(path: str) -> dict[str, Any]:
    data = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}
    if not isinstance(data, dict):
        raise ValueError(f"Invalid Code agent runtime contract: {path}")
    return data


def classify_domain(task: str, explicit_domain: str = "") -> str:
    """Classify coarse user intent without calling an LLM.

    The LLM orchestrator can still provide an explicit domain; this fallback keeps
    tests and local runs deterministic.
    """

    explicit = str(explicit_domain or "").strip().lower()
    if explicit:
        return explicit

    text = str(task or "").lower()
    if any(keyword in text for keyword in _RESEARCH_KEYWORDS):
        return "research"
    if any(keyword in text for keyword in _DEVOPS_KEYWORDS) and not any(keyword in text for keyword in _CODE_KEYWORDS):
        return "devops"
    if any(keyword in text for keyword in _CODE_KEYWORDS):
        return "code"
    return "general"


def is_code_domain(domain: str, runtime: dict[str, Any] | None = None) -> bool:
    required = ((runtime or {}).get("activation", {}) or {}).get("domain_required", "code")
    return str(domain or "").strip().lower() == str(required or "code").strip().lower()


def resolve_workspace_root(state: dict[str, Any]) -> Path:
    """Resolve the workspace directory used for OpenCode sessions."""

    paths = state.get("workspace_paths") or []
    if isinstance(paths, (list, tuple)) and paths:
        return Path(str(paths[0])).expanduser().resolve()

    workspace = state.get("workspace") or {}
    if isinstance(workspace, dict):
        workspace_paths = workspace.get("paths") or []
        if isinstance(workspace_paths, (list, tuple)) and workspace_paths:
            return Path(str(workspace_paths[0])).expanduser().resolve()

    workdir = state.get("workdir") or state.get("workspace_dir") or ""
    if workdir:
        return Path(str(workdir)).expanduser().resolve()

    return Path.cwd().resolve()


def select_code_flow_kind(workspace_root: Path, runtime: dict[str, Any] | None = None) -> CodeFlowKind:
    detection_file = ((runtime or {}).get("activation", {}) or {}).get("new_project_detection_file", ".synto/config.yaml")
    return "existing_project" if (workspace_root / str(detection_file)).exists() else "new_project"


def execution_order(runtime: dict[str, Any], flow_kind: CodeFlowKind) -> list[str]:
    raw = ((runtime.get("execution_order", {}) or {}).get(flow_kind, []))
    return [str(agent_id) for agent_id in raw if agent_id]


def agent_runtime_config(runtime: dict[str, Any], agent_id: str) -> dict[str, Any]:
    agents = runtime.get("agents", {}) or {}
    return dict(agents.get(agent_id, {}) or {})


def opencode_mode_for(runtime: dict[str, Any], agent_id: str) -> OpenCodeMode | None:
    raw = str(agent_runtime_config(runtime, agent_id).get("opencode", "none") or "none").strip().lower()
    if raw == "write":
        return "write"
    if raw == "test_only":
        return "test_only"
    if raw in {"readonly", "read_only", "optional_readonly"} or raw.startswith("readonly") or raw.startswith("read_only"):
        return "read_only"
    return None


def allowed_paths_for(runtime: dict[str, Any], agent_id: str, mode: OpenCodeMode) -> tuple[str, ...]:
    config = agent_runtime_config(runtime, agent_id)
    by_mode = config.get("allowed_paths_by_mode", {}) or {}
    paths = by_mode.get(mode, []) or []
    return tuple(str(path) for path in paths)


def opencode_binary(runtime: dict[str, Any]) -> str | None:
    preferences = ((runtime.get("opencode", {}) or {}).get("binary_preference", []) or [])
    for candidate in preferences:
        path = Path(str(candidate)).expanduser()
        if path.is_absolute() and path.exists():
            return str(path)
    for candidate in preferences:
        if str(candidate) == "opencode":
            return "opencode"
    return None


def agents_before_or_equal(runtime: dict[str, Any], flow_kind: CodeFlowKind, target_agent: str) -> list[str]:
    ordered = execution_order(runtime, flow_kind)
    if target_agent not in ordered:
        return [target_agent]
    return ordered[: ordered.index(target_agent) + 1]
