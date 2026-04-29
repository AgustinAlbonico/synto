"""LangGraph runtime for the Synto multi-agent workflow."""

from __future__ import annotations

import operator
import sqlite3
import uuid
from pathlib import Path
from typing import Annotated, Any, TypedDict

from langgraph.graph import END, StateGraph
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.config import get_config
from langgraph.types import interrupt

from synto.agents import create_all_agents
from synto.config.llm_router import LLMMultiProvider
from synto.memory import (
    MemoryCandidate,
    MemoryContextAgent,
    MemoryKind,
    MemoryManager,
    MemoryStore,
    TaskContext,
)
from synto.registry import AgentRegistry
from synto.state import SharedState, StateStore

REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_REGISTRY_PATH = str(REPO_ROOT / "AGENT-REGISTRY.yaml")
DEFAULT_STATE_DIRNAME = ".synto-state"

_PHASE_ARTIFACT_DIRS = {
    "discovery": "01-discovery",
    "prd": "02-prd",
    "task_graph": "03-spec",
    "spec": "03-spec",
    "design": "04-design",
    "design_system": "04-design",
    "test_plan": "05-tests",
    "backend_summary": "06-implementation",
    "frontend_summary": "06-implementation",
    "contract_report": "07-review",
    "code_review_report": "07-review",
    "security_report": "07-review",
    "test_results": "07-review",
    "qa_report": "08-qa",
    "dependency_report": "08-qa",
    "docs": "08-qa",
    "release_notes": "09-release",
    "deploy_report": "10-deploy",
}

_GATE_REQUIREMENTS = {
    "discovery_gate": ["discovery"],
    "prd_gate": ["prd"],
    "spec_gate": ["spec", "task_graph"],
    "testing_gate": ["test_plan"],
    "contract_gate": ["contract_report"],
    "release_gate": ["release_notes"],
    "deploy_gate": ["release_notes"],
}

_GATE_APPROVAL_LABELS = {
    "discovery": "user_confirms_problem_context",
    "prd": "user_approves_prd",
    "spec_consolidation": "user_approves_spec_when_required",
    "tdd": "test_plan_exists",
    "contract_alignment": "contracts_match",
    "release": "user_approves_release_or_pr",
    "deploy": "user_approves_deploy",
}

_DRAFT_ARTIFACT_ALLOWLIST = {
    "discovery_draft",
    "clarification_questions",
    "prd_draft",
    "task_graph_draft",
    "codebase_map",
    "backend_design_draft",
    "design_system_draft",
    "test_plan_draft",
}

_NODE_TO_PHASE = {
    "intake": "intake",
    "memory_rehydration": "memory_rehydration",
    "discovery": "discovery",
    "discovery_gate": "discovery",
    "prd": "prd",
    "prd_gate": "prd",
    "planning": "technical_planning",
    "spec_gate": "spec_consolidation",
    "testing": "tdd",
    "testing_gate": "tdd",
    "implementation": "implementation",
    "contract_alignment": "contract_alignment",
    "contract_gate": "contract_alignment",
    "review": "review",
    "quality_gate": "qa_docs",
    "release": "release",
    "release_gate": "release",
    "deploy_gate": "deploy",
    "deploy": "deploy",
    "memory_consolidation": "memory_consolidation",
    "delivery": "delivery",
}

_CHECKPOINTER_CONNECTIONS: list[sqlite3.Connection] = []
_ROUTER_CACHE: dict[str, LLMMultiProvider] = {}
_REGISTRY_CACHE: dict[str, AgentRegistry] = {}


class OrchestratorState(TypedDict, total=False):
    task: str
    project_id: str
    config_dir: str
    registry_path: str
    state_root: str
    checkpoint_db_path: str
    memory_db_path: str
    run_id: str
    thread_id: str
    execution_mode: str
    auto_approve_gates: list[str]
    allow_deploy: bool
    max_retries: int
    retry_counts: dict[str, int]
    current_phase: str
    completed_phases: list[str]
    pending_phases: list[str]
    phase_route: str
    gate_passed: bool
    gate_errors: list[str]
    slots: dict[str, Any]
    artifacts: dict[str, Any]
    gates: dict[str, Any]
    approvals: dict[str, Any]
    shared_state_snapshot: dict[str, Any]
    memory_pack_global: dict[str, Any]
    memory_pack_by_agent: dict[str, Any]
    phase_outputs: dict[str, Any]
    discovery_output: str
    prd_output: str
    plan: str
    test_plan: str
    implementation_output: str
    contract_report: str
    test_results: str
    docs_output: str
    release_output: str
    deploy_output: str
    result: str
    events: Annotated[list[dict[str, Any]], operator.add]
    errors: Annotated[list[str], operator.add]


def _default_state_root(project_id: str, memory_db_path: str = "") -> str:
    base_dir = Path(memory_db_path).resolve().parent if memory_db_path else Path.cwd()
    return str(base_dir / DEFAULT_STATE_DIRNAME / "projects" / (project_id or "default"))


def _default_checkpoint_db_path(state_root: str) -> str:
    return str(Path(state_root) / "state" / "checkpoints.sqlite")


def build_initial_state(
    task: str,
    project_id: str = "default",
    *,
    config_dir: str = "",
    registry_path: str = "",
    state_root: str = "",
    checkpoint_db_path: str = "",
    memory_db_path: str = "",
    execution_mode: str = "automatic",
    auto_approve_gates: list[str] | None = None,
    allow_deploy: bool = False,
    max_retries: int = 2,
    thread_id: str = "",
) -> OrchestratorState:
    resolved_state_root = state_root or _default_state_root(project_id, memory_db_path)
    return {
        "task": task,
        "project_id": project_id,
        "config_dir": config_dir,
        "registry_path": registry_path or DEFAULT_REGISTRY_PATH,
        "state_root": resolved_state_root,
        "checkpoint_db_path": checkpoint_db_path or _default_checkpoint_db_path(resolved_state_root),
        "memory_db_path": memory_db_path,
        "run_id": uuid.uuid4().hex[:12],
        "thread_id": thread_id,
        "execution_mode": execution_mode,
        "auto_approve_gates": auto_approve_gates or [],
        "allow_deploy": allow_deploy,
        "max_retries": max_retries,
        "retry_counts": {},
        "current_phase": "",
        "completed_phases": [],
        "pending_phases": [],
        "phase_route": "",
        "gate_passed": False,
        "gate_errors": [],
        "slots": {},
        "artifacts": {},
        "gates": {},
        "approvals": {},
        "shared_state_snapshot": {},
        "memory_pack_global": {},
        "memory_pack_by_agent": {},
        "phase_outputs": {},
        "discovery_output": "",
        "prd_output": "",
        "plan": "",
        "test_plan": "",
        "implementation_output": "",
        "contract_report": "",
        "test_results": "",
        "docs_output": "",
        "release_output": "",
        "deploy_output": "",
        "result": "",
        "events": [],
        "errors": [],
    }


