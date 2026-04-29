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

    return app


app = create_app()
