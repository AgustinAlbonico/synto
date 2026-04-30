from __future__ import annotations

import json
from pathlib import Path

from fastapi.testclient import TestClient

from synto.web import WebConfig, create_app

REPO_ROOT = Path(__file__).resolve().parents[2]
REGISTRY_PATH = REPO_ROOT / "AGENT-REGISTRY.yaml"


def _client(tmp_path: Path, skills_dirs: list[Path] | None = None) -> TestClient:
    config = WebConfig.from_env(
        workspace_dir=tmp_path,
        projects_root=tmp_path / "projects",
        memory_db_path=tmp_path / "memory.db",
        registry_path=REGISTRY_PATH,
        skills_dirs=skills_dirs or [],
    )
    return TestClient(create_app(config))


def _write_run(projects_root: Path) -> Path:
    root = projects_root / "synto"
    state_dir = root / "state"
    artifact_dir = root / "artifacts" / "02-prd"
    state_dir.mkdir(parents=True)
    artifact_dir.mkdir(parents=True)
    artifact_path = artifact_dir / "prd.md"
    artifact_path.write_text("# PRD\n\nShip the web UI.")
    snapshot = {
        "run_id": "run-1",
        "thread_id": "thread-1",
        "project_id": "synto",
        "checkpoint_db_path": str(state_dir / "checkpoints.sqlite"),
        "state_root": str(root),
        "workflow": {
            "current_phase": "prd",
            "completed_phases": ["intake", "discovery"],
            "pending_phases": ["prd", "technical_planning"],
        },
        "shared_state": {"task": "Build UI"},
        "slots": {"product_manager_slot": {"owner": "ProductManager"}},
        "artifacts": {
            "prd": {
                "path": str(artifact_path),
                "version": 1,
                "kind": "markdown",
                "status": "draft",
                "created_by": "ProductManager",
                "summary": "Product requirements",
            }
        },
        "gates": {"prd_gate": {"status": "pending"}},
        "approvals": {"prd_gate": {"status": "pending", "requested_by": "ProductManager"}},
        "events_count": 1,
        "last_event": {"type": "prd_gate", "summary": "Gate awaiting approval"},
        "skill_events_count": 1,
        "last_skill_event": {"type": "skill_loaded", "agent": "ProductManager", "skill": "writing-plans"},
        "last_updated_at": "2026-04-29T00:00:00+00:00",
    }
    (state_dir / "current-state.json").write_text(json.dumps(snapshot))
    (state_dir / "events.jsonl").write_text(json.dumps({"type": "prd_gate", "summary": "Gate awaiting approval"}) + "\n")
    (state_dir / "skill-load-events.jsonl").write_text(
        json.dumps({"type": "skill_loaded", "agent": "ProductManager", "skill": "writing-plans"}) + "\n"
    )
    return root


def test_web_health_and_static_index(tmp_path):
    client = _client(tmp_path)

    health = client.get("/api/health")
    assert health.status_code == 200
    assert health.json()["ok"] is True

    index = client.get("/")
    assert index.status_code == 200
    assert "Synto Command Center" in index.text


def test_runs_artifacts_events_and_registry_contract(tmp_path):
    _write_run(tmp_path / "projects")
    client = _client(tmp_path)

    runs = client.get("/api/runs").json()
    assert runs["totals"]["waiting_approval"] == 1
    assert runs["runs"][0]["run_id"] == "run-1"

    detail = client.get("/api/runs/run-1").json()
    assert detail["run"]["status"] == "waiting_approval"
    assert detail["events"][0]["type"] == "prd_gate"
    assert detail["skill_events"][0]["skill"] == "writing-plans"

    skill_events = client.get("/api/runs/run-1/skill-events").json()
    assert skill_events["events"][0]["agent"] == "ProductManager"

    artifact = client.get("/api/runs/run-1/artifacts/prd").json()
    assert "Ship the web UI" in artifact["content"]

    agents = client.get("/api/agents").json()
    assert agents["count"] >= 19
    assert any(agent["id"] == "FrontendImplementer" for agent in agents["agents"])


def test_skills_endpoint_discovers_skill_metadata(tmp_path):
    skills_root = tmp_path / "skills"
    skill_dir = skills_root / "web-cockpit"
    skill_dir.mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text(
        "---\nname: web-cockpit\ndescription: Build cockpit UIs\ntags: [web, ui]\n---\n# Web Cockpit\n"
    )
    client = _client(tmp_path, [skills_root])

    skills = client.get("/api/skills").json()
    assert skills["count"] == 1
    assert skills["skills"][0]["name"] == "web-cockpit"

    content = client.get("/api/skills/web-cockpit").json()
    assert "Build cockpit UIs" in content["metadata"]["description"]