def _runtime_thread_id(state: OrchestratorState) -> str:
    current = str(state.get("thread_id", "") or "")
    try:
        config = get_config()
        configurable = config.get("configurable", {}) if isinstance(config, dict) else {}
        current = str(configurable.get("thread_id") or current)
    except Exception:
        pass
    return current


def _with_defaults(state: OrchestratorState) -> OrchestratorState:
    initial = build_initial_state(
        task=state.get("task", ""),
        project_id=state.get("project_id", "default"),
        config_dir=state.get("config_dir", ""),
        registry_path=state.get("registry_path", ""),
        state_root=state.get("state_root", ""),
        checkpoint_db_path=state.get("checkpoint_db_path", ""),
        memory_db_path=state.get("memory_db_path", ""),
        execution_mode=state.get("execution_mode", "automatic"),
        auto_approve_gates=list(state.get("auto_approve_gates", [])),
        allow_deploy=bool(state.get("allow_deploy", False)),
        max_retries=int(state.get("max_retries", 2)),
        thread_id=state.get("thread_id", ""),
    )
    merged: OrchestratorState = {**initial, **state}
    merged["thread_id"] = _runtime_thread_id(merged)
    if not merged.get("pending_phases"):
        merged["pending_phases"] = _workflow_phase_ids(merged)
    return merged


def _get_registry(registry_path: str) -> AgentRegistry:
    resolved = str(Path(registry_path or DEFAULT_REGISTRY_PATH).resolve())
    registry = _REGISTRY_CACHE.get(resolved)
    if registry is None:
        registry = AgentRegistry(resolved)
        registry.load()
        _REGISTRY_CACHE[resolved] = registry
    return registry


def _workflow_phase_ids(state: OrchestratorState) -> list[str]:
    registry = _get_registry(state.get("registry_path", DEFAULT_REGISTRY_PATH))
    raw = registry.raw
    return [phase["id"] for phase in raw.get("workflow_phases", []) if phase.get("id")]


def _phase_meta(state: OrchestratorState, phase_id: str) -> dict[str, Any]:
    registry = _get_registry(state.get("registry_path", DEFAULT_REGISTRY_PATH))
    for phase in registry.raw.get("workflow_phases", []):
        if phase.get("id") == phase_id:
            return dict(phase)
    return {}


def _phase_owner(state: OrchestratorState, phase_id: str, fallback: str = "CodeOrchestrator") -> str:
    return _phase_meta(state, phase_id).get("owner", fallback)


def _phase_parallel_agents(state: OrchestratorState, phase_id: str) -> list[str]:
    return list(_phase_meta(state, phase_id).get("parallel_agents", []))


def _phase_review_agent(state: OrchestratorState, phase_id: str) -> str:
    return _phase_meta(state, phase_id).get("continuous_review_agent", "")


def _get_router(config_dir: str = "") -> LLMMultiProvider:
    cache_key = str(Path(config_dir).resolve()) if config_dir else "__default__"
    router = _ROUTER_CACHE.get(cache_key)
    if router is None:
        router = LLMMultiProvider(config_dir)
        _ROUTER_CACHE[cache_key] = router
    return router


def _normalized_memory_by_agent(state: OrchestratorState) -> dict[str, dict[str, int]]:
    normalized: dict[str, dict[str, int]] = {}
    for agent_name, pack in (state.get("memory_pack_by_agent") or {}).items():
        if isinstance(pack, dict):
            items = pack.get("items", [])
            normalized[agent_name] = {"items": len(items) if isinstance(items, list) else int(items or 0)}
            continue
        items = getattr(pack, "items", [])
        normalized[agent_name] = {"items": len(items) if isinstance(items, list) else 0}
    return normalized


def _get_agents(state: OrchestratorState) -> dict[str, Any]:
    router = _get_router(state.get("config_dir", ""))
    agents = create_all_agents(router=router, memory_by_agent=_normalized_memory_by_agent(state))
    context = _memory_text(state)
    if context:
        for agent in agents.values():
            agent.memory_context = context
    return agents


def _memory_text(state: OrchestratorState) -> str:
    parts: list[str] = []
    global_pack = state.get("memory_pack_global", {})
    items = global_pack.get("items", []) if isinstance(global_pack, dict) else []
    for item in items[:6]:
        title = item.get("title") or item.get("id") or "memory"
        snippet = item.get("snippet") or item.get("content") or ""
        if snippet:
            parts.append(f"- {title}: {snippet}")
    return "\n".join(parts)


def _get_state_store(state: OrchestratorState) -> StateStore:
    store = StateStore(
        project_id=state.get("project_id", "default"),
        root_dir=state.get("state_root", _default_state_root(state.get("project_id", "default"), state.get("memory_db_path", ""))),
        registry=_get_registry(state.get("registry_path", DEFAULT_REGISTRY_PATH)),
    )
    return store


def _current_sections(store: StateStore) -> dict[str, Any]:
    snapshot = store.snapshot()
    return {
        "slots": snapshot.get("slots", {}),
        "artifacts": snapshot.get("artifacts", {}),
        "gates": snapshot.get("gates", {}),
        "approvals": snapshot.get("approvals", {}),
    }


def _update_shared_snapshot(state: OrchestratorState, source_agent: str, **entries: Any) -> dict[str, Any]:
    board = SharedState()
    board.merge(state.get("shared_state_snapshot", {}), source_agent="previous")
    board.merge(entries, source_agent=source_agent)
    return board.snapshot()


def _persist_runtime_metadata(state: OrchestratorState, updates: dict[str, Any], store: StateStore) -> dict[str, Any]:
    merged = {**state, **{k: v for k, v in updates.items() if k not in {"events", "errors"}}}
    workflow = {
        "current_phase": merged.get("current_phase", ""),
        "completed_phases": merged.get("completed_phases", []),
        "pending_phases": merged.get("pending_phases", []),
        "retry_counts": merged.get("retry_counts", {}),
        "max_retries": merged.get("max_retries", 2),
        "execution_mode": merged.get("execution_mode", "automatic"),
    }
    thread_id = _runtime_thread_id(merged)
    metadata = {
        "run_id": merged.get("run_id", ""),
        "project_id": merged.get("project_id", ""),
        "thread_id": thread_id,
        "memory_db_path": merged.get("memory_db_path", ""),
        "registry_path": merged.get("registry_path", DEFAULT_REGISTRY_PATH),
        "state_root": merged.get("state_root", ""),
        "checkpoint_db_path": merged.get("checkpoint_db_path", ""),
        "workflow": workflow,
        "shared_state": merged.get("shared_state_snapshot", {}),
        "memory": {
            "global_items": len((merged.get("memory_pack_global") or {}).get("items", [])),
            "agents": list((merged.get("memory_pack_by_agent") or {}).keys()),
        },
        "phase_outputs": merged.get("phase_outputs", {}),
        "gate_passed": merged.get("gate_passed", False),
        "gate_errors": merged.get("gate_errors", []),
        "result": merged.get("result", ""),
    }
    store.write_runtime_metadata(metadata)
    if updates.get("events"):
        store.append_events(updates["events"])
    return _current_sections(store)


