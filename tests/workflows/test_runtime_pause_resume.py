from __future__ import annotations

import json
from pathlib import Path

from langgraph.types import Command

from synto.workflows import build_initial_state, get_compiled


def test_runtime_interrupts_and_resumes_with_sqlite_checkpointer(tmp_path):
    checkpoint_db = tmp_path / "checkpoints.sqlite"
    state_root = tmp_path / "state-root"
    compiled = get_compiled(str(checkpoint_db))

    initial_state = build_initial_state(
        "Build a login API endpoint",
        project_id="runtime-demo",
        state_root=str(state_root),
        checkpoint_db_path=str(checkpoint_db),
        execution_mode="interactive",
        auto_approve_gates=["discovery_gate", "spec_gate", "testing_gate", "contract_gate", "release_gate", "deploy_gate"],
    )
    config = {"configurable": {"thread_id": "runtime-demo-thread"}}

    first = compiled.invoke(initial_state, config=config)

    assert "__interrupt__" in first
    interrupt_payload = first["__interrupt__"][0].value
    assert interrupt_payload["gate"] == "prd_gate"
    assert checkpoint_db.exists()

    resumed = compiled.invoke(Command(resume={"approved": True, "notes": "PRD ok"}), config=config)

    assert resumed["current_phase"] == "delivery"

    current_state = json.loads((state_root / "state" / "current-state.json").read_text())
    assert current_state["approvals"]["prd_gate"]["status"] == "approved"
    assert current_state["gates"]["prd_gate"]["status"] == "passed"
    assert current_state["thread_id"] == "runtime-demo-thread"
    assert current_state["workflow"]["current_phase"] == "delivery"


def test_runtime_persists_ui_ready_state_and_artifacts(tmp_path):
    state_root = tmp_path / "state-root"
    compiled = get_compiled()
    initial_state = build_initial_state(
        "Build a login API endpoint",
        project_id="runtime-demo",
        state_root=str(state_root),
    )

    result = compiled.invoke(initial_state)

    assert result["current_phase"] == "delivery"

    current_state_path = state_root / "state" / "current-state.json"
    events_log_path = state_root / "state" / "events.jsonl"
    assert current_state_path.exists()
    assert events_log_path.exists()

    current_state = json.loads(current_state_path.read_text())
    assert set(current_state["slots"]).issuperset({"business_analyst_slot", "planner_slot", "backend_implementer_slot", "technical_writer_slot"})
    assert set(current_state["artifacts"]).issuperset({"prd", "spec", "test_plan", "release_notes", "docs"})
    assert not ({"gate_statuses", "pull_request", "api_contract_actual"} & set(current_state["artifacts"]))
    assert "deploy" not in set(current_state["workflow"]["pending_phases"])
    assert set(current_state["workflow"]["completed_phases"]).issuperset({"spec_consolidation", "review", "qa_docs", "release"})

    event_lines = [line for line in events_log_path.read_text().splitlines() if line.strip()]
    assert len(event_lines) >= 10