def test_create_run_and_resume_use_checkpoint_contract(tmp_path, monkeypatch):
    import synto.web.app as web_app

    class FakeInterrupt:
        def __init__(self, value):
            self.value = value

    class FakeWorkflow:
        def __init__(self, checkpoint_db):
            self.checkpoint_db = checkpoint_db

        def invoke(self, payload, config=None):
            checkpoint_db = Path(self.checkpoint_db)
            state_root = checkpoint_db.parents[1]
            state_dir = state_root / "state"
            state_dir.mkdir(parents=True, exist_ok=True)
            if isinstance(payload, dict):
                snapshot = {
                    "run_id": payload["run_id"],
                    "thread_id": payload["thread_id"],
                    "project_id": payload["project_id"],
                    "checkpoint_db_path": payload["checkpoint_db_path"],
                    "workflow": {"current_phase": "prd", "completed_phases": ["intake", "discovery"], "pending_phases": ["prd"]},
                    "shared_state": {"task": payload["task"]},
                    "selected_model": payload.get("selected_model"),
                    "orchestrator_model": payload.get("orchestrator_model"),
                    "workspace_paths": payload.get("workspace_paths", []),
                    "technology_stack": payload.get("technology_stack", {}),
                    "slots": {},
                    "artifacts": {},
                    "gates": {"prd_gate": {"status": "pending"}},
                    "approvals": {"prd_gate": {"status": "pending", "requested_by": "ProductManager"}},
                    "events_count": 1,
                    "last_event": {"type": "prd_gate", "summary": "Gate awaiting approval"},
                }
                (state_dir / "current-state.json").write_text(json.dumps(snapshot))
                (state_dir / "events.jsonl").write_text(json.dumps(snapshot["last_event"]) + "\n")
                return {"__interrupt__": [FakeInterrupt({"gate": "prd_gate"})]}

            snapshot = json.loads((state_dir / "current-state.json").read_text())
            snapshot["workflow"]["current_phase"] = "delivery"
            snapshot["workflow"]["completed_phases"].append("prd")
            snapshot["workflow"]["pending_phases"] = []
            snapshot["approvals"]["prd_gate"]["status"] = "approved"
            snapshot["gates"]["prd_gate"]["status"] = "passed"
            (state_dir / "current-state.json").write_text(json.dumps(snapshot))
            return snapshot

    monkeypatch.setattr(web_app, "get_compiled", lambda checkpoint_db=None: FakeWorkflow(checkpoint_db))
    client = _client(tmp_path)

    created = client.post(
        "/api/runs",
        json={"project_id": "synto", "task": "Build UI", "model": "openai/gpt-5.5", "workspace_paths": [str(tmp_path)]},
    ).json()
    assert created["status"] == "waiting_approval"
    assert created["interrupt"]["gate"] == "prd_gate"
    assert created["state"]["selected_model"] == "openai/gpt-5.5"
    assert created["state"]["workspace_paths"] == [str(tmp_path)]

    run_id = created["run"]["run_id"]
    resumed = client.post(f"/api/runs/{run_id}/resume", json={"action": "approve", "notes": "ok"}).json()
    assert resumed["run"]["status"] == "completed"
    assert resumed["state"]["workflow"]["current_phase"] == "delivery"


def test_setup_endpoints_scan_settings_and_prompt_improve(tmp_path):
    (tmp_path / "package.json").write_text(json.dumps({"dependencies": {"react": "latest", "vite": "latest", "typescript": "latest"}}))
    (tmp_path / "tsconfig.json").write_text("{}")
    client = _client(tmp_path)

    scanned = client.post("/api/workspaces/scan", json={"name": "Synto UI", "paths": [str(tmp_path)]})
    assert scanned.status_code == 200
    stack_names = {item["name"] for item in scanned.json()["stack"]["items"]}
    assert {"React", "Vite", "TypeScript"}.issubset(stack_names)

    saved = client.put(
        "/api/app-settings",
        json={
            "selected_model": "openai/gpt-5.5",
            "orchestrator_model": "openai/gpt-5.5",
            "agent_models": {"FrontendImplementer": "openai/gpt-5.5"},
            "selected_workspace": scanned.json()["workspace"],
        },
    )
    assert saved.status_code == 200
    assert saved.json()["settings"]["selected_model"] == "openai/gpt-5.5"
    assert (tmp_path / ".synto" / "models.yaml").exists()

    improved = client.post(
        "/api/prompt/improve",
        json={"prompt": "Mejorá la UI", "workspace": scanned.json()["workspace"], "stack": scanned.json()["stack"]},
    ).json()
    assert "Criterios de aceptación" in improved["improved_prompt"]
    assert "React" in improved["improved_prompt"]