def _phase_progress(state: OrchestratorState, phase_id: str, *, completed: bool = False) -> tuple[list[str], list[str]]:
    known = _workflow_phase_ids(state)
    completed_phases = list(state.get("completed_phases", []))
    if completed and phase_id in known and phase_id not in completed_phases:
        completed_phases.append(phase_id)
    pending = [phase for phase in known if phase not in completed_phases]
    return completed_phases, pending


def _event(node_type: str, summary: str, **extra: Any) -> dict[str, Any]:
    payload = {"type": node_type, "summary": summary}
    payload.update(extra)
    return payload


def _agent_slot_name(state: OrchestratorState, agent_name: str) -> str:
    agent = _get_registry(state.get("registry_path", DEFAULT_REGISTRY_PATH)).get_agent(agent_name) or {}
    writes = [entry for entry in agent.get("writes", []) if isinstance(entry, str)]
    slot = next((entry for entry in writes if entry.endswith("_slot")), "")
    if slot:
        return slot
    return f"{agent_name.lower()}_slot"


def _agent_draft_artifacts(state: OrchestratorState, agent_name: str) -> list[str]:
    agent = _get_registry(state.get("registry_path", DEFAULT_REGISTRY_PATH)).get_agent(agent_name) or {}
    writes = [entry for entry in agent.get("writes", []) if isinstance(entry, str)]
    return [entry for entry in writes if entry in _DRAFT_ARTIFACT_ALLOWLIST]


def _artifact_phase_dir(artifact_id: str, fallback_phase_id: str) -> str:
    return _PHASE_ARTIFACT_DIRS.get(artifact_id, _PHASE_ARTIFACT_DIRS.get(fallback_phase_id, fallback_phase_id))


def _invoke_agent(state: OrchestratorState, agent_name: str, prompt: str) -> tuple[str, dict[str, Any], list[str]]:
    agents = _get_agents(state)
    agent = agents[agent_name]
    try:
        result = agent.generate(prompt)
        metadata = {
            "agent": agent_name,
            "provider": result.provider,
            "model": result.model,
            "fallback": False,
        }
        return result.output, metadata, []
    except Exception as exc:  # pragma: no cover - defensive runtime fallback
        fallback = f"[fallback:{agent_name}] {prompt[:500]}"
        return fallback, {"agent": agent_name, "provider": "mock", "model": "fallback", "fallback": True}, [f"{agent_name}: {exc}"]


def _write_agent_slot_and_drafts(
    state: OrchestratorState,
    store: StateStore,
    *,
    phase_id: str,
    agent_name: str,
    output: str,
    summary: str,
) -> list[str]:
    produced_artifacts: list[str] = []
    for artifact_id in _agent_draft_artifacts(state, agent_name):
        phase_dir = _artifact_phase_dir(artifact_id, phase_id)
        store.write_artifact(
            artifact_id,
            phase_dir,
            output,
            created_by=agent_name,
            status="draft",
            summary=f"Draft artifact from {agent_name}",
        )
        produced_artifacts.append(artifact_id)
    store.write_slot(
        agent_name,
        _agent_slot_name(state, agent_name),
        {"phase": phase_id, "output": output},
        summary=summary,
        produced_artifacts=produced_artifacts,
    )
    return produced_artifacts


def _write_canonical_artifact(store: StateStore, artifact_id: str, content: Any, *, created_by: str, summary: str, status: str = "draft") -> dict[str, Any]:
    return store.write_artifact(
        artifact_id,
        _artifact_phase_dir(artifact_id, artifact_id),
        content,
        created_by=created_by,
        status=status,
        summary=summary,
    )


def _normalize_gate_response(response: Any) -> tuple[bool, str]:
    if isinstance(response, dict):
        approved = bool(response.get("approved", False))
        note = str(response.get("notes") or response.get("comment") or response.get("message") or "")
        return approved, note
    if isinstance(response, bool):
        return response, ""
    text = str(response or "").strip()
    return text.lower() in {"approve", "approved", "true", "yes", "ok"}, text


def _handle_gate(
    state: OrchestratorState,
    gate_node: str,
    *,
    phase_id: str,
    requested_by: str,
    success_route: str,
    retry_route: str,
    skip_route: str = "",
) -> dict[str, Any]:
    state = _with_defaults(state)
    store = _get_state_store(state)
    required_artifacts = _GATE_REQUIREMENTS.get(gate_node, [])
    artifact_versions = store.artifact_versions(required_artifacts)
    missing = [artifact for artifact in required_artifacts if artifact not in artifact_versions]

    completed_phases, pending_phases = _phase_progress(state, phase_id, completed=False)
    updates: dict[str, Any] = {
        "current_phase": gate_node,
        "completed_phases": completed_phases,
        "pending_phases": pending_phases,
        "retry_counts": dict(state.get("retry_counts", {})),
        "gate_errors": [],
    }

    if gate_node == "deploy_gate" and not state.get("allow_deploy", False):
        store.record_approval(gate_node, "approved", requested_by=requested_by, artifact_versions=artifact_versions, user_response="deploy skipped")
        store.set_gate_status(gate_node, "passed", checked_by=requested_by, required_artifacts=required_artifacts)
        completed_phases, pending_phases = _phase_progress(state, phase_id, completed=True)
        shared = _update_shared_snapshot(state, requested_by, **{"deploy.approved": False, "deploy.skipped": True})
        updates.update({
            "completed_phases": completed_phases,
            "pending_phases": pending_phases,
            "phase_route": skip_route or success_route,
            "shared_state_snapshot": shared,
        })
        updates.update(_persist_runtime_metadata(state, updates, store))
        return updates

    if missing:
        retries = dict(state.get("retry_counts", {}))
        retries[phase_id] = retries.get(phase_id, 0) + 1
        blocked = retries[phase_id] > int(state.get("max_retries", 2))
        store.record_approval(gate_node, "changes_requested", requested_by=requested_by, artifact_versions=artifact_versions, user_response=f"missing: {', '.join(missing)}")
        store.set_gate_status(
            gate_node,
            "blocked" if blocked else "failed",
            checked_by=requested_by,
            required_artifacts=required_artifacts,
            blocking_issues=[f"Missing artifacts: {', '.join(missing)}"],
        )
        shared = _update_shared_snapshot(state, requested_by, **{f"{gate_node}.missing_artifacts": missing})
        updates.update({
            "retry_counts": retries,
            "phase_route": "blocked" if blocked else "retry",
            "gate_errors": [f"Missing artifacts for {gate_node}: {', '.join(missing)}"],
            "shared_state_snapshot": shared,
            "events": [_event(gate_node, "Gate missing required artifacts", phase=phase_id, missing=missing)],
        })
        updates.update(_persist_runtime_metadata(state, updates, store))
        return updates

    interactive = state.get("execution_mode", "automatic") == "interactive"
    auto_approved = set(state.get("auto_approve_gates", []))

    if interactive and gate_node not in auto_approved:
        store.record_approval(gate_node, "pending", requested_by=requested_by, artifact_versions=artifact_versions)
        store.set_gate_status(gate_node, "pending", checked_by=requested_by, required_artifacts=required_artifacts)
        pending_shared = _update_shared_snapshot(state, requested_by, **{f"{gate_node}.status": "pending"})
        pending_updates = {
            **updates,
            "phase_route": "pending",
            "shared_state_snapshot": pending_shared,
            "events": [_event(gate_node, "Gate awaiting approval", phase=phase_id, approval=_GATE_APPROVAL_LABELS.get(phase_id, gate_node))],
        }
        pending_updates.update(_persist_runtime_metadata(state, pending_updates, store))
        answer = interrupt(
            {
                "gate": gate_node,
                "phase": phase_id,
                "approval": _GATE_APPROVAL_LABELS.get(phase_id, gate_node),
                "required_artifacts": required_artifacts,
                "artifact_versions": artifact_versions,
            }
        )
        approved, note = _normalize_gate_response(answer)
    else:
        approved, note = True, "automatic approval"

    if approved:
        store.record_approval(gate_node, "approved", requested_by=requested_by, artifact_versions=artifact_versions, user_response=note)
        store.set_gate_status(gate_node, "passed", checked_by=requested_by, required_artifacts=required_artifacts)
        completed_phases, pending_phases = _phase_progress(state, phase_id, completed=True)
        shared = _update_shared_snapshot(state, requested_by, **{f"{gate_node}.status": "approved", f"{phase_id}.approved": True})
        updates.update({
            "completed_phases": completed_phases,
            "pending_phases": pending_phases,
            "phase_route": success_route,
            "shared_state_snapshot": shared,
            "events": [_event(gate_node, "Gate approved", phase=phase_id, approval=_GATE_APPROVAL_LABELS.get(phase_id, gate_node))],
        })
        updates.update(_persist_runtime_metadata(state, updates, store))
        return updates

    retries = dict(state.get("retry_counts", {}))
    retries[phase_id] = retries.get(phase_id, 0) + 1
    blocked = retries[phase_id] > int(state.get("max_retries", 2))
    store.record_approval(gate_node, "changes_requested", requested_by=requested_by, artifact_versions=artifact_versions, user_response=note)
    store.set_gate_status(
        gate_node,
        "blocked" if blocked else "failed",
        checked_by=requested_by,
        required_artifacts=required_artifacts,
        blocking_issues=[note or "changes requested"],
    )
    shared = _update_shared_snapshot(state, requested_by, **{f"{gate_node}.status": "changes_requested"})
    updates.update({
        "retry_counts": retries,
        "phase_route": "blocked" if blocked else "retry",
        "gate_errors": [note or f"Changes requested in {gate_node}"],
        "shared_state_snapshot": shared,
        "events": [_event(gate_node, "Gate rejected", phase=phase_id, note=note)],
    })
    updates.update(_persist_runtime_metadata(state, updates, store))
    return updates


