"""Code-domain workflow integration with OpenCode-backed agent sessions."""

from pathlib import Path

from synto.runtime import AgentRunResult
from synto.workflows import build_workflow
from synto.workflows import orchestrator as orchestrator_module


def _base_state(tmp_path: Path, workspace: Path, *, domain: str = "code") -> dict:
    return {
        "task": "Build a login API endpoint",
        "project_id": "proj",
        "domain": domain,
        "opencode_enabled": True,
        "workspace_paths": [str(workspace)],
        "state_root": str(tmp_path / "state"),
        "run_id": "run123",
        "memory_pack_global": {},
        "memory_pack_by_agent": {},
        "shared_state_snapshot": {},
        "phase_outputs": {},
        "events": [],
        "errors": [],
        "plan": "Spec: add login endpoint",
        "test_plan": "",
        "implementation_output": "",
        "gate_errors": [],
        "result": "",
    }


def _fake_result(spec, *, files_changed=("tests/test_login.py",)) -> AgentRunResult:
    output_dir = Path(spec.workdir) / ".synto" / "runs" / spec.run_id / "opencode" / spec.agent_id
    output_dir.mkdir(parents=True, exist_ok=True)
    patch_dir = Path(spec.workdir) / ".synto" / "runs" / spec.run_id / "patches"
    patch_dir.mkdir(parents=True, exist_ok=True)
    stdout_path = output_dir / "stdout.txt"
    stderr_path = output_dir / "stderr.txt"
    events_path = output_dir / "events.jsonl"
    patch_path = patch_dir / f"{spec.agent_id}.patch"
    stdout_path.write_text(f"{spec.agent_id} done", encoding="utf-8")
    stderr_path.write_text("", encoding="utf-8")
    events_path.write_text("{}\n", encoding="utf-8")
    patch_path.write_text("diff --git", encoding="utf-8")
    return AgentRunResult(
        run_id=spec.run_id,
        agent_id=spec.agent_id,
        task_id=spec.task_id,
        status="success",
        exit_code=0,
        files_changed=tuple(files_changed),
        stdout_path=stdout_path,
        stderr_path=stderr_path,
        events_path=events_path,
        patch_path=patch_path,
        summary=f"{spec.agent_id} completed via OpenCode",
    )


def test_non_code_domain_skips_code_flow_and_opencode(monkeypatch, tmp_path):
    workspace = tmp_path / "research-workspace"
    workspace.mkdir()

    class FailingRunner:
        def __init__(self, *args, **kwargs):
            raise AssertionError("OpenCode must not run for non-code domains")

    monkeypatch.setattr(orchestrator_module, "OpenCodeSessionRunner", FailingRunner, raising=False)

    workflow = build_workflow().compile()
    result = workflow.invoke(_base_state(tmp_path, workspace, domain="research"))

    event_types = [event["type"] for event in result.get("events", [])]
    assert result["domain"] == "research"
    assert "discovery" not in event_types
    assert "testing" not in event_types
    assert "implementation" not in event_types
    assert "memory_consolidation" in event_types
    assert result["result"]


def test_existing_code_project_runs_tdd_before_implementation_with_opencode(monkeypatch, tmp_path):
    workspace = tmp_path / "existing-project"
    (workspace / ".synto").mkdir(parents=True)
    (workspace / ".synto" / "config.yaml").write_text("project: existing\n", encoding="utf-8")
    calls = []

    class FakeRunner:
        def __init__(self, *args, **kwargs):
            pass

        def run(self, spec):
            calls.append(spec)
            files = ("tests/test_login.py",) if spec.agent_id == "TDDAgent" else ("src/login.py",)
            return _fake_result(spec, files_changed=files)

    def fake_invoke_agent(state, agent_name, prompt, *, phase_id=""):
        return (
            f"{agent_name} fallback output",
            {"agent": agent_name, "provider": "test", "model": "mock", "fallback": False},
            [],
            dict(state.get("agent_skills_cache", {})),
        )

    monkeypatch.setattr(orchestrator_module, "OpenCodeSessionRunner", FakeRunner)
    monkeypatch.setattr(orchestrator_module, "_invoke_agent", fake_invoke_agent)

    state = _base_state(tmp_path, workspace)
    testing_result = orchestrator_module.testing(state)
    implementation_result = orchestrator_module.implementation({**state, **testing_result})

    assert [spec.agent_id for spec in calls] == ["TDDAgent", "BackendImplementer", "FrontendImplementer"]
    assert [spec.mode for spec in calls] == ["test_only", "write", "write"]
    assert testing_result["phase_outputs"]["tdd"]["opencode"]["agent_id"] == "TDDAgent"
    assert implementation_result["phase_outputs"]["implementation"]["BackendImplementer"]["opencode"]["agent_id"] == "BackendImplementer"
    assert implementation_result["phase_outputs"]["implementation"]["FrontendImplementer"]["opencode"]["agent_id"] == "FrontendImplementer"


def test_new_code_project_initializes_project_before_tdd(monkeypatch, tmp_path):
    workspace = tmp_path / "new-project"
    workspace.mkdir()
    calls = []

    class FakeRunner:
        def __init__(self, *args, **kwargs):
            pass

        def run(self, spec):
            calls.append(spec)
            files = ("package.json",) if spec.agent_id == "ProjectInitializerAgent" else ("tests/test_login.py",)
            return _fake_result(spec, files_changed=files)

    monkeypatch.setattr(orchestrator_module, "OpenCodeSessionRunner", FakeRunner)

    state = _base_state(tmp_path, workspace)
    result = orchestrator_module.testing(state)

    assert [spec.agent_id for spec in calls] == ["ProjectInitializerAgent", "TDDAgent"]
    assert [spec.mode for spec in calls] == ["write", "test_only"]
    assert result["code_flow_kind"] == "new_project"
    assert result["phase_outputs"]["project_initialization"]["opencode"]["agent_id"] == "ProjectInitializerAgent"
    assert result["phase_outputs"]["tdd"]["opencode"]["agent_id"] == "TDDAgent"
