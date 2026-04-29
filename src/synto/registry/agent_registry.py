"""AgentRegistry — loads and validates AGENT-REGISTRY.yaml."""

from pathlib import Path
from typing import Any, Optional

import yaml


VALID_CAPABILITIES = {
    "code_generation", "code_review", "testing", "research",
    "architecture", "planning", "writing", "editing", "security",
    "documentation", "seo", "strategy", "analysis", "implementation",
    "exploration", "validation", "synthesis", "qa", "memory",
}


class AgentRegistry:
    """Loads agent definitions from YAML and validates them."""

    def __init__(self, registry_path: str = ""):
        self.registry_path = Path(registry_path) if registry_path else None
        self._agents: dict[str, dict] = {}
        self._raw: dict = {}

    def load(self, path: str = "") -> None:
        """Load and validate agent registry from YAML."""
        reg_path = Path(path) if path else self.registry_path
        if not reg_path:
            raise FileNotFoundError("No registry path provided")

        with open(reg_path) as f:
            self._raw = yaml.safe_load(f)

        agents = self._raw.get("agents", [])
        if not agents:
            raise ValueError("No agents defined in registry")

        errors = []
        for agent in agents:
            aid = agent.get("id", "<unknown>")
            errs = self._validate_agent(agent)
            errors.extend(errs)

        if errors:
            raise ValueError(f"Registry validation errors:\n" + "\n".join(f"  - {e}" for e in errors))

        self._agents = {a["id"]: a for a in agents}

    def _validate_agent(self, agent: dict) -> list[str]:
        errors = []
        aid = agent.get("id", "<unknown>")

        if not agent.get("role"):
            errors.append(f"[{aid}] missing 'role'")

        restrictions = agent.get("restrictions", {})
        if not isinstance(restrictions, dict):
            errors.append(f"[{aid}] 'restrictions' must be a dict")

        mcp = agent.get("mcp_capabilities", {})
        if not isinstance(mcp, dict):
            errors.append(f"[{aid}] 'mcp_capabilities' must be a dict")

        model_profile = agent.get("model_profile", "")
        if not model_profile:
            errors.append(f"[{aid}] missing 'model_profile'")

        caps = agent.get("capabilities", [])
        if isinstance(caps, list):
            for cap in caps:
                if cap not in VALID_CAPABILITIES:
                    errors.append(f"[{aid}] unknown capability: {cap}")

        return errors

    def get_agent(self, agent_id: str) -> Optional[dict]:
        """Get a single agent definition."""
        return self._agents.get(agent_id)

    def get_all(self) -> dict[str, dict]:
        """Get all agents."""
        return dict(self._agents)

    def get_agents_by_capability(self, capability: str) -> list[dict]:
        """Find agents that have a specific capability."""
        result = []
        for agent in self._agents.values():
            if capability in agent.get("capabilities", []):
                result.append(agent)
        return result

    def get_agents_by_phase(self, phase: str) -> list[dict]:
        """Find agents assigned to a specific phase."""
        result = []
        for agent in self._agents.values():
            phases = agent.get("phases", [])
            if phase in phases:
                result.append(agent)
        return result

    @property
    def raw(self) -> dict:
        return dict(self._raw)

    @property
    def agent_ids(self) -> list[str]:
        return list(self._agents.keys())