def intake(state: OrchestratorState) -> dict[str, Any]:
    state = _with_defaults(state)
    store = _get_state_store(state)
    shared = _update_shared_snapshot(state, "HermesOrchestrator", **{
        "task": state.get("task", ""),
        "project_id": state.get("project_id", "default"),
        "intake.task": state.get("task", ""),
        "intake.project_id": state.get("project_id", "default"),
    })
    completed_phases, pending_phases = _phase_progress(state, "intake", completed=True)
    updates = {
        "current_phase": "intake",
        "completed_phases": completed_phases,
        "pending_phases": pending_phases,
        "shared_state_snapshot": shared,
        "events": [_event("intake", "Task normalized and run initialized", run_id=state.get("run_id"))],
    }
    updates.update(_persist_runtime_metadata(state, updates, store))
    return updates


def memory_rehydration(state: OrchestratorState) -> dict[str, Any]:
    state = _with_defaults(state)
    store = _get_state_store(state)
    task = TaskContext(task=state.get("task", ""), project_id=state.get("project_id", "default"), agent_ids=[])
    packs: dict[str, Any] = {}
    global_context: dict[str, Any] = {}

    if state.get("memory_db_path"):
        mem_store = MemoryStore(state["memory_db_path"])
        project = mem_store.get_project(state.get("project_id", "default"))
        if project is None:
            mem_store.create_project(state.get("project_id", "default"), state.get("project_id", "default"))
        memory_context = MemoryContextAgent(mem_store)
        agent_ids = list(create_all_agents().keys())
        task.agent_ids = agent_ids
        packs = memory_context.hydrate(task, agent_ids, token_budget=1200)
        global_context = memory_context.get_global_context(state.get("project_id", "default"), limit=10)

    shared = _update_shared_snapshot(state, "MemoryContextAgent", **{
        "memory.rehydrated": True,
        "memory.global_items": len(global_context.get("items", [])) if isinstance(global_context, dict) else 0,
    })
    completed_phases, pending_phases = _phase_progress(state, "memory_rehydration", completed=True)
    updates = {
        "current_phase": "memory_rehydration",
        "completed_phases": completed_phases,
        "pending_phases": pending_phases,
        "memory_pack_by_agent": packs,
        "memory_pack_global": global_context,
        "shared_state_snapshot": shared,
        "events": [_event("memory_rehydration", "Memory packs rehydrated", agents=len(packs))],
    }
    updates.update(_persist_runtime_metadata(state, updates, store))
    return updates


def discovery(state: OrchestratorState) -> dict[str, Any]:
    state = _with_defaults(state)
    store = _get_state_store(state)
    agent_name = _phase_owner(state, "discovery", "BusinessAnalyst")
    prompt = f"Analyze the user's task, clarify goals, risks, and constraints.\n\nTask:\n{state.get('task', '')}"
    output, meta, errors = _invoke_agent(state, agent_name, prompt)
    produced = _write_agent_slot_and_drafts(state, store, phase_id="discovery", agent_name=agent_name, output=output, summary="Discovery draft ready")
    _write_canonical_artifact(store, "discovery", output, created_by=agent_name, summary="Discovery summary")
    shared = _update_shared_snapshot(state, agent_name, **{"discovery.output": output})
    phase_outputs = dict(state.get("phase_outputs", {}))
    phase_outputs["discovery"] = {"owner": agent_name, "output": output, "draft_artifacts": produced, **meta}
    completed_phases, pending_phases = _phase_progress(state, "discovery", completed=False)
    updates = {
        "current_phase": "discovery",
        "completed_phases": completed_phases,
        "pending_phases": pending_phases,
        "discovery_output": output,
        "phase_outputs": phase_outputs,
        "shared_state_snapshot": shared,
        "errors": errors,
        "events": [_event("discovery", "Discovery draft produced", **meta)],
    }
    updates.update(_persist_runtime_metadata(state, updates, store))
    return updates


def discovery_gate(state: OrchestratorState) -> dict[str, Any]:
    return _handle_gate(state, "discovery_gate", phase_id="discovery", requested_by="HermesOrchestrator", success_route="prd", retry_route="discovery")


