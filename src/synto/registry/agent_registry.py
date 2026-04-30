"""AgentRegistry — loads and validates AGENT-REGISTRY.yaml."""

from __future__ import annotations

from pathlib import Path
from typing import Optional, Any

import yaml


VALID_CAPABILITIES = {
    "code_generation",
    "code_review",
    "testing",
    "research",
    "architecture",
    "planning",
    "writing",
    "editing",
    "security",
    "documentation",
    "seo",
    "strategy",
    "analysis",
    "implementation",
    "exploration",
    "validation",
    "synthesis",
    "qa",
    "memory",
}


class AgentRegistry:
    """Loads agent definitions from YAML and validates them.

    Supports both:
    - legacy list format: {agents: [{id: ..., ...}, ...]}
    - architecture contract format: {agents: {AgentName: {...}, ...}}
    """

    def __init__(self, registry_path: str = ""):
        self.registry_path = Path(registry_path) if registry_path else None
        self._agents: dict[str, dict[str, Any]] = {}
        self._raw: dict[str, Any] = {}

    def load(self, path: str = "") -> None:
        """Load and validate agent registry from YAML."""
        reg_path = Path(path) if path else self.registry_path
        if not reg_path:
            raise FileNotFoundError("No registry path provided")

        with open(reg_path) as f:
            self._raw = yaml.safe_load(f) or {}

        normalized = self._normalize_agents(self._raw.get("agents"))
        if not normalized:
            raise ValueError("No agents defined in registry")

        errors: list[str] = []
        for agent_id, agent in normalized.items():
            errors.extend(self._validate_agent(agent_id, agent))

        if errors:
            raise ValueError("Registry validation errors:\n" + "\n".join(f"  - {e}" for e in errors))

        self._agents = normalized

    def _normalize_agents(self, agents: Any) -> dict[str, dict[str, Any]]:
        if isinstance(agents, dict):
            normalized: dict[str, dict[str, Any]] = {}
            for agent_id, config in agents.items():
                if not isinstance(config, dict):
                    continue
                item = dict(config)
                item.setdefault("id", agent_id)
                normalized[agent_id] = item
            return normalized

        if isinstance(agents, list):
            normalized = {}
            for agent in agents:
                if not isinstance(agent, dict):
                    continue
                agent_id = agent.get("id") or agent.get("name")
                if not agent_id:
                    continue
                normalized[str(agent_id)] = dict(agent)
            return normalized

        return {}

    def _validate_agent(self, agent_id: str, agent: dict[str, Any]) -> list[str]:
        errors: list[str] = []

        if not agent.get("role"):
            errors.append(f"[{agent_id}] missing 'role'")

        if "restrictions" not in agent:
            errors.append(f"[{agent_id}] missing 'restrictions'")
        elif not isinstance(agent.get("restrictions"), (list, dict)):
            errors.append(f"[{agent_id}] 'restrictions' must be a list or dict")

        if not agent.get("model_profile"):
            errors.append(f"[{agent_id}] missing 'model_profile'")

        if "mcp_capabilities" not in agent:
            errors.append(f"[{agent_id}] missing 'mcp_capabilities'")
        elif not isinstance(agent.get("mcp_capabilities"), (list, dict)):
            errors.append(f"[{agent_id}] 'mcp_capabilities' must be a list or dict")

        caps = agent.get("capabilities", [])
        if caps and not isinstance(caps, list):
            errors.append(f"[{agent_id}] 'capabilities' must be a list")
        elif isinstance(caps, list):
            for cap in caps:
                if cap not in VALID_CAPABILITIES:
                    errors.append(f"[{agent_id}] unknown capability: {cap}")

        reads = agent.get("reads")
        if reads is not None and not isinstance(reads, list):
            errors.append(f"[{agent_id}] 'reads' must be a list")

        writes = agent.get("writes")
        if writes is not None and not isinstance(writes, list):
            errors.append(f"[{agent_id}] 'writes' must be a list")

        prompt_contract = agent.get("prompt_contract")
        if prompt_contract is not None:
            errors.extend(self._validate_prompt_contract(agent_id, prompt_contract))

        return errors

    def _validate_prompt_contract(self, agent_id: str, prompt_contract: Any) -> list[str]:
        errors: list[str] = []
        if not isinstance(prompt_contract, dict):
            return [f"[{agent_id}] 'prompt_contract' must be a dict"]

        required_string_fields = ["identity", "mission"]
        required_list_fields = ["inputs", "outputs", "must_do", "must_not_do", "done_criteria"]
        optional_list_fields = ["escalation_rules"]

        for field in required_string_fields:
            value = prompt_contract.get(field)
            if not isinstance(value, str) or not value.strip():
                errors.append(f"[{agent_id}] 'prompt_contract.{field}' must be a non-empty string")

        workflow_position = prompt_contract.get("workflow_position")
        if workflow_position is not None and (not isinstance(workflow_position, str) or not workflow_position.strip()):
            errors.append(f"[{agent_id}] 'prompt_contract.workflow_position' must be a non-empty string when present")

        for field in required_list_fields:
            errors.extend(self._validate_prompt_contract_list(agent_id, prompt_contract, field, required=True))

        for field in optional_list_fields:
            errors.extend(self._validate_prompt_contract_list(agent_id, prompt_contract, field, required=False))

        response_contract = prompt_contract.get("response_contract")
        if response_contract is not None:
            if not isinstance(response_contract, dict):
                errors.append(f"[{agent_id}] 'prompt_contract.response_contract' must be a dict")
            else:
                style = response_contract.get("style")
                if style is not None and (not isinstance(style, str) or not style.strip()):
                    errors.append(f"[{agent_id}] 'prompt_contract.response_contract.style' must be a non-empty string when present")
                format_value = response_contract.get("format")
                if format_value is not None:
                    if not isinstance(format_value, list) or not format_value or any(not isinstance(item, str) or not item.strip() for item in format_value):
                        errors.append(f"[{agent_id}] 'prompt_contract.response_contract.format' must be a non-empty list of strings when present")

        return errors

    def _validate_prompt_contract_list(
        self,
        agent_id: str,
        prompt_contract: dict[str, Any],
        field: str,
        *,
        required: bool,
    ) -> list[str]:
        value = prompt_contract.get(field)
        if value is None:
            if required:
                return [f"[{agent_id}] missing 'prompt_contract.{field}'"]
            return []
        if not isinstance(value, list) or not value or any(not isinstance(item, str) or not item.strip() for item in value):
            return [f"[{agent_id}] 'prompt_contract.{field}' must be a non-empty list of strings"]
        return []

    def get_agent(self, agent_id: str) -> Optional[dict[str, Any]]:
        """Get a single agent definition."""
        agent = self._agents.get(agent_id)
        return dict(agent) if agent else None

    def get_all(self) -> dict[str, dict[str, Any]]:
        """Get all agents."""
        return {k: dict(v) for k, v in self._agents.items()}

    def get_agents_by_capability(self, capability: str) -> list[dict[str, Any]]:
        """Find agents that have a specific capability."""
        return [dict(agent) for agent in self._agents.values() if capability in agent.get("capabilities", [])]

    def get_agents_by_phase(self, phase: str) -> list[dict[str, Any]]:
        """Find agents assigned to a specific phase.

        Supports both `phase: str` and `phases: list[str]`.
        """
        result = []
        for agent in self._agents.values():
            if agent.get("phase") == phase:
                result.append(dict(agent))
                continue
            phases = agent.get("phases", [])
            if phase in phases:
                result.append(dict(agent))
        return result

    @property
    def raw(self) -> dict[str, Any]:
        return dict(self._raw)

    @property
    def agent_ids(self) -> list[str]:
        return list(self._agents.keys())
