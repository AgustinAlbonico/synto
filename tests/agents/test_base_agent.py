from __future__ import annotations

from synto.agents.base import BaseAgent


def test_base_agent_includes_loaded_skill_context_in_system_message():
    agent = BaseAgent(memory_context="memory item", skill_context="--- Skill: testing ---\nUse pytest.")

    messages = agent._build_messages("write tests")

    system = messages[0]["content"]
    assert "--- Memory Context ---" in system
    assert "memory item" in system
    assert "--- Loaded Skills ---" in system
    assert "Use pytest" in system