def prd(state: OrchestratorState) -> dict[str, Any]:
    state = _with_defaults(state)
    store = _get_state_store(state)
    agent_name = _phase_owner(state, "prd", "ProductManager")
    prompt = (
        "Turn the discovery into an actionable PRD with scope, acceptance criteria, non-goals, and rollout notes.\n\n"
        f"Task:\n{state.get('task', '')}\n\nDiscovery:\n{state.get('discovery_output', '')}"
    )
    output, meta, errors = _invoke_agent(state, agent_name, prompt)
    produced = _write_agent_slot_and_drafts(state, store, phase_id="prd", agent_name=agent_name, output=output, summary="PRD draft ready")
    _write_canonical_artifact(store, "prd", output, created_by=agent_name, summary="Product requirements document")
    shared = _update_shared_snapshot(state, agent_name, **{"prd.output": output})
    phase_outputs = dict(state.get("phase_outputs", {}))
    phase_outputs["prd"] = {"owner": agent_name, "output": output, "draft_artifacts": produced, **meta}
    completed_phases, pending_phases = _phase_progress(state, "prd", completed=False)
    updates = {
        "current_phase": "prd",
        "completed_phases": completed_phases,
        "pending_phases": pending_phases,
        "prd_output": output,
        "phase_outputs": phase_outputs,
        "shared_state_snapshot": shared,
        "errors": errors,
        "events": [_event("prd", "PRD draft produced", **meta)],
    }
    updates.update(_persist_runtime_metadata(state, updates, store))
    return updates


def prd_gate(state: OrchestratorState) -> dict[str, Any]:
    return _handle_gate(state, "prd_gate", phase_id="prd", requested_by="HermesOrchestrator", success_route="planning", retry_route="prd")


def planning(state: OrchestratorState) -> dict[str, Any]:
    state = _with_defaults(state)
    store = _get_state_store(state)
    phase_outputs = dict(state.get("phase_outputs", {}))
    planning_outputs: dict[str, Any] = {}
    all_errors: list[str] = []
    subevents: list[dict[str, Any]] = []

    planning_prompt = (
        f"Task:\n{state.get('task', '')}\n\n"
        f"Discovery:\n{state.get('discovery_output', '')}\n\n"
        f"PRD:\n{state.get('prd_output', '')}"
    )

    for agent_name in _phase_parallel_agents(state, "technical_planning") or ["Planner", "CodebaseExplorer", "Architect", "SystemDesigner"]:
        output, meta, errors = _invoke_agent(state, agent_name, planning_prompt)
        produced = _write_agent_slot_and_drafts(state, store, phase_id="technical_planning", agent_name=agent_name, output=output, summary=f"{agent_name} planning draft ready")
        planning_outputs[agent_name] = {"output": output, "draft_artifacts": produced, **meta}
        all_errors.extend(errors)
        subevents.append(_event("planning", f"{agent_name} contributed planning context", **meta))

    consolidator = _phase_owner(state, "spec_consolidation", "CodeOrchestrator")
    consolidation_prompt = (
        "Consolidate the technical planning drafts into canonical artifacts: spec, task graph, design, and design system.\n\n"
        f"Task:\n{state.get('task', '')}\n\n"
        f"PRD:\n{state.get('prd_output', '')}\n\n"
        f"Drafts:\n{planning_outputs}"
    )
    spec_output, meta, errors = _invoke_agent(state, consolidator, consolidation_prompt)
    all_errors.extend(errors)
    _write_agent_slot_and_drafts(state, store, phase_id="spec_consolidation", agent_name=consolidator, output=spec_output, summary="Canonical spec consolidated")

    _write_canonical_artifact(store, "task_graph", planning_outputs.get("Planner", {}).get("output", spec_output), created_by=consolidator, summary="Task graph")
    _write_canonical_artifact(store, "design", planning_outputs.get("Architect", {}).get("output", spec_output), created_by=consolidator, summary="Architecture design")
    _write_canonical_artifact(store, "design_system", planning_outputs.get("SystemDesigner", {}).get("output", spec_output), created_by=consolidator, summary="Design system")
    _write_canonical_artifact(store, "spec", spec_output, created_by=consolidator, summary="Canonical engineering spec")

    shared = _update_shared_snapshot(
        state,
        consolidator,
        **{
            "planning.plan": spec_output,
            "planning.task_graph": planning_outputs.get("Planner", {}).get("output", ""),
            "planning.design": planning_outputs.get("Architect", {}).get("output", ""),
        },
    )
    phase_outputs["technical_planning"] = planning_outputs
    phase_outputs["spec_consolidation"] = {"owner": consolidator, "output": spec_output, **meta}
    completed_phases, pending_phases = _phase_progress(state, "technical_planning", completed=True)
    updates = {
        "current_phase": "planning",
        "completed_phases": completed_phases,
        "pending_phases": pending_phases,
        "plan": spec_output,
        "phase_outputs": phase_outputs,
        "shared_state_snapshot": shared,
        "errors": all_errors,
        "events": subevents + [_event("planning", "Canonical spec consolidated", **meta)],
    }
    updates.update(_persist_runtime_metadata(state, updates, store))
    return updates


def spec_gate(state: OrchestratorState) -> dict[str, Any]:
    return _handle_gate(state, "spec_gate", phase_id="spec_consolidation", requested_by="CodeOrchestrator", success_route="testing", retry_route="planning")


def testing(state: OrchestratorState) -> dict[str, Any]:
    state = _with_defaults(state)
    store = _get_state_store(state)
    agent_name = _phase_owner(state, "tdd", "Tester")
    prompt = (
        "Create a test-first execution plan covering acceptance criteria, edge cases, integration checks, and rollback considerations.\n\n"
        f"Task:\n{state.get('task', '')}\n\n"
        f"Spec:\n{state.get('plan', '')}"
    )
    output, meta, errors = _invoke_agent(state, agent_name, prompt)
    produced = _write_agent_slot_and_drafts(state, store, phase_id="tdd", agent_name=agent_name, output=output, summary="Test plan ready")
    _write_canonical_artifact(store, "test_plan", output, created_by=agent_name, summary="Test plan")
    shared = _update_shared_snapshot(state, agent_name, **{"testing.plan": output})
    phase_outputs = dict(state.get("phase_outputs", {}))
    phase_outputs["tdd"] = {"owner": agent_name, "output": output, "draft_artifacts": produced, **meta}
    completed_phases, pending_phases = _phase_progress(state, "tdd", completed=False)
    updates = {
        "current_phase": "testing",
        "completed_phases": completed_phases,
        "pending_phases": pending_phases,
        "test_plan": output,
        "phase_outputs": phase_outputs,
        "shared_state_snapshot": shared,
        "errors": errors,
        "events": [_event("testing", "Test plan drafted", **meta)],
    }
    updates.update(_persist_runtime_metadata(state, updates, store))
    return updates


def testing_gate(state: OrchestratorState) -> dict[str, Any]:
    return _handle_gate(state, "testing_gate", phase_id="tdd", requested_by="Tester", success_route="implementation", retry_route="testing")


