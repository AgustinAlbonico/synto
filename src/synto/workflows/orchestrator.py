"""LangGraph runtime — complete orchestrator workflow with all nodes."""

from __future__ import annotations

import time
from typing import TypedDict, Annotated, Optional, Any
import operator

from langgraph.graph import StateGraph, END

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


# --- Node functions ---

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

    # Try to build memory context
    try:
        db_path = f"memory_{project_id}.db"
        store = MemoryStore(db_path)
        context_agent = MemoryContextAgent(store)
        pack_builder = MemoryPackBuilder()

        task_ctx = TaskContext(task=task, project_id=project_id)

        # Global context
        global_ctx = context_agent.get_global_context(project_id, limit=5)

        # Agent packs (for known agent roles)
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
    mem = state.get("memory_pack_global", {})
    mem_info = f" ({len(mem.get('context', []))} memories found)" if mem else ""

    discovery_out = (
        f"Discovery for: {state.get('task', 'no task')}\n"
        f"Project: {state.get('project_id', 'default')}\n"
        f"Memory context loaded: {bool(mem)}{mem_info}\n"
        f"Status: discovery complete (mock)"
    )
    return {
        "discovery_output": discovery_out,
        "events": [{"type": "discovery", "ts": time.time()}],
        "errors": [],
    }


def planning(state: OrchestratorState) -> dict:
    """Create a detailed implementation plan."""
    plan = (
        f"Plan for: {state.get('task', 'no task')}\n"
        f"1. Analyze requirements from discovery\n"
        f"2. Design architecture\n"
        f"3. Implement components\n"
        f"4. Write tests\n"
        f"5. Review and finalize\n"
        f"Status: planning complete (mock)"
    )
    return {
        "plan": plan,
        "events": [{"type": "planning", "ts": time.time()}],
        "errors": [],
    }


def implementation(state: OrchestratorState) -> dict:
    """Execute the plan — create code, configs, etc."""
    output = (
        f"Implementation for: {state.get('task', 'no task')}\n"
        f"Plan: {state.get('plan', 'no plan')[:100]}...\n"
        f"Status: implementation complete (mock)"
    )
    return {
        "implementation_output": output,
        "events": [{"type": "implementation", "ts": time.time()}],
        "errors": [],
    }


def testing(state: OrchestratorState) -> dict:
    """Run tests and validate output."""
    results = (
        f"Testing for: {state.get('task', 'no task')}\n"
        f"Tests: 0/0 run (mock)\n"
        f"Status: testing complete (mock)"
    )
    return {
        "test_results": results,
        "events": [{"type": "testing", "ts": time.time()}],
        "errors": [],
    }


def quality_gate(state: OrchestratorState) -> dict:
    """Evaluate quality gates. Decide if we proceed or retry."""
    has_plan = bool(state.get("plan"))
    has_impl = bool(state.get("implementation_output"))
    has_tests = bool(state.get("test_results"))

    passed = has_plan and has_impl and has_tests
    errors = []
    if not has_plan:
        errors.append("no plan")
    if not has_impl:
        errors.append("no implementation")
    if not has_tests:
        errors.append("no test results")

    return {
        "gate_passed": passed,
        "gate_errors": errors,
        "events": [{"type": "quality_gate", "passed": passed, "errors": errors, "ts": time.time()}],
        "errors": [],
    }


def memory_consolidation(state: OrchestratorState) -> dict:
    """Save learnings back to MemoryStore."""
    try:
        import tempfile as _tf
        project_id = state.get("project_id", "default")
        db_path = _tf.mktemp(suffix="_memory.db")
        store = MemoryStore(db_path)
        # Create project if not exists (needed when DB is fresh)
        store.create_project(project_id, project_id)

        mgr = MemoryManager(store)

        # Create candidates from run outputs
        candidates = []
        if state.get("plan"):
            candidates.append(MemoryCandidate(
                kind=MemoryKind.DECISION,
                title="Run plan",
                content=state["plan"],
                project_id=project_id,
                source_agent="planner-agent",
            ))
        if state.get("implementation_output"):
            candidates.append(MemoryCandidate(
                kind=MemoryKind.SOLUTION,
                title="Run implementation",
                content=state["implementation_output"][:500],
                project_id=project_id,
                source_agent="implementer-agent",
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
    """Build the full orchestration workflow.

    Phases:
      1. intake
      2. memory_rehydration
      3. discovery
      4. planning
      5. implementation
      6. testing
      7. quality_gate (conditional: retry → discovery or proceed)
      8. memory_consolidation
      9. delivery
    """
    workflow = StateGraph(OrchestratorState)

    # Add nodes
    workflow.add_node("intake", intake)
    workflow.add_node("memory_rehydration", memory_rehydration)
    workflow.add_node("discovery", discovery)
    workflow.add_node("planning", planning)
    workflow.add_node("implementation", implementation)
    workflow.add_node("testing", testing)
    workflow.add_node("quality_gate", quality_gate)
    workflow.add_node("memory_consolidation", memory_consolidation)
    workflow.add_node("delivery", delivery)

    # Entry
    workflow.set_entry_point("intake")

    # Linear flow
    workflow.add_edge("intake", "memory_rehydration")
    workflow.add_edge("memory_rehydration", "discovery")
    workflow.add_edge("discovery", "planning")
    workflow.add_edge("planning", "implementation")
    workflow.add_edge("implementation", "testing")
    workflow.add_edge("testing", "quality_gate")

    # Conditional retry
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
