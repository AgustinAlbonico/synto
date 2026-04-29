"""Architecture-contract tests for AGENT-REGISTRY.yaml."""

from pathlib import Path

from synto.registry import AgentRegistry


ROOT = Path(__file__).resolve().parents[2]
REGISTRY_PATH = ROOT / "AGENT-REGISTRY.yaml"


def test_loads_mapping_style_agent_registry_contract():
    reg = AgentRegistry(str(REGISTRY_PATH))
    reg.load()

    assert len(reg.agent_ids) == 21
    assert "HermesOrchestrator" in reg.agent_ids
    assert "BackendImplementer" in reg.agent_ids
    assert "FrontendImplementer" in reg.agent_ids
    assert "QAGatekeeper" in reg.agent_ids

    backend = reg.get_agent("BackendImplementer")
    assert backend is not None
    assert backend["id"] == "BackendImplementer"
    assert backend["model_profile"]
    assert isinstance(backend["restrictions"], list)
    assert isinstance(backend["mcp_capabilities"], list)


def test_mapping_style_phase_lookup_supports_phase_field(tmp_path: Path):
    content = """
agents:
  Architect:
    role: System architect
    model_profile: strategic
    restrictions: []
    mcp_capabilities: []
    phase: planning
  Builder:
    role: Builder
    model_profile: heavy_coding
    restrictions: []
    mcp_capabilities: []
    phases: [implementation]
"""
    path = tmp_path / "registry.yaml"
    path.write_text(content)

    reg = AgentRegistry(str(path))
    reg.load()

    planning = reg.get_agents_by_phase("planning")
    implementation = reg.get_agents_by_phase("implementation")

    assert [agent["id"] for agent in planning] == ["Architect"]
    assert [agent["id"] for agent in implementation] == ["Builder"]