def implementation(state: OrchestratorState) -> dict[str, Any]:
    state = _with_defaults(state)
    store = _get_state_store(state)
    phase_outputs = dict(state.get("phase_outputs", {}))
    impl_outputs: dict[str, Any] = {}
    all_errors: list[str] = []
    events: list[dict[str, Any]] = []

    prompt = (
        f"Task:\n{state.get('task', '')}\n\n"
        f"Spec:\n{state.get('plan', '')}\n\n"
        f"Test plan:\n{state.get('test_plan', '')}"
    )

    for agent_name in _phase_parallel_agents(state, "implementation") or ["BackendImplementer", "FrontendImplementer"]:
        output, meta, errors = _invoke_agent(state, agent_name, prompt)
        produced = _write_agent_slot_and_drafts(state, store, phase_id="implementation", agent_name=agent_name, output=output, summary=f"{agent_name} implementation summary")
        impl_outputs[agent_name] = {"output": output, "draft_artifacts": produced, **meta}
        all_errors.extend(errors)
        events.append(_event("implementation", f"{agent_name} implementation completed", **meta))

    reviewer = _phase_review_agent(state, "implementation") or "SystemDesigner"
    review_prompt = (
        "Review the combined backend and frontend implementation against the design system and UX constraints.\n\n"
        f"Design system:\n{store.get_artifact('design_system') or {}}\n\n"
        f"Implementation outputs:\n{impl_outputs}"
    )
    review_output, meta, errors = _invoke_agent(state, reviewer, review_prompt)
    _write_agent_slot_and_drafts(state, store, phase_id="implementation", agent_name=reviewer, output=review_output, summary="Implementation review by SystemDesigner")
    all_errors.extend(errors)
    events.append(_event("implementation", "Continuous design review completed", **meta))

    backend_summary = impl_outputs.get("BackendImplementer", {}).get("output", "")
    frontend_summary = impl_outputs.get("FrontendImplementer", {}).get("output", "")
    _write_canonical_artifact(store, "backend_summary", backend_summary, created_by="BackendImplementer", summary="Backend implementation summary")
    _write_canonical_artifact(store, "frontend_summary", frontend_summary, created_by="FrontendImplementer", summary="Frontend implementation summary")

    combined = f"Backend:\n{backend_summary}\n\nFrontend:\n{frontend_summary}\n\nDesign review:\n{review_output}"
    shared = _update_shared_snapshot(state, reviewer, **{
        "implementation.agent": "BackendImplementer+FrontendImplementer",
        "implementation.output": combined,
    })
    phase_outputs["implementation"] = {**impl_outputs, "SystemDesigner": {"output": review_output, **meta}}
    completed_phases, pending_phases = _phase_progress(state, "implementation", completed=True)
    updates = {
        "current_phase": "implementation",
        "completed_phases": completed_phases,
        "pending_phases": pending_phases,
        "implementation_output": combined,
        "phase_outputs": phase_outputs,
        "shared_state_snapshot": shared,
        "errors": all_errors,
        "events": events,
    }
    updates.update(_persist_runtime_metadata(state, updates, store))
    return updates


def contract_alignment(state: OrchestratorState) -> dict[str, Any]:
    state = _with_defaults(state)
    store = _get_state_store(state)
    agent_name = _phase_owner(state, "contract_alignment", "ContractAligner")
    prompt = (
        "Compare backend and frontend implementation outputs, identify API/data contract mismatches, and propose fixes.\n\n"
        f"Implementation:\n{state.get('implementation_output', '')}\n\n"
        f"Spec:\n{state.get('plan', '')}"
    )
    output, meta, errors = _invoke_agent(state, agent_name, prompt)
    produced = _write_agent_slot_and_drafts(state, store, phase_id="contract_alignment", agent_name=agent_name, output=output, summary="Contract alignment report ready")
    _write_canonical_artifact(store, "contract_report", output, created_by=agent_name, summary="Contract alignment report")
    shared = _update_shared_snapshot(state, agent_name, **{"contract.alignment": output})
    phase_outputs = dict(state.get("phase_outputs", {}))
    phase_outputs["contract_alignment"] = {"owner": agent_name, "output": output, "draft_artifacts": produced, **meta}
    completed_phases, pending_phases = _phase_progress(state, "contract_alignment", completed=False)
    updates = {
        "current_phase": "contract_alignment",
        "completed_phases": completed_phases,
        "pending_phases": pending_phases,
        "contract_report": output,
        "phase_outputs": phase_outputs,
        "shared_state_snapshot": shared,
        "errors": errors,
        "events": [_event("contract_alignment", "Contract alignment report generated", **meta)],
    }
    updates.update(_persist_runtime_metadata(state, updates, store))
    return updates


def contract_gate(state: OrchestratorState) -> dict[str, Any]:
    return _handle_gate(state, "contract_gate", phase_id="contract_alignment", requested_by="ContractAligner", success_route="review", retry_route="implementation")


def review(state: OrchestratorState) -> dict[str, Any]:
    state = _with_defaults(state)
    store = _get_state_store(state)
    phase_outputs = dict(state.get("phase_outputs", {}))
    review_outputs: dict[str, Any] = {}
    all_errors: list[str] = []
    events: list[dict[str, Any]] = []

    prompt = (
        f"Task:\n{state.get('task', '')}\n\n"
        f"Implementation:\n{state.get('implementation_output', '')}\n\n"
        f"Contract report:\n{state.get('contract_report', '')}\n\n"
        f"Test plan:\n{state.get('test_plan', '')}"
    )
    for agent_name in _phase_parallel_agents(state, "review") or ["Reviewer", "SecurityReviewer", "Tester"]:
        output, meta, errors = _invoke_agent(state, agent_name, prompt)
        produced = _write_agent_slot_and_drafts(state, store, phase_id="review", agent_name=agent_name, output=output, summary=f"{agent_name} review output ready")
        review_outputs[agent_name] = {"output": output, "draft_artifacts": produced, **meta}
        all_errors.extend(errors)
        events.append(_event("review", f"{agent_name} review completed", **meta))

    _write_canonical_artifact(store, "code_review_report", review_outputs.get("Reviewer", {}).get("output", ""), created_by="Reviewer", summary="Code review report")
    _write_canonical_artifact(store, "security_report", review_outputs.get("SecurityReviewer", {}).get("output", ""), created_by="SecurityReviewer", summary="Security review report")
    _write_canonical_artifact(store, "test_results", review_outputs.get("Tester", {}).get("output", ""), created_by="Tester", summary="Test execution results")

    tester_output = review_outputs.get("Tester", {}).get("output", "")
    shared = _update_shared_snapshot(state, "CodeOrchestrator", **{"testing.results": tester_output})
    phase_outputs["review"] = review_outputs
    completed_phases, pending_phases = _phase_progress(state, "review", completed=True)
    updates = {
        "current_phase": "review",
        "completed_phases": completed_phases,
        "pending_phases": pending_phases,
        "test_results": tester_output,
        "phase_outputs": phase_outputs,
        "shared_state_snapshot": shared,
        "errors": all_errors,
        "events": events,
    }
    updates.update(_persist_runtime_metadata(state, updates, store))
    return updates


