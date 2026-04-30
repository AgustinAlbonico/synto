from __future__ import annotations

from pathlib import Path

import yaml

import synto.agents.all_agents as all_agents_module
from synto.agents.factory import AgentFactory
from synto.registry import AgentRegistry


def test_agent_factory_combines_shared_and_agent_memory_context():
    factory = AgentFactory()

    agents = factory.create_all(
        memory_by_agent={"Tester": {"items": 3}},
        shared_memory_context="- project memory snippet",
    )

    tester = agents["Tester"]
    assert "project memory snippet" in tester.memory_context
    assert "3 items loaded" in tester.memory_context


def test_agent_factory_uses_registry_prompt_contract(tmp_path: Path):
    registry_path = tmp_path / "registry.yaml"
    registry_path.write_text(
        yaml.safe_dump(
            {
                "agents": {
                    "BackendImplementer": {
                        "role": "Desarrollador backend.",
                        "model_profile": "heavy_coding",
                        "restrictions": [],
                        "mcp_capabilities": [],
                        "prompt_contract": {
                            "identity": "Sos un desarrollador backend senior orientado a cambios seguros.",
                            "mission": "Implementar APIs y lógica de negocio cumpliendo spec y test plan.",
                            "workflow_position": "Fase de implementación.",
                            "inputs": ["spec", "backend_design"],
                            "outputs": ["backend_code_changes"],
                            "must_do": ["Cambiar el mínimo necesario."],
                            "must_not_do": ["No tocar frontend."],
                            "escalation_rules": ["Escalar contradicciones fuertes."],
                            "done_criteria": ["El scope quedó implementado."],
                            "response_contract": {"style": "directo", "format": ["Summary"]},
                        },
                    }
                }
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    registry = AgentRegistry(str(registry_path))
    registry.load()

    factory = AgentFactory(registry=registry)
    agent = factory.create("BackendImplementer")

    assert "Sos un desarrollador backend senior orientado a cambios seguros." in agent.system_prompt
    assert "You are the Backend Implementer" not in agent.system_prompt


def test_legacy_create_all_agents_uses_prompt_compiler_from_default_registry():
    agents = all_agents_module.create_all_agents()

    reviewer = agents["Reviewer"]
    assert "MISIÓN" in reviewer.system_prompt
    assert "CONTRATO DE RESPUESTA" in reviewer.system_prompt
    assert "Fallback prompt" not in reviewer.system_prompt


def test_legacy_create_all_agents_accepts_registry_override(tmp_path: Path):
    registry_path = tmp_path / "registry.yaml"
    registry_path.write_text(
        yaml.safe_dump(
            {
                "agents": {
                    "Reviewer": {
                        "role": "Revisor de código custom.",
                        "model_profile": "balanced",
                        "restrictions": [],
                        "mcp_capabilities": [],
                        "prompt_contract": {
                            "identity": "Sos un reviewer custom desde registry override.",
                            "mission": "Demostrar que create_all_agents delega en AgentFactory.",
                            "inputs": ["diff"],
                            "outputs": ["review"],
                            "must_do": ["Compilar desde YAML."],
                            "must_not_do": ["Usar fallback Python."],
                            "done_criteria": ["El prompt contiene este contrato."],
                        },
                    }
                }
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    registry = AgentRegistry(str(registry_path))
    registry.load()

    agents = all_agents_module.create_all_agents(registry=registry)

    assert list(agents) == ["Reviewer"]
    assert "reviewer custom desde registry override" in agents["Reviewer"].system_prompt
    assert "Fallback prompt" not in agents["Reviewer"].system_prompt


def test_migrated_agents_only_keep_registry_fallback_prompt():
    for cls in [
        all_agents_module.HermesOrchestrator,
        all_agents_module.CodeOrchestrator,
        all_agents_module.BusinessAnalyst,
        all_agents_module.ProductManager,
        all_agents_module.Planner,
        all_agents_module.CodebaseExplorer,
        all_agents_module.Architect,
        all_agents_module.SystemDesigner,
        all_agents_module.Tester,
        all_agents_module.BackendImplementer,
        all_agents_module.FrontendImplementer,
        all_agents_module.ContractAligner,
        all_agents_module.Reviewer,
        all_agents_module.SecurityReviewer,
        all_agents_module.QAGatekeeper,
        all_agents_module.DependencyChecker,
        all_agents_module.TechnicalWriter,
        all_agents_module.ReleaseManager,
        all_agents_module.Builder,
    ]:
        assert "AGENT-REGISTRY.yaml" in cls.system_prompt
        assert "PromptCompiler" in cls.system_prompt
