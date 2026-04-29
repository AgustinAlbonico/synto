"""FastAPI app for the Synto local-first Command Center."""

from __future__ import annotations

import asyncio
import json
import os
import re
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

from fastapi import Body, FastAPI, HTTPException, Query
from fastapi.responses import FileResponse, HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from langgraph.types import Command
from pydantic import BaseModel, Field

from synto.mcp.memory_tools import MemoryToolLayer
from synto.memory import MemoryStore
from synto.memory.obsidian_export import export_to_obsidian
from synto.registry import AgentRegistry, SkillRegistry
from synto.workflows import build_initial_state, get_compiled
from synto.workflows.orchestrator import DEFAULT_REGISTRY_PATH

REPO_ROOT = Path(__file__).resolve().parents[3]
STATIC_DIR = Path(__file__).resolve().parent / "static"


def _slugify(value: str) -> str:
    value = value.strip().lower()
    value = re.sub(r"[^a-z0-9._-]+", "-", value)
    value = re.sub(r"-+", "-", value)
    return value.strip("-") or "default"


@dataclass(slots=True)
class WebConfig:
    """Local-first paths used by the web/API process."""

    workspace_dir: Path
    projects_root: Path
    memory_db_path: Path
    registry_path: Path
    config_dir: Path | None = None
    skills_dirs: tuple[Path, ...] = ()

    @classmethod
    def from_env(
        cls,
        *,
        workspace_dir: str | Path | None = None,
        projects_root: str | Path | None = None,
        memory_db_path: str | Path | None = None,
        registry_path: str | Path | None = None,
        config_dir: str | Path | None = None,
        skills_dirs: Iterable[str | Path] | None = None,
    ) -> "WebConfig":
        workspace = Path(
            workspace_dir
            or os.getenv("SYNTO_WORKSPACE_DIR")
            or Path.cwd()
        ).resolve()
        projects = Path(
            projects_root
            or os.getenv("SYNTO_PROJECTS_ROOT")
            or workspace / ".synto-state" / "projects"
        ).resolve()
        memory_db = Path(
            memory_db_path
            or os.getenv("SYNTO_MEMORY_DB")
            or workspace / "memory_store.db"
        ).resolve()
        registry = Path(
            registry_path
            or os.getenv("SYNTO_AGENT_REGISTRY")
            or DEFAULT_REGISTRY_PATH
        ).resolve()
        cfg_dir = config_dir or os.getenv("SYNTO_CONFIG_DIR") or ""
        resolved_cfg = Path(cfg_dir).resolve() if cfg_dir else None
        raw_skill_dirs = list(skills_dirs or [])
        if not raw_skill_dirs:
            env_dirs = os.getenv("SYNTO_SKILLS_DIRS", "")
            if env_dirs:
                raw_skill_dirs.extend(env_dirs.split(os.pathsep))
            raw_skill_dirs.extend([
                Path.home() / ".hermes" / "skills",
                workspace / "skills",
            ])
        return cls(
            workspace_dir=workspace,
            projects_root=projects,
            memory_db_path=memory_db,
            registry_path=registry,
            config_dir=resolved_cfg,
            skills_dirs=tuple(Path(p).resolve() for p in raw_skill_dirs if str(p)),
        )

    def state_root_for(self, project_id: str) -> Path:
        return self.projects_root / _slugify(project_id or "default")