def quality_gate(state: OrchestratorState) -> dict[str, Any]:
    state = _with_defaults(state)
    store = _get_state_store(state)
    phase_outputs = dict(state.get("phase_outputs", {}))
    qa_outputs: dict[str, Any] = {}
    all_errors: list[str] = []
    events: list[dict[str, Any]] = []

    prompt = (
        f"Task:\n{state.get('task', '')}\n\n"
        f"Review outputs:\n{phase_outputs.get('review', {})}\n\n"
        f"Contract report:\n{state.get('contract_report', '')}\n\n"
        f"Spec:\n{state.get('plan', '')}"
    )
    for agent_name in _phase_parallel_agents(state, "qa_docs") or ["QAGatekeeper", "DependencyChecker", "TechnicalWriter"]:
        output, meta, errors = _invoke_agent(state, agent_name, prompt)
        produced = _write_agent_slot_and_drafts(state, store, phase_id="qa_docs", agent_name=agent_name, output=output, summary=f"{agent_name} QA/docs output ready")
        qa_outputs[agent_name] = {"output": output, "draft_artifacts": produced, **meta}
        all_errors.extend(errors)
        events.append(_event("quality_gate", f"{agent_name} QA/docs contribution completed", **meta))

    qa_report = qa_outputs.get("QAGatekeeper", {}).get("output", "")
    dependency_report = qa_outputs.get("DependencyChecker", {}).get("output", "")
    docs_output = qa_outputs.get("TechnicalWriter", {}).get("output", "")

    _write_canonical_artifact(store, "qa_report", qa_report, created_by="QAGatekeeper", summary="QA gate report")
    _write_canonical_artifact(store, "dependency_report", dependency_report, created_by="DependencyChecker", summary="Dependency report")
    _write_canonical_artifact(store, "docs", docs_output, created_by="TechnicalWriter", summary="Technical documentation")

    lowered = qa_report.lower()
    gate_passed = not any(flag in lowered for flag in ["fail", "failed", "blocked", "reject"])
    route = "approved" if gate_passed else "retry"
    gate_errors = [] if gate_passed else ["QA gatekeeper requested changes"]
    store.set_gate_status("quality_gate", "passed" if gate_passed else "failed", checked_by="QAGatekeeper", required_artifacts=["qa_report", "dependency_report", "docs"], blocking_issues=gate_errors)

    shared = _update_shared_snapshot(state, "QAGatekeeper", **{
        "quality.gate_passed": gate_passed,
        "quality.docs_ready": bool(docs_output),
    })
    phase_outputs["qa_docs"] = qa_outputs
    completed_phases, pending_phases = _phase_progress(state, "qa_docs", completed=gate_passed)
    updates = {
        "current_phase": "quality_gate",
        "completed_phases": completed_phases,
        "pending_phases": pending_phases,
        "gate_passed": gate_passed,
        "gate_errors": gate_errors,
        "docs_output": docs_output,
        "phase_route": route,
        "phase_outputs": phase_outputs,
        "shared_state_snapshot": shared,
        "errors": all_errors,
        "events": events + [_event("quality_gate", "Quality gate evaluated", passed=gate_passed)],
    }
    updates.update(_persist_runtime_metadata(state, updates, store))
    return updates


def release(state: OrchestratorState) -> dict[str, Any]:
    state = _with_defaults(state)
    store = _get_state_store(state)
    agent_name = _phase_owner(state, "release", "ReleaseManager")
    prompt = (
        "Prepare a release summary with change scope, validation checklist, risks, and next operational steps.\n\n"
        f"QA/docs:\n{state.get('phase_outputs', {}).get('qa_docs', {})}\n\n"
        f"Implementation summary:\n{state.get('implementation_output', '')}"
    )
    output, meta, errors = _invoke_agent(state, agent_name, prompt)
    produced = _write_agent_slot_and_drafts(state, store, phase_id="release", agent_name=agent_name, output=output, summary="Release package ready")
    _write_canonical_artifact(store, "release_notes", output, created_by=agent_name, summary="Release notes")
    shared = _update_shared_snapshot(state, agent_name, **{"release.output": output})
    phase_outputs = dict(state.get("phase_outputs", {}))
    phase_outputs["release"] = {"owner": agent_name, "output": output, "draft_artifacts": produced, **meta}
    completed_phases, pending_phases = _phase_progress(state, "release", completed=False)
    updates = {
        "current_phase": "release",
        "completed_phases": completed_phases,
        "pending_phases": pending_phases,
        "release_output": output,
        "phase_outputs": phase_outputs,
        "shared_state_snapshot": shared,
        "errors": errors,
        "events": [_event("release", "Release notes prepared", **meta)],
    }
    updates.update(_persist_runtime_metadata(state, updates, store))
    return updates


def release_gate(state: OrchestratorState) -> dict[str, Any]:
    return _handle_gate(state, "release_gate", phase_id="release", requested_by="HermesOrchestrator", success_route="deploy_gate", retry_route="release", skip_route="memory_consolidation")


def deploy_gate(state: OrchestratorState) -> dict[str, Any]:
    return _handle_gate(state, "deploy_gate", phase_id="deploy", requested_by="HermesOrchestrator", success_route="deploy", retry_route="release", skip_route="memory_consolidation")


def deploy(state: OrchestratorState) -> dict[str, Any]:
    state = _with_defaults(state)
    store = _get_state_store(state)
    agent_name = _phase_owner(state, "deploy", "Builder")

    if not state.get("allow_deploy", False):
        output = "Deploy skipped because allow_deploy=false. Runtime still produced the deploy phase handoff."
        meta = {"agent": agent_name, "provider": "system", "model": "skip", "fallback": False}
        errors: list[str] = []
    else:
        prompt = (
            "Prepare a safe deployment execution summary, verification steps, and post-deploy checks.\n\n"
            f"Release notes:\n{state.get('release_output', '')}"
        )
        output, meta, errors = _invoke_agent(state, agent_name, prompt)

    produced = _write_agent_slot_and_drafts(state, store, phase_id="deploy", agent_name=agent_name, output=output, summary="Deploy report ready")
    _write_canonical_artifact(store, "deploy_report", output, created_by=agent_name, summary="Deploy report")
    shared = _update_shared_snapshot(state, agent_name, **{"deploy.output": output})
    phase_outputs = dict(state.get("phase_outputs", {}))
    phase_outputs["deploy"] = {"owner": agent_name, "output": output, "draft_artifacts": produced, **meta}
    completed_phases, pending_phases = _phase_progress(state, "deploy", completed=True)
    updates = {
        "current_phase": "deploy",
        "completed_phases": completed_phases,
        "pending_phases": pending_phases,
        "deploy_output": output,
        "phase_outputs": phase_outputs,
        "shared_state_snapshot": shared,
        "errors": errors,
        "events": [_event("deploy", "Deploy phase completed", **meta)],
    }
    updates.update(_persist_runtime_metadata(state, updates, store))
    return updates


