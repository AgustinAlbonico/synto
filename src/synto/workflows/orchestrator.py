"""LangGraph runtime — complete orchestrator workflow with all nodes."""

from __future__ import annotations

import os
import time
from typing import TypedDict, Annotated, Optional, Any
import operator

from langgraph.graph import StateGraph, END

from synto.config.llm_router import LLMMultiProvider
from synto.agents import (
    DiscoveryAgent, PlannerAgent, ImplementerAgent,
    TesterAgent, QAGateAgent, AgentResult,
)
from synto.memory import (
    MemoryStore, MemoryContextAgent, MemoryManager,
    MemoryPackBuilder, TaskContext, MemoryCandidate, MemoryKind,
)
from synto.state import SharedState


# --- Graph State ---

class OrchestratorState(TypedDict):
    """State flowing through the LangGraph workflow."""
    # Input
    task: str
    project_id: str
    # LLM router config
    config_dir: str
    # Memory
    memory_pack_global: dict[str, Any]
    memory_pack_by_agent: dict[str, Any]
    # Work products
    discovery_output: str
    plan: str
    implementation_output: str
    test_results: str
    # Quality
    gate_passed: bool
    gate_errors: list[str]
    # Audit (accumulated)
    events: Annotated[list[dict], operator.add]
    errors: Annotated[list[str], operator.add]
    # Output
    result: str


# --- LLM Router (global per run) ---

_router: LLMMultiProvider | None = None


def _get_router(config_dir: str) -> LLMMultiProvider:
    global _router
    if _router is None and os.path.isdir(config_dir):
        _router = LLMMultiProvider(config_dir)
    elif _router is None:
        _router = LLMMultiProvider()
    return _router


def _reset_router():
    global _router
    _router = None


# --- Node functions ---

def _memory_text(state: OrchestratorState) -> str:
    mem = state.get("memory_pack_global", {})
    ctx = mem.get("context", [])
    if not ctx:
        return ""
    parts = []
    for item in ctx:
        if isinstance(item, dict):
            parts.append(f"- [{item.get('kind', '')}] {item.get('content', '')[:200]}")
        else:
            parts.append(f"- {str(item)[:200]}")
    return "\n".join(parts)


def intake(state: OrchestratorState) -> dict:
    """Validate and normalize input."""
    return {
        "events": [{"type": "intake", "task": state.get("task", ""), "ts": time.time()}],
        "errors": [],
        "discovery_output": "",
        "plan": "",
        "implementation_output": "",
        "test_results": "",
        "gate_passed": False,
        "gate_errors": [],
        "result": "",
        "memory_pack_global": {},
        "memory_pack_by_agent": {},
    }


def memory_rehydration(state: OrchestratorState) -> dict:
    """Load relevant memories for the current project/task."""
    task = state.get("task", "")
    project_id = state.get("project_id", "default")

    try:
        db_path = f"memory_{project_id}.db"
        store = MemoryStore(db_path)
        context_agent = MemoryContextAgent(store)
        pack_builder = MemoryPackBuilder()

        task_ctx = TaskContext(task=task, project_id=project_id)
        global_ctx = context_agent.get_global_context(project_id, limit=5)
        agents = ["discovery-agent", "planner-agent", "implementer-agent", "tester-agent"]
        packs = context_agent.hydrate(task_ctx, agents, token_budget=3000)
        store.close()

        return {
            "memory_pack_global": {"context": global_ctx, "project": project_id},
            "memory_pack_by_agent": {aid: {"items": len(p.items), "tokens": p.total_tokens_estimate} for aid, p in packs.items()},
            "events": [{"type": "memory_rehydration", "packs": len(packs), "ts": time.time()}],
            "errors": [],
        }
    except Exception as e:
        return {
            "events": [{"type": "memory_rehydration_error", "error": str(e), "ts": time.time()}],
            "errors": [f"memory_rehydration: {e}"],
        }