def _read_json(path: Path, default: Any) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def _read_events(state_root: Path, limit: int = 200) -> list[dict[str, Any]]:
    events_path = state_root / "state" / "events.jsonl"
    if not events_path.exists():
        return []
    lines = [line for line in events_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    if limit > 0:
        lines = lines[-limit:]
    events: list[dict[str, Any]] = []
    for idx, line in enumerate(lines):
        try:
            payload = json.loads(line)
        except json.JSONDecodeError:
            payload = {"type": "log", "summary": line}
        payload.setdefault("index", idx)
        events.append(payload)
    return events


def _read_skill_events(state_root: Path, limit: int = 200) -> list[dict[str, Any]]:
    events_path = state_root / "state" / "skill-load-events.jsonl"
    if not events_path.exists():
        return []
    lines = [line for line in events_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    if limit > 0:
        lines = lines[-limit:]
    events: list[dict[str, Any]] = []
    for idx, line in enumerate(lines):
        try:
            payload = json.loads(line)
        except json.JSONDecodeError:
            payload = {"type": "skill_loaded", "summary": line}
        payload.setdefault("index", idx)
        events.append(payload)
    return events


def _run_status(snapshot: dict[str, Any]) -> str:
    approvals = snapshot.get("approvals", {}) or {}
    gates = snapshot.get("gates", {}) or {}
    if any(a.get("status") == "pending" for a in approvals.values() if isinstance(a, dict)):
        return "waiting_approval"
    if any(g.get("status") == "blocked" for g in gates.values() if isinstance(g, dict)):
        return "blocked"
    if snapshot.get("workflow", {}).get("current_phase") == "delivery":
        return "completed"
    if snapshot.get("gate_errors"):
        return "attention"
    return "running"


def _summarize_run(snapshot: dict[str, Any], state_root: Path) -> dict[str, Any]:
    workflow = snapshot.get("workflow", {}) or {}
    slots = snapshot.get("slots", {}) or {}
    artifacts = snapshot.get("artifacts", {}) or {}
    gates = snapshot.get("gates", {}) or {}
    approvals = snapshot.get("approvals", {}) or {}
    pending_approval = next(
        (
            {"id": key, **value}
            for key, value in approvals.items()
            if isinstance(value, dict) and value.get("status") == "pending"
        ),
        None,
    )
    run_id = snapshot.get("run_id") or snapshot.get("thread_id") or state_root.name
    return {
        "run_id": run_id,
        "thread_id": snapshot.get("thread_id", ""),
        "project_id": snapshot.get("project_id") or state_root.name,
        "status": _run_status(snapshot),
        "current_phase": workflow.get("current_phase", ""),
        "completed_count": len(workflow.get("completed_phases", []) or []),
        "pending_count": len(workflow.get("pending_phases", []) or []),
        "slots_count": len(slots),
        "artifacts_count": len(artifacts),
        "gates_count": len(gates),
        "pending_approval": pending_approval,
        "events_count": snapshot.get("events_count", 0),
        "last_event": snapshot.get("last_event"),
        "skill_events_count": snapshot.get("skill_events_count", 0),
        "last_skill_event": snapshot.get("last_skill_event"),
        "last_updated_at": snapshot.get("last_updated_at", ""),
        "state_root": str(state_root),
        "task": (snapshot.get("shared_state", {}) or {}).get("task", ""),
    }


def _candidate_state_files(projects_root: Path) -> list[Path]:
    candidates: list[Path] = []
    direct = projects_root / "state" / "current-state.json"
    if direct.exists():
        candidates.append(direct)
    if projects_root.exists():
        candidates.extend(projects_root.glob("*/state/current-state.json"))
    return sorted(set(candidates), key=lambda p: p.stat().st_mtime, reverse=True)


def _state_root_from_current_state(path: Path) -> Path:
    return path.parent.parent


def _load_snapshots(config: WebConfig) -> list[tuple[Path, dict[str, Any]]]:
    snapshots: list[tuple[Path, dict[str, Any]]] = []
    for state_file in _candidate_state_files(config.projects_root):
        snapshot = _read_json(state_file, {})
        if not isinstance(snapshot, dict):
            continue
        state_root = _state_root_from_current_state(state_file)
        snapshot.setdefault("state_root", str(state_root))
        snapshots.append((state_root, snapshot))
    return snapshots


def _find_run(config: WebConfig, run_id: str) -> tuple[Path, dict[str, Any]]:
    for state_root, snapshot in _load_snapshots(config):
        identifiers = {
            str(snapshot.get("run_id", "")),
            str(snapshot.get("thread_id", "")),
            str(snapshot.get("project_id", "")),
            state_root.name,
        }
        if run_id in identifiers:
            return state_root, snapshot
    raise HTTPException(status_code=404, detail=f"Run '{run_id}' not found")


def _load_registry(config: WebConfig) -> AgentRegistry:
    registry = AgentRegistry(str(config.registry_path))
    registry.load()
    return registry


def _memory_tools(config: WebConfig) -> tuple[MemoryStore, MemoryToolLayer]:
    store = MemoryStore(str(config.memory_db_path))
    return store, MemoryToolLayer(store)


class RunCreateRequest(BaseModel):
    task: str = Field(..., min_length=1)
    project_id: str = "default"
    execution_mode: str = Field("interactive", pattern="^(automatic|interactive)$")
    auto_approve_gates: list[str] = Field(default_factory=lambda: ["discovery_gate"])
    allow_deploy: bool = False
    thread_id: str = ""
    max_retries: int = Field(2, ge=0, le=10)


class ResumeRequest(BaseModel):
    action: str = Field("approve", pattern="^(approve|request_changes|reject)$")
    notes: str = ""


class ApprovalActionRequest(ResumeRequest):
    run_id: str


class MemoryCandidateAction(BaseModel):
    actor: str = "web"
    reason: str = ""


def create_app(config: WebConfig | None = None) -> FastAPI:
    config = config or WebConfig.from_env()
    config.projects_root.mkdir(parents=True, exist_ok=True)
    config.memory_db_path.parent.mkdir(parents=True, exist_ok=True)

    app = FastAPI(
        title="Synto Command Center",
        description="Local-first web UI and API for Synto agent swarms.",
        version="0.1.0",
    )
    app.state.synto_config = config

    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

    @app.get("/", response_class=HTMLResponse)
    def index() -> FileResponse:
        return FileResponse(STATIC_DIR / "index.html")

    @app.get("/api/health")
    def health() -> dict[str, Any]:
        return {
            "ok": True,
            "service": "synto-command-center",
            "workspace_dir": str(config.workspace_dir),
            "projects_root": str(config.projects_root),
            "memory_db_path": str(config.memory_db_path),
            "registry_path": str(config.registry_path),
        }

    @app.get("/api/runs")
    def list_runs() -> dict[str, Any]:
        runs = [_summarize_run(snapshot, root) for root, snapshot in _load_snapshots(config)]
        totals = {
            "total": len(runs),
            "waiting_approval": sum(1 for run in runs if run["status"] == "waiting_approval"),
            "running": sum(1 for run in runs if run["status"] == "running"),
            "completed": sum(1 for run in runs if run["status"] == "completed"),
            "blocked": sum(1 for run in runs if run["status"] == "blocked"),
        }
        return {"runs": runs, "totals": totals}

    @app.post("/api/runs")
    def create_run(payload: RunCreateRequest) -> dict[str, Any]:
        run_id = uuid.uuid4().hex[:12]
        thread_id = payload.thread_id or run_id
        state_root = config.state_root_for(payload.project_id)
        initial_state = build_initial_state(
            payload.task,
            project_id=payload.project_id or "default",
            config_dir=str(config.config_dir or ""),
            registry_path=str(config.registry_path),
            skills_dirs=[str(path) for path in config.skills_dirs],
            state_root=str(state_root),
            memory_db_path=str(config.memory_db_path),
            execution_mode=payload.execution_mode,
            auto_approve_gates=payload.auto_approve_gates,
            allow_deploy=payload.allow_deploy,
            max_retries=payload.max_retries,
            thread_id=thread_id,
        )
        initial_state["run_id"] = run_id
        checkpoint_db = initial_state["checkpoint_db_path"]
        workflow = get_compiled(checkpoint_db)
        result = workflow.invoke(initial_state, config={"configurable": {"thread_id": thread_id}})
        interrupt_payload = None
        if isinstance(result, dict) and result.get("__interrupt__"):
            interrupt_payload = result["__interrupt__"][0].value
        snapshot_path = state_root / "state" / "current-state.json"
        snapshot = _read_json(snapshot_path, result if isinstance(result, dict) else {})
        return {
            "run": _summarize_run(snapshot, state_root),
            "status": "waiting_approval" if interrupt_payload else _run_status(snapshot),
            "interrupt": interrupt_payload,
            "state": snapshot,
        }

    @app.get("/api/runs/{run_id}")
    def get_run(run_id: str) -> dict[str, Any]:
        state_root, snapshot = _find_run(config, run_id)
        return {
            "run": _summarize_run(snapshot, state_root),
            "state": snapshot,
            "events": _read_events(state_root),
            "skill_events": _read_skill_events(state_root),
        }

    @app.get("/api/runs/{run_id}/state")
    def get_run_state(run_id: str) -> dict[str, Any]:
        _, snapshot = _find_run(config, run_id)
        return snapshot

    @app.get("/api/runs/{run_id}/events")
    def get_run_events(run_id: str, limit: int = Query(200, ge=1, le=2000)) -> dict[str, Any]:
        state_root, _ = _find_run(config, run_id)
        return {"events": _read_events(state_root, limit=limit)}

    @app.get("/api/runs/{run_id}/skill-events")
    def get_run_skill_events(run_id: str, limit: int = Query(200, ge=1, le=2000)) -> dict[str, Any]:
        state_root, _ = _find_run(config, run_id)
        return {"events": _read_skill_events(state_root, limit=limit)}

    @app.get("/api/runs/{run_id}/stream")
    async def stream_run(run_id: str) -> StreamingResponse:
        state_root, _ = _find_run(config, run_id)

        async def event_stream():
            events = _read_events(state_root, limit=500)
            for event in events:
                yield f"event: {event.get('type', 'event')}\ndata: {json.dumps(event, ensure_ascii=False)}\n\n"
            yield "event: heartbeat\ndata: {\"ok\": true}\n\n"
            await asyncio.sleep(0)

        return StreamingResponse(event_stream(), media_type="text/event-stream")

    @app.post("/api/runs/{run_id}/resume")
    def resume_run(run_id: str, payload: ResumeRequest) -> dict[str, Any]:
        state_root, snapshot = _find_run(config, run_id)
        checkpoint_db = snapshot.get("checkpoint_db_path") or str(state_root / "state" / "checkpoints.sqlite")
        thread_id = snapshot.get("thread_id") or run_id
        approved = payload.action == "approve"
        workflow = get_compiled(checkpoint_db)
        result = workflow.invoke(
            Command(resume={"approved": approved, "notes": payload.notes or payload.action}),
            config={"configurable": {"thread_id": thread_id}},
        )
        refreshed = _read_json(state_root / "state" / "current-state.json", result if isinstance(result, dict) else {})
        return {
            "run": _summarize_run(refreshed, state_root),
            "state": refreshed,
            "result": result,
        }

    @app.get("/api/runs/{run_id}/artifacts")
    def list_artifacts(run_id: str) -> dict[str, Any]:
        _, snapshot = _find_run(config, run_id)
        artifacts = snapshot.get("artifacts", {}) or {}
        return {
            "artifacts": [
                {"artifact_id": artifact_id, **meta}
                for artifact_id, meta in artifacts.items()
                if isinstance(meta, dict)
            ]
        }

    @app.get("/api/runs/{run_id}/artifacts/{artifact_id}")
    def get_artifact(run_id: str, artifact_id: str) -> dict[str, Any]:
        state_root, snapshot = _find_run(config, run_id)
        artifact = (snapshot.get("artifacts", {}) or {}).get(artifact_id)
        if not artifact:
            raise HTTPException(status_code=404, detail=f"Artifact '{artifact_id}' not found")
        artifact_path = Path(artifact.get("path", "")).resolve()
        allowed_root = state_root.resolve()
        if not artifact_path.exists() or not artifact_path.is_relative_to(allowed_root):
            raise HTTPException(status_code=404, detail="Artifact file not available")
        return {"artifact": {"artifact_id": artifact_id, **artifact}, "content": artifact_path.read_text(encoding="utf-8")}

    @app.get("/api/agents")
    def list_agents() -> dict[str, Any]:
        registry = _load_registry(config)
        agents = registry.get_all()
        phases = registry.raw.get("workflow_phases", [])
        return {
            "agents": [{"id": agent_id, **agent} for agent_id, agent in agents.items()],
            "phases": phases,
            "count": len(agents),
        }

    @app.get("/api/agents/{agent_id}")
    def get_agent(agent_id: str) -> dict[str, Any]:
        agent = _load_registry(config).get_agent(agent_id)
        if not agent:
            raise HTTPException(status_code=404, detail=f"Agent '{agent_id}' not found")
        return {"agent": agent}

    @app.get("/api/skills")
    def list_skills() -> dict[str, Any]:
        registry = SkillRegistry(skills_dirs=[str(p) for p in config.skills_dirs])
        registry.discover()
        skills = []
        for name, meta in registry.get_all_metadata().items():
            item = meta.to_dict()
            item["quarantined"] = registry.is_quarantined(name)
            skills.append(item)
        return {"skills": sorted(skills, key=lambda item: item["name"]), "count": len(skills)}

    @app.get("/api/skills/{skill_name}")
    def get_skill(skill_name: str) -> dict[str, Any]:
        registry = SkillRegistry(skills_dirs=[str(p) for p in config.skills_dirs])
        content = registry.load_skill(skill_name)
        meta = registry.get_metadata(skill_name)
        if content is None or meta is None:
            raise HTTPException(status_code=404, detail=f"Skill '{skill_name}' not found")
        return {"metadata": meta.to_dict(), "content": content, "quarantined": registry.is_quarantined(skill_name)}

    @app.get("/api/memory/stats")
    def memory_stats() -> dict[str, Any]:
        store, tools = _memory_tools(config)
        try:
            return tools.stats()
        finally:
            store.close()

    @app.get("/api/memory/projects")
    def memory_projects() -> dict[str, Any]:
        store, tools = _memory_tools(config)
        try:
            return {"projects": tools.list_projects()}
        finally:
            store.close()

    @app.get("/api/memory/projects/{project_id}/tree")
    def memory_tree(project_id: str) -> dict[str, Any]:
        store, tools = _memory_tools(config)
        try:
            return tools.get_tree(project_id)
        finally:
            store.close()

    @app.get("/api/memory/search")
    def memory_search(
        q: str = Query("", description="Search query"),
        project_id: str = Query(""),
        limit: int = Query(20, ge=1, le=100),
    ) -> dict[str, Any]:
        store, tools = _memory_tools(config)
        try:
            if not q:
                return {"items": []}
            resolved_project = store.get_project(project_id) if project_id else None
            pid = resolved_project["id"] if resolved_project else project_id
            return {"items": tools.search(q, project_id=pid, limit=limit)}
        finally:
            store.close()

    @app.get("/api/memory/candidates")
    def memory_candidates(project_id: str = Query("")) -> dict[str, Any]:
        store, tools = _memory_tools(config)
        try:
            resolved_project = store.get_project(project_id) if project_id else None
            pid = resolved_project["id"] if resolved_project else project_id
            return {"candidates": tools.list_candidates(pid)}
        finally:
            store.close()

    @app.post("/api/memory/candidates/{candidate_id}/approve")
    def approve_candidate(candidate_id: str, payload: MemoryCandidateAction = Body(default_factory=MemoryCandidateAction)) -> dict[str, Any]:
        store, tools = _memory_tools(config)
        try:
            item_id = tools.commit_candidate(candidate_id, actor=payload.actor)
            return {"status": "approved", "item_id": item_id}
        finally:
            store.close()

    @app.post("/api/memory/candidates/{candidate_id}/reject")
    def reject_candidate(candidate_id: str, payload: MemoryCandidateAction = Body(default_factory=MemoryCandidateAction)) -> dict[str, Any]:
        store, tools = _memory_tools(config)
        try:
            tools.reject_candidate(candidate_id, reason=payload.reason, actor=payload.actor)
            return {"status": "rejected", "candidate_id": candidate_id}
        finally:
            store.close()

    @app.post("/api/memory/items/{memory_id}/forget")
    def forget_memory(memory_id: str, payload: MemoryCandidateAction = Body(default_factory=MemoryCandidateAction)) -> dict[str, Any]:
        store, tools = _memory_tools(config)
        try:
            tools.forget(memory_id, actor=payload.actor)
            return {"status": "archived", "memory_id": memory_id}
        finally:
            store.close()

    @app.get("/api/memory/audit")
    def memory_audit(limit: int = Query(50, ge=1, le=500)) -> dict[str, Any]:
        store, tools = _memory_tools(config)
        try:
            return {"events": tools.get_audit_log(limit=limit)}
        finally:
            store.close()

    @app.post("/api/memory/export/obsidian")
    def memory_export(project_id: str = Body("", embed=True), output: str = Body("./obsidian-export", embed=True)) -> dict[str, Any]:
        store, _ = _memory_tools(config)
        try:
            project = store.get_project(project_id) if project_id else None
            pid = project["id"] if project else project_id
            files = export_to_obsidian(store, output, project_id=pid)
            return {"files": files, "count": len(files)}
        finally:
            store.close()

    @app.get("/api/design-system/{project_id}")
    def design_system(project_id: str) -> dict[str, Any]:
        try:
            state_root, snapshot = _find_run(config, project_id)
        except HTTPException:
            state_root = config.state_root_for(project_id)
            snapshot = _read_json(state_root / "state" / "current-state.json", {})
        artifacts = snapshot.get("artifacts", {}) or {}
        for artifact_id in ("design_system", "design-system", "design", "design_system_draft"):
            artifact = artifacts.get(artifact_id)
            if artifact and Path(artifact.get("path", "")).exists():
                return {
                    "project_id": project_id,
                    "artifact_id": artifact_id,
                    "artifact": artifact,
                    "content": Path(artifact["path"]).read_text(encoding="utf-8"),
                }
        return {
            "project_id": project_id,
            "artifact_id": "default",
            "tokens": {
                "color": {"ink": "#1f241f", "paper": "#eee6d1", "copper": "#b86f3c"},
                "radius": {"panel": "18px", "control": "999px"},
                "density": "operational-cockpit",
            },
            "components": [],
            "reviews": [],
        }

    @app.post("/api/approvals/{approval_id}/approve")
    def approve_gate(approval_id: str, payload: ApprovalActionRequest) -> dict[str, Any]:
        if approval_id and payload.notes:
            payload.notes = f"{approval_id}: {payload.notes}"
        return resume_run(payload.run_id, ResumeRequest(action="approve", notes=payload.notes))

    @app.post("/api/approvals/{approval_id}/request-changes")
    def request_gate_changes(approval_id: str, payload: ApprovalActionRequest) -> dict[str, Any]:
        note = payload.notes or f"Changes requested for {approval_id}"
        return resume_run(payload.run_id, ResumeRequest(action="request_changes", notes=note))

    @app.post("/api/approvals/{approval_id}/reject")
    def reject_gate(approval_id: str, payload: ApprovalActionRequest) -> dict[str, Any]:
        note = payload.notes or f"Rejected {approval_id}"
        return resume_run(payload.run_id, ResumeRequest(action="reject", notes=note))

    # ── LLM Provider Configuration ──────────────────────────────────────────

    PROVIDERS_CATALOG: list[dict[str, Any]] = [
        {
            "id": "zen",
            "name": "OpenCode Zen",
            "type": "openai_compat",
            "base_url": "https://opencode.ai/zen/v1",
            "auth_type": "api_key",
            "env_var": "OPENCODE_ZEN_API_KEY",
            "models": [
                {"id": "big-pickle", "name": "Big Pickle", "context_window": 131072, "tier": "free", "capabilities": ["chat", "completion"]},
                {"id": "glm-4.7-free", "name": "GLM 4.7", "context_window": 131072, "tier": "free", "capabilities": ["chat", "completion"]},
                {"id": "kimi-k2.5-free", "name": "Kimi K2.5", "context_window": 131072, "tier": "free", "capabilities": ["chat", "completion"]},
                {"id": "minimax-m2.1-free", "name": "MiniMax M2.1", "context_window": 131072, "tier": "free", "capabilities": ["chat", "completion"]},
                {"id": "gpt-5-nano", "name": "GPT 5 Nano", "context_window": 128000, "tier": "free", "capabilities": ["chat", "completion"]},
                {"id": "minimax-m2.5", "name": "MiniMax M2.5", "context_window": 131072, "tier": "balanced", "capabilities": ["chat", "completion"]},
                {"id": "glm-5.1", "name": "GLM 5.1", "context_window": 131072, "tier": "premium", "capabilities": ["chat", "completion"]},
            ],
            "signup_url": "https://opencode.ai/",
        },
        {
            "id": "openrouter",
            "name": "OpenRouter",
            "type": "openrouter",
            "base_url": "https://openrouter.ai/api/v1",
            "auth_type": "api_key",
            "env_var": "OPENROUTER_API_KEY",
            "models": [
                {"id": "minimax/minimax-m2.5:free", "name": "MiniMax M2.5 (Free)", "context_window": 131072, "tier": "free", "capabilities": ["chat", "completion"]},
                {"id": "google/gemma-4-31b-it:free", "name": "Gemma 4 31B (Free)", "context_window": 131072, "tier": "free", "capabilities": ["chat", "completion"]},
                {"id": "qwen/qwen3-next-80b-a3b-instruct:free", "name": "Qwen3 Next 80B (Free)", "context_window": 131072, "tier": "free", "capabilities": ["chat", "completion"]},
                {"id": "nvidia/nemotron-3-super-120b-a12b:free", "name": "Nemotron 3 Super 120B (Free)", "context_window": 131072, "tier": "free", "capabilities": ["chat", "completion"]},
                {"id": "minimax/minimax-m2.5", "name": "MiniMax M2.5 (Paid)", "context_window": 131072, "tier": "balanced", "capabilities": ["chat", "completion"]},
            ],
            "signup_url": "https://openrouter.ai/",
        },
        {
            "id": "openai",
            "name": "OpenAI (OAuth)",
            "type": "openai_oauth",
            "base_url": "https://api.openai.com/v1",
            "auth_type": "oauth",
            "env_var": "",
            "auth_file_hint": "~/.local/share/opencode/auth.json",
            "models": [
                {"id": "gpt-5.3-codex", "name": "GPT 5.3 Codex", "context_window": 200000, "tier": "premium", "capabilities": ["chat", "completion", "reasoning"]},
                {"id": "gpt-5.4", "name": "GPT 5.4", "context_window": 1000000, "tier": "premium", "capabilities": ["chat", "completion", "reasoning", "vision"]},
                {"id": "gpt-4o", "name": "GPT-4o", "context_window": 128000, "tier": "balanced", "capabilities": ["chat", "completion", "vision"]},
                {"id": "gpt-4o-mini", "name": "GPT-4o Mini", "context_window": 128000, "tier": "economy", "capabilities": ["chat", "completion"]},
                {"id": "o4-mini", "name": "o4-mini", "context_window": 200000, "tier": "premium", "capabilities": ["chat", "reasoning"]},
            ],
            "signup_url": "",
        },
        {
            "id": "openai_apikey",
            "name": "OpenAI (API Key)",
            "type": "openai_compat",
            "base_url": "https://api.openai.com/v1",
            "auth_type": "api_key",
            "env_var": "OPENAI_API_KEY",
            "models": [
                {"id": "gpt-4o", "name": "GPT-4o", "context_window": 128000, "tier": "balanced", "capabilities": ["chat", "completion", "vision"]},
                {"id": "gpt-4o-mini", "name": "GPT-4o Mini", "context_window": 128000, "tier": "economy", "capabilities": ["chat", "completion"]},
                {"id": "o4-mini", "name": "o4-mini", "context_window": 200000, "tier": "premium", "capabilities": ["chat", "reasoning"]},
            ],
            "signup_url": "https://platform.openai.com/api-keys",
        },
        {
            "id": "ollama",
            "name": "Ollama (Local)",
            "type": "ollama",
            "base_url": "http://localhost:11434",
            "auth_type": "none",
            "env_var": "",
            "models": [
                {"id": "qwen2.5:7b", "name": "Qwen 2.5 7B", "context_window": 32768, "tier": "free", "capabilities": ["chat", "completion"]},
                {"id": "llama3.2:3b", "name": "Llama 3.2 3B", "context_window": 32768, "tier": "free", "capabilities": ["chat", "completion"]},
                {"id": "gemma3:4b", "name": "Gemma 3 4B", "context_window": 8192, "tier": "free", "capabilities": ["chat", "completion"]},
            ],
            "signup_url": "https://ollama.com/",
        },
    ]

    def _mask_key(key: str) -> str:
        if not key:
            return ""
        if len(key) <= 8:
            return key[:2] + "***"
        return key[:6] + "***" + key[-4:]

    def _resolve_env(value: str) -> str:
        """Resolve ${ENV_VAR} patterns in config values."""
        import re
        pattern = re.compile(r"\$\{([^}]+)\}")
        def replacer(m):
            return os.environ.get(m.group(1), "")
        return pattern.sub(replacer, value)

    def _load_providers_yaml() -> dict[str, Any]:
        """Load the providers.yaml file and return its content."""
        config_dir = config.config_dir
        if not config_dir:
            return {}
        providers_path = config_dir / "providers.yaml"
        if not providers_path.exists():
            return {}
        import yaml as _yaml
        return _yaml.safe_load(providers_path.read_text()) or {}

    def _save_providers_yaml(data: dict[str, Any]) -> Path:
        """Save the providers.yaml file."""
        import yaml as _yaml
        config_dir = config.config_dir
        if not config_dir:
            config_dir = REPO_ROOT / "src" / "synto" / "config"
            config_dir.mkdir(parents=True, exist_ok=True)
            config.config_dir = config_dir
        providers_path = config_dir / "providers.yaml"
        providers_path.write_text(_yaml.dump(data, default_flow_style=False, sort_keys=False, allow_unicode=True), encoding="utf-8")
        return providers_path

    @app.get("/api/llm/providers")
    def llm_list_providers() -> dict[str, Any]:
        """List all known LLM providers with their models and config status."""
        providers_yaml = _load_providers_yaml()
        yaml_providers = providers_yaml.get("providers", {})
        env_keys = {
            "OPENCODE_ZEN_API_KEY": os.getenv("OPENCODE_ZEN_API_KEY", ""),
            "OPENROUTER_API_KEY": os.getenv("OPENROUTER_API_KEY", ""),
            "OPENAI_API_KEY": os.getenv("OPENAI_API_KEY", ""),
        }
        result = []
        for catalog in PROVIDERS_CATALOG:
            yaml_cfg = yaml_providers.get(catalog["id"], {})
            api_key = yaml_cfg.get("api_key", "")
            # Resolve env vars
            if api_key.startswith("${") and api_key.endswith("}"):
                env_name = api_key[2:-1]
                api_key = env_keys.get(env_name, os.getenv(env_name, ""))
            configured = bool(api_key)
            if catalog["auth_type"] == "oauth":
                # Check auth.json existence
                auth_paths = [
                    os.path.expanduser("~/.local/share/opencode/auth.json"),
                    "/mnt/c/Users/agust/.local/share/opencode/auth.json",
                    "/mnt/c/Users/agust/.config/opencode/auth.json",
                ]
                configured = any(os.path.exists(p) for p in auth_paths)
            elif catalog["auth_type"] == "none":
                # Ollama: check if running
                import urllib.request
                try:
                    urllib.request.urlopen("http://localhost:11434/api/tags", timeout=2)
                    configured = True
                except Exception:
                    configured = False
            result.append({
                **catalog,
                "configured": configured,
                "api_key_masked": _mask_key(api_key) if api_key else "",
                "api_key_raw": api_key,  # For editing
                "auth_file": yaml_cfg.get("auth_file", yaml_cfg.get("base_url", "")),
            })
        return {"providers": result, "count": len(result)}

    @app.put("/api/llm/providers/{provider_id}")
    def llm_update_provider(provider_id: str, payload: dict[str, Any] = Body(...)) -> dict[str, Any]:
        """Update a provider's configuration (API key, auth file, etc.)."""
        catalog = next((p for p in PROVIDERS_CATALOG if p["id"] == provider_id), None)
        if not catalog:
            raise HTTPException(status_code=404, detail=f"Provider '{provider_id}' not found")
        providers_yaml = _load_providers_yaml()
        providers_yaml.setdefault("providers", {})
        existing = providers_yaml["providers"].get(provider_id, {})
        # Merge with catalog defaults
        existing["type"] = catalog["type"]
        existing["base_url"] = payload.get("base_url", catalog["base_url"])
        if payload.get("api_key") is not None:
            existing["api_key"] = payload["api_key"]
        if payload.get("auth_file") is not None:
            existing["auth_file"] = payload["auth_file"]
        if "models" not in existing or payload.get("models"):
            existing["models"] = catalog["models"]
        providers_yaml["providers"][provider_id] = existing
        saved = _save_providers_yaml(providers_yaml)
        return {"status": "ok", "path": str(saved), "provider": provider_id}

    @app.post("/api/llm/providers/{provider_id}/test")
    def llm_test_provider(provider_id: str) -> dict[str, Any]:
        """Test a provider connection."""
        import urllib.request
        from synto.config.llm_router import LLMMultiProvider, ProviderConfig, OpenAICompatProvider, OpenAIOAuthProvider, OpenRouterProvider
        providers_yaml = _load_providers_yaml()
        yaml_providers = providers_yaml.get("providers", {})
        cfg = yaml_providers.get(provider_id)
        if not cfg:
            catalog = next((p for p in PROVIDERS_CATALOG if p["id"] == provider_id), None)
            if not catalog:
                raise HTTPException(status_code=404, detail=f"Provider '{provider_id}' not found")
            cfg = {"type": catalog["type"], "base_url": catalog["base_url"], "api_key": "", "models": catalog["models"]}
            providers_yaml.setdefault("providers", {})[provider_id] = cfg
            _save_providers_yaml(providers_yaml)
        api_key = _resolve_env(cfg.get("api_key", ""))
        prov_cfg = ProviderConfig(
            name=provider_id,
            provider_type=cfg["type"],
            base_url=_resolve_env(cfg.get("base_url", "")),
            api_key=api_key if api_key else None,
        )
        if cfg["type"] == "openai_oauth":
            provider = OpenAIOAuthProvider(prov_cfg)
        elif cfg["type"] == "openrouter":
            provider = OpenRouterProvider(prov_cfg)
        else:
            provider = OpenAICompatProvider(prov_cfg)
        available = provider.is_available
        return {
            "provider": provider_id,
            "available": available,
            "models_count": len(prov_cfg.models),
        }

    @app.get("/api/llm/models")
    def llm_list_models() -> dict[str, Any]:
        """List all models across all providers."""
        all_models = []
        for catalog in PROVIDERS_CATALOG:
            for m in catalog["models"]:
                all_models.append({
                    "id": m["id"],
                    "name": m["name"],
                    "provider": catalog["id"],
                    "provider_name": catalog["name"],
                    "context_window": m["context_window"],
                    "tier": m["tier"],
                    "capabilities": m["capabilities"],
                })
        return {"models": all_models, "count": len(all_models)}

    @app.get("/api/llm/profiles")
    def llm_list_profiles() -> dict[str, Any]:
        """List agent profiles and their model assignments from models.yaml."""
        config_dir = config.config_dir
        if not config_dir:
            return {"profiles": {}}
        models_path = config_dir / "models.yaml"
        if not models_path.exists():
            return {"profiles": {}}
        import yaml as _yaml
        data = _yaml.safe_load(models_path.read_text()) or {}
        return {"profiles": data}

    @app.put("/api/llm/profiles")
    def llm_update_profile(payload: dict[str, Any] = Body(...)) -> dict[str, Any]:
        """Update agent profile model assignments."""
        import yaml as _yaml
        config_dir = config.config_dir
        if not config_dir:
            config_dir = REPO_ROOT / "src" / "synto" / "config"
            config_dir.mkdir(parents=True, exist_ok=True)
            config.config_dir = config_dir
        models_path = config_dir / "models.yaml"
        models_path.write_text(_yaml.dump(payload, default_flow_style=False, sort_keys=False, allow_unicode=True), encoding="utf-8")
        return {"status": "ok", "path": str(models_path)}

    return app


app = create_app()