def memory_consolidation(state: OrchestratorState) -> dict[str, Any]:
    state = _with_defaults(state)
    store = _get_state_store(state)
    if state.get("memory_db_path"):
        mem_store = MemoryStore(state["memory_db_path"])
        project = mem_store.get_project(state.get("project_id", "default"))
        if project is None:
            mem_store.create_project(state.get("project_id", "default"), state.get("project_id", "default"))
        manager = MemoryManager(mem_store)
        candidate = MemoryCandidate(
            source_agent="MemoryManager",
            kind=MemoryKind.DECISION,
            project_id=state.get("project_id", "default"),
            title=f"Run {state.get('run_id', '')} summary",
            content=(
                f"Task: {state.get('task', '')}\n"
                f"Spec: {state.get('plan', '')[:500]}\n"
                f"Implementation: {state.get('implementation_output', '')[:500]}\n"
                f"Release: {state.get('release_output', '')[:500]}"
            ),
            tags=["workflow", "runtime", "langgraph"],
        )
        candidate_id = manager.add_candidate(candidate)
        manager.auto_commit_safe(candidate_id, actor="MemoryManager")

    shared = _update_shared_snapshot(state, "MemoryManager", **{"memory.last_consolidation": state.get("run_id", "")})
    completed_phases, pending_phases = _phase_progress(state, "memory_consolidation", completed=True)
    updates = {
        "current_phase": "memory_consolidation",
        "completed_phases": completed_phases,
        "pending_phases": pending_phases,
        "shared_state_snapshot": shared,
        "events": [_event("memory_consolidation", "Workflow memory consolidated")],
    }
    updates.update(_persist_runtime_metadata(state, updates, store))
    return updates


def delivery(state: OrchestratorState) -> dict[str, Any]:
    state = _with_defaults(state)
    store = _get_state_store(state)
    snapshot = store.snapshot()
    completed_phases, pending_phases = _phase_progress(state, "delivery", completed=False)
    summary = (
        f"Synto runtime completed for {state.get('project_id', 'default')}\n"
        f"State root: {state.get('state_root', '')}\n"
        f"Current state: {store.current_state_path}\n"
        f"Events log: {store.events_log_path}\n"
        f"Artifacts: {len(snapshot.get('artifacts', {}))}\n"
        f"Slots: {len(snapshot.get('slots', {}))}\n"
        f"Completed phases: {', '.join(state.get('completed_phases', []))}"
    )
    updates = {
        "current_phase": "delivery",
        "completed_phases": completed_phases,
        "pending_phases": pending_phases,
        "result": summary,
        "events": [_event("delivery", "Final delivery summary prepared")],
    }
    updates.update(_persist_runtime_metadata(state, updates, store))
    return updates


def _quality_route(state: OrchestratorState) -> str:
    route = state.get("phase_route", "approved")
    if route == "retry":
        return "implementation"
    if route == "blocked":
        return "delivery"
    return "release"


def _gate_route(state: OrchestratorState) -> str:
    route = state.get("phase_route", "approved")
    if route == "blocked":
        return "delivery"
    if route == "retry":
        return "retry"
    if route == "skip":
        return "memory_consolidation"
    return route or "delivery"


def build_workflow() -> StateGraph:
    graph = StateGraph(OrchestratorState)

    graph.add_node("intake", intake)
    graph.add_node("memory_rehydration", memory_rehydration)
    graph.add_node("discovery", discovery)
    graph.add_node("discovery_gate", discovery_gate)
    graph.add_node("prd", prd)
    graph.add_node("prd_gate", prd_gate)
    graph.add_node("planning", planning)
    graph.add_node("spec_gate", spec_gate)
    graph.add_node("testing", testing)
    graph.add_node("testing_gate", testing_gate)
    graph.add_node("implementation", implementation)
    graph.add_node("contract_alignment", contract_alignment)
    graph.add_node("contract_gate", contract_gate)
    graph.add_node("review", review)
    graph.add_node("quality_gate", quality_gate)
    graph.add_node("release", release)
    graph.add_node("release_gate", release_gate)
    graph.add_node("deploy_gate", deploy_gate)
    graph.add_node("deploy", deploy)
    graph.add_node("memory_consolidation", memory_consolidation)
    graph.add_node("delivery", delivery)

    graph.set_entry_point("intake")
    graph.add_edge("intake", "memory_rehydration")
    graph.add_edge("memory_rehydration", "discovery")
    graph.add_edge("discovery", "discovery_gate")
    graph.add_conditional_edges(
        "discovery_gate",
        _gate_route,
        {"prd": "prd", "retry": "discovery", "delivery": "delivery"},
    )
    graph.add_edge("prd", "prd_gate")
    graph.add_conditional_edges(
        "prd_gate",
        _gate_route,
        {"planning": "planning", "retry": "prd", "delivery": "delivery"},
    )
    graph.add_edge("planning", "spec_gate")
    graph.add_conditional_edges(
        "spec_gate",
        _gate_route,
        {"testing": "testing", "retry": "planning", "delivery": "delivery"},
    )
    graph.add_edge("testing", "testing_gate")
    graph.add_conditional_edges(
        "testing_gate",
        _gate_route,
        {"implementation": "implementation", "retry": "testing", "delivery": "delivery"},
    )
    graph.add_edge("implementation", "contract_alignment")
    graph.add_edge("contract_alignment", "contract_gate")
    graph.add_conditional_edges(
        "contract_gate",
        _gate_route,
        {"review": "review", "retry": "implementation", "delivery": "delivery"},
    )
    graph.add_edge("review", "quality_gate")
    graph.add_conditional_edges(
        "quality_gate",
        _quality_route,
        {"release": "release", "implementation": "implementation", "delivery": "delivery"},
    )
    graph.add_edge("release", "release_gate")
    graph.add_conditional_edges(
        "release_gate",
        _gate_route,
        {"deploy_gate": "deploy_gate", "retry": "release", "memory_consolidation": "memory_consolidation", "delivery": "delivery"},
    )
    graph.add_conditional_edges(
        "deploy_gate",
        _gate_route,
        {"deploy": "deploy", "retry": "release", "memory_consolidation": "memory_consolidation", "delivery": "delivery"},
    )
    graph.add_edge("deploy", "memory_consolidation")
    graph.add_edge("memory_consolidation", "delivery")
    graph.add_edge("delivery", END)

    return graph


def _create_sqlite_checkpointer(checkpoint_db_path: str) -> SqliteSaver:
    path = Path(checkpoint_db_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path, check_same_thread=False)
    saver = SqliteSaver(conn)
    _CHECKPOINTER_CONNECTIONS.append(conn)
    return saver


def get_compiled(checkpoint_db_path: str | None = None):
    workflow = build_workflow()
    if checkpoint_db_path:
        return workflow.compile(checkpointer=_create_sqlite_checkpointer(checkpoint_db_path))
    return workflow.compile()