def discovery(state: OrchestratorState) -> dict:
    """Understand the task, gather context, identify constraints."""
    mem_text = _memory_text(state)
    router = _get_router(state.get("config_dir", ""))
    agent = DiscoveryAgent(router=router, memory_context=mem_text)
    extra = f"Project ID: {state.get('project_id', 'default')}"

    try:
        result = agent.generate(state.get("task", ""))
        return {
            "discovery_output": result.output,
            "events": [{"type": "discovery", "model": result.model, "provider": result.provider, "ts": time.time()}],
            "errors": [],
        }
    except Exception as e:
        # Fallback to mock if LLM unavailable
        return {
            "discovery_output": (
                f"Discovery for: {state.get('task', 'no task')}\n"
                f"Project: {state.get('project_id', 'default')}\n"
                f"[LLM unavailable, using mock]\n"
                f"Status: discovery complete"
            ),
            "events": [{"type": "discovery", "model": agent.resolve_model(), "provider": "none", "fallback": True, "ts": time.time()}],
            "errors": [f"discovery LLM error: {e}"],
        }


def planning(state: OrchestratorState) -> dict:
    """Create a detailed implementation plan."""
    router = _get_router(state.get("config_dir", ""))
    agent = PlannerAgent(router=router, memory_context=_memory_text(state))

    task_input = (
        f"Task: {state.get('task', '')}\n\n"
        f"Discovery:\n{state.get('discovery_output', '')}"
    )

    try:
        result = agent.generate(task_input)
        return {
            "plan": result.output,
            "events": [{"type": "planning", "model": result.model, "provider": result.provider, "ts": time.time()}],
            "errors": [],
        }
    except Exception as e:
        return {
            "plan": (
                f"Plan for: {state.get('task', 'no task')}\n"
                f"1. Analyze requirements from discovery\n"
                f"2. Design architecture\n"
                f"3. Implement components\n"
                f"4. Write tests\n"
                f"5. Review and finalize\n"
                f"[LLM unavailable, using mock]"
            ),
            "events": [{"type": "planning", "model": agent.resolve_model(), "provider": "none", "fallback": True, "ts": time.time()}],
            "errors": [f"planning LLM error: {e}"],
        }


def implementation(state: OrchestratorState) -> dict:
    """Execute the plan — create code, configs, etc."""
    router = _get_router(state.get("config_dir", ""))
    agent = ImplementerAgent(router=router, memory_context=_memory_text(state))

    task_input = (
        f"Task: {state.get('task', '')}\n\n"
        f"Plan:\n{state.get('plan', '')}"
    )

    try:
        result = agent.generate(task_input)
        return {
            "implementation_output": result.output,
            "events": [{"type": "implementation", "model": result.model, "provider": result.provider, "ts": time.time()}],
            "errors": [],
        }
    except Exception as e:
        return {
            "implementation_output": f"[LLM unavailable] Would implement: {state.get('task', '')[:100]}",
            "events": [{"type": "implementation", "model": agent.resolve_model(), "provider": "none", "fallback": True, "ts": time.time()}],
            "errors": [f"implementation LLM error: {e}"],
        }


def testing(state: OrchestratorState) -> dict:
    """Run tests and validate output."""
    router = _get_router(state.get("config_dir", ""))
    agent = TesterAgent(router=router, memory_context=_memory_text(state))

    task_input = (
        f"Task: {state.get('task', '')}\n\n"
        f"Implementation:\n{state.get('implementation_output', '')[:2000]}"
    )

    try:
        result = agent.generate(task_input)
        return {
            "test_results": result.output,
            "events": [{"type": "testing", "model": result.model, "provider": result.provider, "ts": time.time()}],
            "errors": [],
        }
    except Exception as e:
        return {
            "test_results": f"[LLM unavailable] Would test: {state.get('task', '')[:100]}",
            "events": [{"type": "testing", "model": agent.resolve_model(), "provider": "none", "fallback": True, "ts": time.time()}],
            "errors": [f"testing LLM error: {e}"],
        }


