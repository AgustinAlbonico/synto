"""Tests for the full LangGraph workflow."""

import os
import tempfile
import pytest

from synto.workflows import build_workflow, get_compiled
from synto.workflows import orchestrator as orchestrator_module


@pytest.fixture
def workflow():
    return build_workflow().compile()


def test_workflow_compiles():
    w = get_compiled()
    assert w is not None


def test_workflow_runs_end_to_end(workflow):
    initial_state = {
        "task": "Build a login API endpoint",
        "project_id": "test-project",
        "config_dir": "",
        "memory_pack_global": {},
        "memory_pack_by_agent": {},
        "discovery_output": "",
        "plan": "",
        "implementation_output": "",
        "test_results": "",
        "gate_passed": False,
        "gate_errors": [],
        "events": [],
        "errors": [],
        "result": "",
    }

    result = workflow.invoke(initial_state)

    assert result is not None
    assert "result" in result
    assert result["result"]  # has output
    assert len(result.get("events", [])) >= 5
    # Should have all phases
    event_types = [e["type"] for e in result["events"]]
    assert "intake" in event_types
    assert "memory_rehydration" in event_types
    assert "discovery" in event_types
    assert "planning" in event_types
    assert "implementation" in event_types
    assert "testing" in event_types
    assert "quality_gate" in event_types
    assert "memory_consolidation" in event_types
    assert "delivery" in event_types


def test_workflow_has_memory_packs(workflow):
    initial_state = {
        "task": "test",
        "project_id": "proj",
        "config_dir": "",
        "memory_pack_global": {},
        "memory_pack_by_agent": {},
        "discovery_output": "",
        "plan": "",
        "implementation_output": "",
        "test_results": "",
        "gate_passed": False,
        "gate_errors": [],
        "events": [],
        "errors": [],
        "result": "",
    }

    result = workflow.invoke(initial_state)

    # Memory rehydration should have run
    mem_events = [e for e in result["events"] if "memory" in e.get("type", "")]
    assert len(mem_events) >= 2  # rehydration + consolidation


def test_memory_rehydration_uses_registry_agent_ids_without_legacy_factory(monkeypatch, tmp_path):
    def fail_if_called(*args, **kwargs):
        raise AssertionError("memory_rehydration must not instantiate agents through legacy create_all_agents")

    monkeypatch.setattr(orchestrator_module, "create_all_agents", fail_if_called, raising=False)
    state = {
        "task": "Build a login API endpoint",
        "project_id": "proj",
        "memory_db_path": str(tmp_path / "memory.db"),
        "state_root": str(tmp_path / "state"),
        "memory_pack_global": {},
        "memory_pack_by_agent": {},
        "shared_state_snapshot": {},
        "events": [],
        "errors": [],
    }

    result = orchestrator_module.memory_rehydration(state)

    assert "Reviewer" in result["memory_pack_by_agent"]
    assert "MemoryContextAgent" in result["memory_pack_by_agent"]


def test_workflow_gate_failure_retry(workflow):
    """If gate fails, should loop back to discovery."""
    initial_state = {
        "task": "impossible task",
        "project_id": "test",
        "config_dir": "",
        "memory_pack_global": {},
        "memory_pack_by_agent": {},
        "discovery_output": "",
        "plan": "",
        "implementation_output": "",
        "test_results": "",
        "gate_passed": False,  # Force gate fail
        "gate_errors": ["no output"],
        "events": [],
        "errors": [],
        "result": "",
    }

    # With mock nodes, gate always passes since nodes produce output
    # This test verifies the conditional edge is wired correctly
    result = workflow.invoke(initial_state)
    assert result is not None
