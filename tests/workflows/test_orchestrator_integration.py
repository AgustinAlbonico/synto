"""Additional workflow integration tests for shared state and memory persistence."""

import os
import tempfile

from synto.memory import MemoryStore
from synto.workflows import build_workflow


def _initial_state(memory_db_path: str) -> dict:
    return {
        "task": "Build a login API endpoint",
        "project_id": "test-project",
        "memory_db_path": memory_db_path,
        "config_dir": "",
        "shared_state_snapshot": {},
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


def test_workflow_populates_shared_state_snapshot():
    workflow = build_workflow().compile()
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name

    try:
        result = workflow.invoke(_initial_state(db_path))
        snapshot = result["shared_state_snapshot"]

        assert snapshot["task"] == "Build a login API endpoint"
        assert snapshot["project_id"] == "test-project"
        assert "discovery.output" in snapshot
        assert "planning.plan" in snapshot
        assert "implementation.agent" in snapshot
        assert "testing.results" in snapshot
        assert "quality.gate_passed" in snapshot
        assert "memory.last_consolidation" in snapshot
    finally:
        os.unlink(db_path)


def test_workflow_persists_memory_consolidation_to_same_db():
    workflow = build_workflow().compile()
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name

    try:
        workflow.invoke(_initial_state(db_path))

        store = MemoryStore(db_path)
        project = store.get_project("test-project")
        assert project is not None
        memories = store.list_by_project(project["id"])
        store.close()

        assert len(memories) >= 1
    finally:
        os.unlink(db_path)