def quality_gate(state: OrchestratorState) -> dict:
    """Evaluate quality gates. Decide if we proceed or retry."""
    router = _get_router(state.get("config_dir", ""))
    agent = QAGateAgent(router=router)

    has_plan = bool(state.get("plan"))
    has_impl = bool(state.get("implementation_output"))
    has_tests = bool(state.get("test_results"))

    gate_input = (
        f"Task: {state.get('task', '')}\n\n"
        f"Plan:\n{state.get('plan', '')[:2000]}\n\n"
        f"Implementation:\n{state.get('implementation_output', '')[:2000]}\n\n"
        f"Tests:\n{state.get('test_results', '')[:2000]}"
    )

    try:
        result = agent.generate(gate_input)
        passed = "PASSED" in result.output.upper() and "FAILED" not in result.output.upper().split("PASSED")[0]
        return {
            "gate_passed": passed,
            "gate_errors": [] if passed else [result.output[:200]],
            "events": [{"type": "quality_gate", "passed": passed, "model": result.model, "provider": result.provider, "ts": time.time()}],
            "errors": [],
        }
    except Exception as e:
        # Fallback: structural check
        errors = []
        if not has_plan: errors.append("no plan")
        if not has_impl: errors.append("no implementation")
        if not has_tests: errors.append("no test results")
        return {
            "gate_passed": len(errors) == 0,
            "gate_errors": errors,
            "events": [{"type": "quality_gate", "passed": len(errors) == 0, "fallback": True, "ts": time.time()}],
            "errors": [],
        }


def memory_consolidation(state: OrchestratorState) -> dict:
    """Save learnings back to MemoryStore."""
    try:
        import tempfile as _tf
        project_id = state.get("project_id", "default")
        db_path = _tf.mktemp(suffix="_memory.db")
        store = MemoryStore(db_path)
        store.create_project(project_id, project_id)

        mgr = MemoryManager(store)
        candidates = []
        if state.get("plan"):
            candidates.append(MemoryCandidate(
                kind=MemoryKind.DECISION,
                title="Run plan",
                content=state["plan"],
                project_id=project_id,
                source_agent="PlannerAgent",
            ))
        if state.get("implementation_output"):
            candidates.append(MemoryCandidate(
                kind=MemoryKind.SOLUTION,
                title="Run implementation",
                content=state["implementation_output"][:500],
                project_id=project_id,
                source_agent="ImplementerAgent",
            ))

        summary = mgr.consolidate_run(candidates, actor="orchestrator")
        store.close()

        return {
            "events": [{"type": "memory_consolidation", "summary": summary, "ts": time.time()}],
            "errors": [],
        }
    except Exception as e:
        return {
            "events": [{"type": "memory_consolidation_error", "error": str(e), "ts": time.time()}],
            "errors": [f"memory_consolidation: {e}"],
        }


def delivery(state: OrchestratorState) -> dict:
    """Produce final result."""
    result = (
        f"=== Run Complete ===\n"
        f"Task: {state.get('task', 'no task')}\n"
        f"Plan: {state.get('plan', '')[:200]}\n"
        f"Implementation: {state.get('implementation_output', '')[:200]}\n"
        f"Tests: {state.get('test_results', '')}\n"
        f"Gate: {'PASSED' if state.get('gate_passed') else 'FAILED'}\n"
        f"Gate errors: {state.get('gate_errors', [])}"
    )
    return {
        "result": result,
        "events": [{"type": "delivery", "ts": time.time()}],
        "errors": [],
    }


# --- Graph builder ---

def build_workflow() -> StateGraph:
    """Build the full orchestration workflow."""
    workflow = StateGraph(OrchestratorState)

    workflow.add_node("intake", intake)
    workflow.add_node("memory_rehydration", memory_rehydration)
    workflow.add_node("discovery", discovery)
    workflow.add_node("planning", planning)
    workflow.add_node("implementation", implementation)
    workflow.add_node("testing", testing)
    workflow.add_node("quality_gate", quality_gate)
    workflow.add_node("memory_consolidation", memory_consolidation)
    workflow.add_node("delivery", delivery)

    workflow.set_entry_point("intake")

    workflow.add_edge("intake", "memory_rehydration")
    workflow.add_edge("memory_rehydration", "discovery")
    workflow.add_edge("discovery", "planning")
    workflow.add_edge("planning", "implementation")
    workflow.add_edge("implementation", "testing")
    workflow.add_edge("testing", "quality_gate")

    workflow.add_conditional_edges(
        "quality_gate",
        lambda s: "memory_consolidation" if s.get("gate_passed", False) else "discovery",
        {
            "memory_consolidation": "memory_consolidation",
            "discovery": "discovery",
        },
    )

    workflow.add_edge("memory_consolidation", "delivery")
    workflow.add_edge("delivery", END)

    return workflow


def get_compiled():
    """Return a compiled workflow ready to run."""
    return build_workflow().compile()
