"""Compile agent system prompts from AGENT-REGISTRY definitions."""

from __future__ import annotations

from typing import Any


class PromptCompiler:
    """Build a consistent system prompt from structured registry metadata."""

    def compile(self, agent_name: str, agent: dict[str, Any] | None, fallback_prompt: str = "") -> str:
        agent = dict(agent or {})
        prompt_contract = agent.get("prompt_contract")
        if isinstance(prompt_contract, dict) and prompt_contract:
            return self._compile_prompt_contract(agent_name, agent, prompt_contract)
        if any(agent.get(key) for key in ("role", "responsibilities", "restrictions", "reads", "writes")):
            return self._compile_legacy(agent_name, agent)
        return fallback_prompt or "You are a helpful AI assistant."

    def _compile_prompt_contract(self, agent_name: str, agent: dict[str, Any], contract: dict[str, Any]) -> str:
        lines: list[str] = [f"Sos {agent_name}.", ""]

        identity = str(contract.get("identity") or agent.get("role") or "").strip()
        mission = str(contract.get("mission") or agent.get("role") or "").strip()
        workflow_position = str(contract.get("workflow_position") or agent.get("phase") or "").strip()
        role = str(agent.get("role") or "").strip()

        self._append_section(lines, "IDENTIDAD", [identity, role] if role and role != identity else [identity])
        self._append_section(lines, "MISIÓN", [mission])
        if workflow_position:
            self._append_section(lines, "POSICIÓN EN EL WORKFLOW", [workflow_position])

        self._append_section(lines, "ENTRADAS PRIMARIAS", self._string_list(contract.get("inputs")))
        self._append_section(lines, "SALIDAS ESPERADAS", self._string_list(contract.get("outputs")))
        self._append_section(lines, "DEBÉS", self._string_list(contract.get("must_do")))
        self._append_section(lines, "NO DEBÉS", self._string_list(contract.get("must_not_do")))
        self._append_section(lines, "ESCALÁ CUANDO", self._string_list(contract.get("escalation_rules")))
        self._append_section(lines, "CRITERIO DE DONE", self._string_list(contract.get("done_criteria")))

        response_contract = contract.get("response_contract") if isinstance(contract.get("response_contract"), dict) else {}
        response_lines: list[str] = []
        style = str(response_contract.get("style") or "").strip()
        if style:
            response_lines.append(f"Style: {style}")
        fmt = self._string_list(response_contract.get("format"))
        response_lines.extend(f"Format: {entry}" for entry in fmt)
        self._append_section(lines, "CONTRATO DE RESPUESTA", response_lines)

        collaboration_lines = [
            f"Leés de: {', '.join(self._string_list(agent.get('reads'))) or 'sin declarar'}.",
            f"Escribís en: {', '.join(self._string_list(agent.get('writes'))) or 'sin declarar'}.",
            f"Interacción humana: {str(agent.get('human_interaction') or 'sin declarar')}",
            "No actúes fuera de tu rol.",
            "Si falta información o hay contradicciones, escalá en vez de inventar.",
        ]
        self._append_section(lines, "REGLAS DE COLABORACIÓN", collaboration_lines)

        return "\n".join(lines).strip()

    def _compile_legacy(self, agent_name: str, agent: dict[str, Any]) -> str:
        lines: list[str] = [f"Sos {agent_name}.", ""]
        role = str(agent.get("role") or "Agente especializado.").strip()

        self._append_section(lines, "IDENTIDAD", [role])
        self._append_section(lines, "RESPONSABILIDADES BASE", self._string_list(agent.get("responsibilities")))
        self._append_section(lines, "RESTRICCIONES BASE", self._string_list(agent.get("restrictions")))

        collaboration_lines = [
            f"Leés de: {', '.join(self._string_list(agent.get('reads'))) or 'sin declarar'}.",
            f"Escribís en: {', '.join(self._string_list(agent.get('writes'))) or 'sin declarar'}.",
            f"Interacción humana: {str(agent.get('human_interaction') or 'sin declarar')}",
            "Respetá estrictamente tu rol y límites.",
            "Si falta información, escalá en vez de inventar.",
        ]
        self._append_section(lines, "REGLAS DE COLABORACIÓN", collaboration_lines)
        return "\n".join(lines).strip()

    def _append_section(self, lines: list[str], title: str, entries: list[str]) -> None:
        normalized = [entry.strip() for entry in entries if str(entry).strip()]
        if not normalized:
            return
        lines.append(title)
        for entry in normalized:
            lines.append(f"- {entry}")
        lines.append("")

    def _string_list(self, value: Any) -> list[str]:
        if value is None:
            return []
        if isinstance(value, str):
            text = value.strip()
            return [text] if text else []
        if isinstance(value, (list, tuple, set)):
            return [str(item).strip() for item in value if str(item).strip()]
        if isinstance(value, dict):
            return [f"{key}: {value[key]}" for key in value]
        text = str(value).strip()
        return [text] if text else []
