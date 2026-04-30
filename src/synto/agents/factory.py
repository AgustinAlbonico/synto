"""AgentFactory — central instantiation for specialized Synto agents."""

from __future__ import annotations

from typing import Any

from synto.agents.all_agents import (
    Architect,
    BackendImplementer,
    Builder,
    BusinessAnalyst,
    CodeOrchestrator,
    CodebaseExplorer,
    ContractAligner,
    DependencyChecker,
    FrontendImplementer,
    HermesOrchestrator,
    Planner,
    ProductManager,
    QAGatekeeper,
    ReleaseManager,
    Reviewer,
    SecurityReviewer,
    SystemDesigner,
    TechnicalWriter,
    Tester,
)
from synto.agents.base import BaseAgent
from synto.config.llm_router import LLMMultiProvider
from synto.registry import AgentRegistry, PromptCompiler


_AGENT_CLASSES = [
    HermesOrchestrator,
    CodeOrchestrator,
    BusinessAnalyst,
    ProductManager,
    Planner,
    CodebaseExplorer,
    Architect,
    SystemDesigner,
    Tester,
    BackendImplementer,
    FrontendImplementer,
    ContractAligner,
    Reviewer,
    SecurityReviewer,
    QAGatekeeper,
    DependencyChecker,
    TechnicalWriter,
    ReleaseManager,
    Builder,
]

AGENT_CLASS_MAP: dict[str, type[BaseAgent]] = {cls.name: cls for cls in _AGENT_CLASSES}


class AgentFactory:
    """Create specialized agents with consistent router + context wiring."""

    def __init__(
        self,
        router: LLMMultiProvider | None = None,
        registry: AgentRegistry | None = None,
        prompt_compiler: PromptCompiler | None = None,
    ):
        self.router = router
        self.registry = registry
        self.prompt_compiler = prompt_compiler or PromptCompiler()

    def create(
        self,
        agent_name: str,
        *,
        memory_context: str = "",
        skill_context: str = "",
    ) -> BaseAgent:
        cls = AGENT_CLASS_MAP.get(agent_name)
        if cls is None:
            raise KeyError(f"Unknown agent: {agent_name}")
        agent = cls(router=self.router, memory_context=memory_context, skill_context=skill_context)
        agent_def = self.registry.get_agent(agent_name) if self.registry else None
        compiled_prompt = self.prompt_compiler.compile(
            agent_name=agent_name,
            agent=agent_def,
            fallback_prompt=getattr(cls, "system_prompt", ""),
        )
        if compiled_prompt:
            agent.system_prompt = compiled_prompt
        return agent

    def create_all(
        self,
        *,
        memory_by_agent: dict[str, dict[str, int]] | None = None,
        shared_memory_context: str = "",
    ) -> dict[str, BaseAgent]:
        memory_by_agent = memory_by_agent or {}
        agent_names = self._agent_names()
        agents: dict[str, BaseAgent] = {}

        for agent_name in agent_names:
            per_agent = memory_by_agent.get(agent_name, {}) or {}
            item_count = int(per_agent.get("items", 0) or 0)
            parts: list[str] = []
            if shared_memory_context:
                parts.append(shared_memory_context)
            if item_count:
                parts.append(f"[Agent-specific memory pack has {item_count} items loaded]")
            memory_context = "\n".join(part for part in parts if part)
            agents[agent_name] = self.create(agent_name, memory_context=memory_context)

        return agents

    def _agent_names(self) -> list[str]:
        if not self.registry:
            return list(AGENT_CLASS_MAP.keys())

        names: list[str] = []
        for agent_name in self.registry.agent_ids:
            if agent_name in AGENT_CLASS_MAP:
                names.append(agent_name)
        return names or list(AGENT_CLASS_MAP.keys())
