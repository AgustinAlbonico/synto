"""Tests for AgentRegistry."""

import tempfile
from pathlib import Path

import pytest
import yaml

from synto.registry import AgentRegistry, VALID_CAPABILITIES


VALID_AGENT = {
    "id": "test-agent",
    "role": "Backend Implementer",
    "capabilities": ["code_generation", "testing"],
    "model_profile": "capable",
    "restrictions": {"max_tokens": 8000},
    "mcp_capabilities": {"memory": True},
    "phases": ["implementation"],
}


def _write_registry(tmp_path: Path, agents: list[dict]) -> str:
    content = {"agents": agents}
    f = tmp_path / "registry.yaml"
    f.write_text(yaml.dump(content))
    return str(f)


def test_load_valid_registry(tmp_path: Path):
    path = _write_registry(tmp_path, [VALID_AGENT])
    reg = AgentRegistry(path)
    reg.load()
    assert "test-agent" in reg.agent_ids
    agent = reg.get_agent("test-agent")
    assert agent["role"] == "Backend Implementer"


def test_load_missing_role(tmp_path: Path):
    bad = dict(VALID_AGENT)
    del bad["role"]
    path = _write_registry(tmp_path, [bad])
    reg = AgentRegistry(path)
    with pytest.raises(ValueError, match="missing 'role'"):
        reg.load()


def test_load_missing_model_profile(tmp_path: Path):
    bad = dict(VALID_AGENT)
    del bad["model_profile"]
    path = _write_registry(tmp_path, [bad])
    reg = AgentRegistry(path)
    with pytest.raises(ValueError, match="missing 'model_profile'"):
        reg.load()


def test_load_unknown_capability(tmp_path: Path):
    bad = dict(VALID_AGENT)
    bad["capabilities"] = ["code_generation", "telepathy"]
    path = _write_registry(tmp_path, [bad])
    reg = AgentRegistry(path)
    with pytest.raises(ValueError, match="unknown capability"):
        reg.load()


def test_get_agents_by_capability(tmp_path: Path):
    a1 = dict(VALID_AGENT, id="agent-a", capabilities=["code_generation"])
    a2 = dict(VALID_AGENT, id="agent-b", capabilities=["testing"])
    path = _write_registry(tmp_path, [a1, a2])
    reg = AgentRegistry(path)
    reg.load()
    coders = reg.get_agents_by_capability("code_generation")
    assert len(coders) == 1
    assert coders[0]["id"] == "agent-a"


def test_get_agents_by_phase(tmp_path: Path):
    a1 = dict(VALID_AGENT, id="impl", phases=["implementation"])
    a2 = dict(VALID_AGENT, id="test", phases=["testing"])
    path = _write_registry(tmp_path, [a1, a2])
    reg = AgentRegistry(path)
    reg.load()
    impl = reg.get_agents_by_phase("implementation")
    assert len(impl) == 1


def test_load_empty_registry(tmp_path: Path):
    f = tmp_path / "empty.yaml"
    f.write_text("agents: []")
    reg = AgentRegistry(str(f))
    with pytest.raises(ValueError):
        reg.load()


def test_no_registry_path():
    reg = AgentRegistry()
    with pytest.raises(FileNotFoundError):
        reg.load()
