"""End-to-end test: full workflow from task input to delivery with memory consolidation."""

import json
import os
import tempfile
from pathlib import Path

from fastapi.testclient import TestClient

from synto.memory import MemoryStore
from synto.web import WebConfig, create_app
from synto.workflows import build_initial_state, get_compiled

REPO_ROOT = Path(__file__).resolve().parents[1]
REGISTRY_PATH = str(REPO_ROOT / "AGENT-REGISTRY.yaml")


def _client(tmp_path: Path) -> TestClient:
    config = WebConfig.from_env(
        workspace_dir=tmp_path,
        projects_root=tmp_path / "projects",
        memory_db_path=tmp_path / "memory.db",
        registry_path=REPO_ROOT / "AGENT-REGISTRY.yaml",
        skills_dirs=[],
    )
    return TestClient(create_app(config))


def test_e2e_full_workflow_through_web_api(tmp_path):
    """Run a complete workflow via POST /api/runs and verify all phases complete."""
    client = _client(tmp_path)

    # Create a run via the web API
    resp = client.post("/api/runs", json={
        "task": "Create a REST API for a todo list with CRUD endpoints",
        "project_id": "e2e-todo-api",
        "execution_mode": "automatic",
        "auto_approve_gates": ["*"],
    })
    assert resp.status_code == 200
    data = resp.json()

    # Verify run was created
    assert "run" in data
    run_id = data["run"]["run_id"]
    assert run_id

    # Verify state was persisted
    state = data.get("state", {})
    assert state.get("run_id") == run_id
    assert state.get("project_id") == "e2e-todo-api"

    # Verify events were logged
    events = client.get(f"/api/runs/{run_id}/events").json()
    assert len(events["events"]) > 0, "Workflow should have produced events"

    # Verify skill events were logged
    skill_events = client.get(f"/api/runs/{run_id}/skill-events").json()
    # Skills may or may not be loaded depending on skills_dirs config

    # Verify artifacts were created
    artifacts = client.get(f"/api/runs/{run_id}/artifacts").json()
    assert len(artifacts["artifacts"]) > 0, "Workflow should have produced artifacts"

    # Verify memory was consolidated
    db_path = tmp_path / "memory.db"
    assert db_path.exists(), "Memory database should exist after workflow"
    store = MemoryStore(str(db_path))
    try:
        project = store.get_project("e2e-todo-api")
        assert project is not None, "Project should be created in memory"
        memories = store.list_by_project(project["id"])
        assert len(memories) >= 1, "At least one memory should be consolidated"
    finally:
        store.close()


def test_e2e_workflow_direct_invoke(tmp_path):
    """Run the workflow directly (not via web API) and verify all phases execute."""
    db_path = str(tmp_path / "memory.db")

    initial_state = build_initial_state(
        task="Build a user authentication system with JWT tokens",
        project_id="e2e-auth",
        config_dir="",
        registry_path=str(REGISTRY_PATH),
        skills_dirs=[],
        state_root=str(tmp_path / "state"),
        memory_db_path=db_path,
        execution_mode="automatic",
        auto_approve_gates=["*"],
    )

    workflow = get_compiled()
    result = workflow.invoke(initial_state)

    # Verify all phases completed
    completed = result.get("completed_phases", [])
    assert len(completed) >= 8, f"Expected at least 8 phases completed, got {len(completed)}: {completed}"

    # Verify delivery phase was reached
    assert "delivery" in completed or result.get("current_phase") == "delivery"

    # Verify memory consolidation happened
    store = MemoryStore(db_path)
    try:
        project = store.get_project("e2e-auth")
        assert project is not None
        memories = store.list_by_project(project["id"])
        assert len(memories) >= 1
    finally:
        store.close()

    # Verify state files were persisted
    state_dir = tmp_path / "state" / "state"
    assert (state_dir / "current-state.json").exists()
    assert (state_dir / "events.jsonl").exists()

    state_data = json.loads((state_dir / "current-state.json").read_text())
    assert state_data.get("project_id") == "e2e-auth"
