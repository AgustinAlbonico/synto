"""Agent base class — wraps LLM calls with system prompts and memory context."""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any

from synto.config.llm_router import LLMMultiProvider, LLMRequest, LLMResponse


@dataclass
class AgentResult:
    output: str
    model: str
    provider: str
    raw: LLMResponse | None = None


class BaseAgent:
    """Base agent that calls an LLM with a system prompt + task."""

    name: str = "base-agent"
    system_prompt: str = "You are a helpful AI assistant."
    model_override: str = ""  # empty = resolved from config

    def __init__(self, router: LLMMultiProvider | None = None, memory_context: str = ""):
        self.router = router
        self.memory_context = memory_context

    def _build_messages(self, task: str, extra: str = "") -> list[dict[str, str]]:
        system = self.system_prompt
        if self.memory_context:
            system += f"\n\n--- Memory Context ---\n{self.memory_context}"
        if extra:
            system += f"\n\n--- Additional Context ---\n{extra}"
        return [
            {"role": "system", "content": system},
            {"role": "user", "content": task},
        ]

    def resolve_model(self) -> str:
        if self.model_override:
            return self.model_override
        if self.router:
            return self.router.resolve_model(
                self.name,
                profile=getattr(self, "model_profile", None),
            )
        return "glm-5.1"  # default

    def generate(self, task: str, extra: str = "", **kwargs) -> AgentResult:
        """Sync LLM call."""
        if self.router:
            model = self.resolve_model()
            if "max_tokens" not in kwargs:
                kwargs["max_tokens"] = 3000  # Reasoning models need headroom
            req = LLMRequest(
                model=model,
                messages=self._build_messages(task, extra),
                agent_name=self.name,
                **kwargs,
            )
            resp = self.router.generate_sync(req)
            return AgentResult(
                output=resp.content,
                model=resp.model,
                provider=resp.provider,
                raw=resp,
            )

        # No router — return mock
        return AgentResult(
            output=f"[mock:{self.name}] Would call LLM with: {task[:100]}",
            model=self.resolve_model(),
            provider="none",
        )

    async def generate_async(self, task: str, extra: str = "", **kwargs) -> AgentResult:
        """Async LLM call."""
        if self.router:
            model = self.resolve_model()
            if "max_tokens" not in kwargs:
                kwargs["max_tokens"] = 3000
            req = LLMRequest(
                model=model,
                messages=self._build_messages(task, extra),
                agent_name=self.name,
                **kwargs,
            )
            resp = await self.router.generate(req)
            return AgentResult(
                output=resp.content,
                model=resp.model,
                provider=resp.provider,
                raw=resp,
            )
        return AgentResult(
            output=f"[mock:{self.name}] Would call LLM with: {task[:100]}",
            model=self.resolve_model(),
            provider="none",
        )
