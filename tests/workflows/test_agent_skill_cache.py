from __future__ import annotations

from types import SimpleNamespace

from synto.agents.base import BaseAgent
import synto.workflows.orchestrator as orch


class DummySkillLoader:
    def __init__(self):
        self.calls = 0

    def resolve(self, agent_name, agent_def, state):
        self.calls += 1
        return SimpleNamespace(
            context=f"cached-skill-context:{self.calls}",
            skill_names=["test-driven-development"],
            skipped={},
            events=[{"type": "skill_loaded", "agent": agent_name, "run_id": state.get("run_id", "")}],
        )


class DummyStateStore:
    def append_skill_events(self, events):
        self.events = list(events)


class DummyRegistry:
    def get_agent(self, agent_name):
        return {"id": agent_name}


class DummyAgent(BaseAgent):
    name = "Tester"


def test_invoke_agent_reuses_skills_within_same_phase(monkeypatch):
    loader = DummySkillLoader()
    store = DummyStateStore()

    monkeypatch.setattr(orch, "_get_agents", lambda state: {"Tester": DummyAgent()})
    monkeypatch.setattr(orch, "_get_registry", lambda path: DummyRegistry())
    monkeypatch.setattr(orch, "_get_skill_loader", lambda state: loader)
    monkeypatch.setattr(orch, "_get_state_store", lambda state: store)

    state = {
        "task": "write tests",
        "run_id": "run_123",
        "registry_path": "dummy",
        "agent_skills_cache": {},
    }

    _, meta1, errors1, cache1 = orch._invoke_agent(state, "Tester", "first prompt", phase_id="review")
    _, meta2, errors2, cache2 = orch._invoke_agent(
        {**state, "agent_skills_cache": cache1},
        "Tester",
        "second prompt with different wording",
        phase_id="review",
    )
    _, meta3, errors3, cache3 = orch._invoke_agent(
        {**state, "agent_skills_cache": cache2},
        "Tester",
        "third prompt",
        phase_id="qa_docs",
    )

    assert not errors1
    assert not errors2
    assert not errors3
    assert loader.calls == 2
    assert meta1["skills_cache_status"] == "miss"
    assert meta2["skills_cache_status"] == "hit"
    assert meta3["skills_cache_status"] == "miss"
    assert cache1["Tester"]["phase"] == "review"
    assert cache2["Tester"]["phase"] == "review"
    assert cache3["Tester"]["phase"] == "qa_docs"
