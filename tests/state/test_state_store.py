from __future__ import annotations

import json
from pathlib import Path

import pytest

from synto.state import StateStore

REPO_ROOT = Path(__file__).resolve().parents[2]
REGISTRY_PATH = str(REPO_ROOT / "AGENT-REGISTRY.yaml")


def test_state_store_enforces_slot_ownership(tmp_path):
    store = StateStore("demo-project", root_dir=str(tmp_path / "runtime"), registry_path=REGISTRY_PATH)

    slot = store.write_slot("Planner", "planner_slot", {"output": "plan ready"}, summary="Planner draft")

    assert slot["owner"] == "Planner"
    assert store.get_slot("planner_slot")["data"]["output"] == "plan ready"

    with pytest.raises(PermissionError):
        store.write_slot("Architect", "planner_slot", {"output": "override attempt"})


def test_state_store_versions_artifacts_and_merges_parallel_slots(tmp_path):
    store = StateStore("demo-project", root_dir=str(tmp_path / "runtime"), registry_path=REGISTRY_PATH)

    art_v1 = store.write_artifact("spec", "03-spec", "spec v1", created_by="CodeOrchestrator", summary="first")
    art_v2 = store.write_artifact("spec", "03-spec", "spec v2", created_by="CodeOrchestrator", summary="second")

    assert art_v1["version"] == 1
    assert art_v2["version"] == 2
    assert (tmp_path / "runtime" / "artifacts" / "03-spec" / "spec.v1.md").exists()
    assert (tmp_path / "runtime" / "artifacts" / "03-spec" / "spec.v2.md").exists()
    assert (tmp_path / "runtime" / "artifacts" / "03-spec" / "spec.md").read_text() == "spec v2"

    store.write_slot("Planner", "planner_slot", {"output": "plan"}, summary="planner")
    store.write_slot("Architect", "architect_slot", {"output": "design"}, summary="architect")
    store.append_events([
        {"type": "planning", "summary": "planner finished"},
        {"type": "planning", "summary": "architect finished"},
    ])

    snapshot = json.loads((tmp_path / "runtime" / "state" / "current-state.json").read_text())
    assert set(snapshot["slots"]).issuperset({"planner_slot", "architect_slot"})
    assert snapshot["events_count"] == 2
    assert (tmp_path / "runtime" / "state" / "events.jsonl").exists()
