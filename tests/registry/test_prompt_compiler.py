from __future__ import annotations

from synto.registry import PromptCompiler


def test_compile_prompt_contract_includes_structured_sections():
    compiler = PromptCompiler()
    prompt = compiler.compile(
        agent_name="BackendImplementer",
        agent={
            "role": "Desarrollador backend.",
            "reads": ["spec", "backend_design"],
            "writes": ["backend_code_changes", "api_contract_actual"],
            "human_interaction": "none",
            "prompt_contract": {
                "identity": "Sos un desarrollador backend senior.",
                "mission": "Implementar APIs y lógica de negocio cumpliendo spec y test plan.",
                "workflow_position": "Fase de implementación con insumos aprobados.",
                "inputs": ["spec", "task_graph", "backend_design", "test_plan"],
                "outputs": ["backend_code_changes", "api_contract_actual"],
                "must_do": ["Cambiar el mínimo necesario.", "Mantener contratos claros."],
                "must_not_do": ["No tocar frontend.", "No modificar PRD/spec."],
                "escalation_rules": ["Escalar contradicciones serias entre spec y repo."],
                "done_criteria": ["El scope asignado quedó implementado."],
                "response_contract": {
                    "style": "directo y técnico",
                    "format": ["Summary", "Files changed", "Risks"],
                },
            },
        },
    )

    assert "Sos BackendImplementer." in prompt
    assert "IDENTIDAD" in prompt
    assert "MISIÓN" in prompt
    assert "ENTRADAS PRIMARIAS" in prompt
    assert "SALIDAS ESPERADAS" in prompt
    assert "DEBÉS" in prompt
    assert "NO DEBÉS" in prompt
    assert "ESCALÁ CUANDO" in prompt
    assert "CRITERIO DE DONE" in prompt
    assert "CONTRATO DE RESPUESTA" in prompt
    assert "REGLAS DE COLABORACIÓN" in prompt
    assert "Cambiar el mínimo necesario." in prompt
    assert "No tocar frontend." in prompt
    assert "Files changed" in prompt


def test_compile_prompt_contract_from_real_registry_agents():
    from pathlib import Path
    import yaml

    registry_path = Path(__file__).resolve().parents[2] / "AGENT-REGISTRY.yaml"
    data = yaml.safe_load(registry_path.read_text(encoding="utf-8"))
    compiler = PromptCompiler()

    for agent_name in data["agents"]:
        agent = data["agents"][agent_name]
        prompt = compiler.compile(agent_name=agent_name, agent=agent)
        assert f"Sos {agent_name}." in prompt
        assert "MISIÓN" in prompt
        assert "DEBÉS" in prompt
        assert "NO DEBÉS" in prompt


def test_compile_legacy_registry_metadata_when_prompt_contract_missing():
    compiler = PromptCompiler()
    prompt = compiler.compile(
        agent_name="Reviewer",
        agent={
            "role": "Revisor de código general.",
            "responsibilities": [
                "Revisar calidad y legibilidad.",
                "Detectar bugs y deuda técnica.",
            ],
            "restrictions": [
                "No corrige directamente.",
                "No hace security review profunda.",
            ],
            "reads": ["implementation_slots", "spec"],
            "writes": ["code_review_report"],
            "human_interaction": "none",
        },
    )

    assert "Sos Reviewer." in prompt
    assert "Revisor de código general." in prompt
    assert "RESPONSABILIDADES BASE" in prompt
    assert "RESTRICCIONES BASE" in prompt
    assert "implementation_slots" in prompt
    assert "code_review_report" in prompt
