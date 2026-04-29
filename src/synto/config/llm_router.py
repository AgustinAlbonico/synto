"""LLM Provider Router — unified interface for multiple LLM providers."""

import os
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Literal

import yaml
from openai import AsyncOpenAI, OpenAI


import json


@dataclass
class ModelInfo:
    id: str
    name: str
    context_window: int
    capabilities: list[str]
    cost_tier: Literal["free", "economy", "balanced", "premium"]

    @property
    def is_free(self) -> bool:
        return self.cost_tier == "free"


@dataclass
class ProviderConfig:
    name: str
    provider_type: str  # openai_compat, openrouter, ollama
    base_url: str
    api_key: str | None = None
    models: list[ModelInfo] = field(default_factory=list)


@dataclass
class LLMRequest:
    model: str
    messages: list[dict[str, str]]
    temperature: float = 0.7
    max_tokens: int | None = None  # 3000+ recommended for reasoning models
    agent_name: str = ""
    response_format: dict | None = None


@dataclass
class LLMResponse:
    content: str
    model: str
    provider: str
    usage: dict[str, int] = field(default_factory=dict)
    finish_reason: str = ""
    reasoning: str = ""


def resolve_env(value: str) -> str:
    """Resolve ${ENV_VAR} patterns in config values."""
    pattern = re.compile(r"\$\{([^}]+)\}")
    def replacer(m):
        return os.environ.get(m.group(1), "")
    return pattern.sub(replacer, value)


class BaseProvider(ABC):
    def __init__(self, config: ProviderConfig):
        self.config = config

    @abstractmethod
    async def generate(self, req: LLMRequest) -> LLMResponse: ...

    @abstractmethod
    def generate_sync(self, req: LLMRequest) -> LLMResponse: ...

    @property
    def is_available(self) -> bool:
        return True


class OpenAICompatProvider(BaseProvider):
    """Any OpenAI-compatible endpoint (GLM, Kimi, Gemini, OpenAI)."""

    def __init__(self, config: ProviderConfig):
        super().__init__(config)
        self.client = OpenAI(
            api_key=config.api_key or "dummy",
            base_url=config.base_url,
        )
        self.async_client = AsyncOpenAI(
            api_key=config.api_key or "dummy",
            base_url=config.base_url,
        )

    async def generate(self, req: LLMRequest) -> LLMResponse:
        kwargs: dict[str, Any] = {
            "model": req.model,
            "messages": req.messages,
            "temperature": req.temperature,
        }
        if req.max_tokens:
            kwargs["max_tokens"] = req.max_tokens
        if req.response_format:
            kwargs["response_format"] = req.response_format

        resp = await self.async_client.chat.completions.create(**kwargs)
        choice = resp.choices[0]
        msg = choice.message
        content = msg.content or ""
        if not content:
            content = getattr(msg, "reasoning", "") or ""
        reasoning = getattr(msg, "reasoning", "") or ""
        return LLMResponse(
            content=content,
            model=req.model,
            provider=self.config.name,
            usage={
                "prompt_tokens": resp.usage.prompt_tokens if resp.usage else 0,
                "completion_tokens": resp.usage.completion_tokens if resp.usage else 0,
            },
            finish_reason=choice.finish_reason or "",
            reasoning=reasoning,
        )

    def generate_sync(self, req: LLMRequest) -> LLMResponse:
        kwargs: dict[str, Any] = {
            "model": req.model,
            "messages": req.messages,
            "temperature": req.temperature,
        }
        if req.max_tokens:
            kwargs["max_tokens"] = req.max_tokens
        if req.response_format:
            kwargs["response_format"] = req.response_format

        resp = self.client.chat.completions.create(**kwargs)
        choice = resp.choices[0]
        msg = choice.message
        content = msg.content or ""
        # For reasoning models: fall back to reasoning if content is empty
        if not content:
            content = getattr(msg, "reasoning", "") or ""
        reasoning = getattr(msg, "reasoning", "") or ""
        return LLMResponse(
            content=content,
            model=req.model,
            provider=self.config.name,
            usage={
                "prompt_tokens": resp.usage.prompt_tokens if resp.usage else 0,
                "completion_tokens": resp.usage.completion_tokens if resp.usage else 0,
            },
            finish_reason=choice.finish_reason or "",
            reasoning=reasoning,
        )

    @property
    def is_available(self) -> bool:
        if self.config.api_key:
            return True
        # Ollama and some open endpoints don't need a key
        if self.config.provider_type == "ollama":
            try:
                self.client.models.list()
                return True
            except Exception:
                return False
        return False


class OpenAIOAuthProvider(BaseProvider):
    """OpenAI via OAuth — reads access token from OpenCode auth.json.

    Used for OpenAI subscriptions (Codex, etc.) where you don't have
    a traditional API key but OAuth tokens stored by OpenCode.
    """

    DEFAULT_AUTH_PATHS = [
        os.path.expanduser("~/.local/share/opencode/auth.json"),
        "/mnt/c/Users/agust/.local/share/opencode/auth.json",
        "/mnt/c/Users/agust/.config/opencode/auth.json",
    ]

    def __init__(self, config: ProviderConfig):
        super().__init__(config)
        self.client: OpenAI | None = None
        self.async_client: AsyncOpenAI | None = None
        self._token: str | None = None
        self._setup()

    def _setup(self):
        """Find auth.json and create OpenAI client with OAuth token."""
        auth_file = self.config.base_url or ""
        if not auth_file or not os.path.exists(auth_file):
            for p in self.DEFAULT_AUTH_PATHS:
                if os.path.exists(p):
                    auth_file = p
                    break

        if not auth_file:
            return

        try:
            with open(auth_file) as f:
                auth = json.load(f)
        except (json.JSONDecodeError, IOError):
            return

        openai_entry = auth.get("openai")
        if not openai_entry:
            return

        # Use access token as API key
        token = openai_entry.get("access")
        if not token:
            return

        self._token = token
        self.client = OpenAI(
            api_key=token,
            base_url=self.config.base_url if self.config.base_url else "https://api.openai.com/v1",
        )
        self.async_client = AsyncOpenAI(
            api_key=token,
            base_url=self.config.base_url if self.config.base_url else "https://api.openai.com/v1",
        )

    @property
    def is_available(self) -> bool:
        return self.client is not None and self._token is not None

    async def generate(self, req: LLMRequest) -> LLMResponse:
        if not self.async_client:
            raise RuntimeError("OpenAI OAuth not configured")
        kwargs: dict[str, Any] = {
            "model": req.model,
            "messages": req.messages,
            "temperature": req.temperature,
        }
        if req.max_tokens:
            kwargs["max_tokens"] = req.max_tokens
        if req.response_format:
            kwargs["response_format"] = req.response_format

        resp = await self.async_client.chat.completions.create(**kwargs)
        choice = resp.choices[0]
        return LLMResponse(
            content=choice.message.content or "",
            model=req.model,
            provider="openai",
            usage={
                "prompt_tokens": resp.usage.prompt_tokens if resp.usage else 0,
                "completion_tokens": resp.usage.completion_tokens if resp.usage else 0,
            },
            finish_reason=choice.finish_reason or "",
        )

    def generate_sync(self, req: LLMRequest) -> LLMResponse:
        if not self.client:
            raise RuntimeError("OpenAI OAuth not configured")
        kwargs: dict[str, Any] = {
            "model": req.model,
            "messages": req.messages,
            "temperature": req.temperature,
        }
        if req.max_tokens:
            kwargs["max_tokens"] = req.max_tokens
        if req.response_format:
            kwargs["response_format"] = req.response_format

        resp = self.client.chat.completions.create(**kwargs)
        choice = resp.choices[0]
        return LLMResponse(
            content=choice.message.content or "",
            model=req.model,
            provider="openai",
            usage={
                "prompt_tokens": resp.usage.prompt_tokens if resp.usage else 0,
                "completion_tokens": resp.usage.completion_tokens if resp.usage else 0,
            },
            finish_reason=choice.finish_reason or "",
        )


class OpenCodeProvider(BaseProvider):
    """Reads OpenCode auth.json and creates sub-providers for each configured service.

    Supports:
      - zai-coding-plan → GLM models via Z.AI API
      - openai OAuth → GPT models via OpenAI API
    """

    DEFAULT_AUTH_PATHS = [
        os.path.expanduser("~/.local/share/opencode/auth.json"),
        "/mnt/c/Users/agust/.local/share/opencode/auth.json",
        "/mnt/c/Users/agust/.config/opencode/auth.json",
    ]

    ZAI_BASE_URL = "https://api.z.ai/api/api/v1"
    OPENAI_BASE_URL = "https://api.openai.com/v1"

    def __init__(self, config: ProviderConfig):
        super().__init__(config)
        self.auth_path = config.base_url if config else ""  # repurposed for auth file path
        self.sub_providers: dict[str, OpenAICompatProvider] = {}
        self.auth_data: dict = {}

        self._load_auth()

    def _load_auth(self):
        """Find and parse auth.json, create sub-providers."""
        auth_file = self.auth_path or ""
        if not auth_file or not os.path.exists(auth_file):
            # Try default paths
            for p in self.DEFAULT_AUTH_PATHS:
                if os.path.exists(p):
                    auth_file = p
                    break

        if not auth_file:
            return

        try:
            with open(auth_file) as f:
                self.auth_data = json.load(f)
        except (json.JSONDecodeError, IOError):
            return

        # Z.AI / GLM
        zai_entry = self.auth_data.get("zai-coding-plan")
        if zai_entry and zai_entry.get("key"):
            zai_cfg = ProviderConfig(
                name="zai",
                provider_type="openai_compat",
                base_url=self.ZAI_BASE_URL,
                api_key=zai_entry["key"],
            )
            self.sub_providers["zai"] = OpenAICompatProvider(zai_cfg)

        # OpenAI OAuth
        openai_entry = self.auth_data.get("openai")
        if openai_entry and openai_entry.get("access"):
            oa_cfg = ProviderConfig(
                name="openai",
                provider_type="openai_compat",
                base_url=self.OPENAI_BASE_URL,
                api_key=openai_entry["access"],
            )
            self.sub_providers["openai"] = OpenAICompatProvider(oa_cfg)

    @property
    def is_available(self) -> bool:
        return len(self.sub_providers) > 0

    def _pick_provider(self, model_id: str) -> BaseProvider | None:
        """Choose sub-provider based on model ID."""
        # Z.AI models
        if model_id.startswith("glm"):
            return self.sub_providers.get("zai")
        # OpenAI models
        if model_id.startswith(("gpt", "o1", "o3", "o4")):
            return self.sub_providers.get("openai")
        # Fallback: first available
        for p in self.sub_providers.values():
            if p.is_available:
                return p
        return None

    async def generate(self, req: LLMRequest) -> LLMResponse:
        prov = self._pick_provider(req.model)
        if not prov:
            raise RuntimeError(f"No opencode sub-provider for model '{req.model}'")
        return await prov.generate(req)

    def generate_sync(self, req: LLMRequest) -> LLMResponse:
        prov = self._pick_provider(req.model)
        if not prov:
            raise RuntimeError(f"No opencode sub-provider for model '{req.model}'")
        return prov.generate_sync(req)


class OpenRouterProvider(OpenAICompatProvider):
    """OpenRouter — same API shape, different headers."""

    def __init__(self, config: ProviderConfig):
        super().__init__(config)
        # Override headers for OpenRouter
        self.client.default_headers["HTTP-Referer"] = "https://github.com/AgustinAlbonico/synto"
        self.client.default_headers["X-Title"] = "Synto"


class LLMMultiProvider:
    """Central router that dispatches to the right provider/model."""

    def __init__(self, config_path: str = ""):
        self.providers: dict[str, BaseProvider] = {}
        self.model_to_provider: dict[str, str] = {}
        self.agent_profiles: dict[str, str] = {}  # agent_name -> profile name
        self.profile_models: dict[str, str] = {}  # profile_name -> model_id
        self.fallback_order: list[str] = []
        self._loaded = False

        if config_path:
            self.load(config_path)

    def load(self, config_dir: str):
        """Load providers.yaml and models.yaml from config directory."""
        providers_path = os.path.join(config_dir, "providers.yaml")
        models_path = os.path.join(config_dir, "models.yaml")

        with open(providers_path) as f:
            prov_config = yaml.safe_load(f)

        for name, cfg in prov_config.get("providers", {}).items():
            api_key = resolve_env(cfg.get("api_key", ""))
            prov_cfg = ProviderConfig(
                name=name,
                provider_type=cfg["type"],
                base_url=resolve_env(cfg.get("base_url", "")),
                api_key=api_key if api_key else None,
                models=[ModelInfo(**m) for m in cfg.get("models", [])],
            )

            if cfg["type"] == "opencode":
                provider = OpenCodeProvider(prov_cfg)
            elif cfg["type"] == "openai_oauth":
                provider = OpenAIOAuthProvider(prov_cfg)
            elif cfg["type"] == "openrouter":
                provider = OpenRouterProvider(prov_cfg)
            elif cfg["type"] in ("openai_compat", "ollama"):
                provider = OpenAICompatProvider(prov_cfg)
            else:
                continue

            self.providers[name] = provider
            for m in prov_cfg.models:
                self.model_to_provider[m.id] = name

        self.fallback_order = prov_config.get("provider_fallback", list(self.providers.keys()))

        if os.path.exists(models_path):
            with open(models_path) as f:
                models_config = yaml.safe_load(f)
            for key, val in models_config.items():
                if val in ("premium", "balanced", "economy", "free"):
                    self.agent_profiles[key] = val
                else:
                    self.profile_models[key] = val

        self._loaded = True

    def set_profile_model(self, profile: str, model_id: str, provider: str = ""):
        """Manually configure which model a profile uses."""
        self.profile_models[profile] = model_id
        if provider:
            self.model_to_provider[model_id] = provider

    def resolve_model(self, agent_name: str) -> str:
        """Resolve agent name → profile → model_id."""
        profile = self.agent_profiles.get(agent_name, "balanced")
        model_id = self.profile_models.get(profile, "")
        if not model_id:
            # Fallback: use provider-specific defaults
            return self._default_model_for(profile)
        return model_id

    def _default_model_for(self, tier: str) -> str:
        defaults = {
            "premium": "glm-5.1",
            "balanced": "minimax/minimax-m2.5",
            "economy": "qwen2.5:7b",
            "free": "google/gemini-2.0-flash-exp:free",
        }
        return defaults.get(tier, "glm-5.1")

    def get_provider_for_model(self, model_id: str) -> BaseProvider | None:
        """Get the provider that handles a model, with fallback."""
        prov_name = self.model_to_provider.get(model_id)
        if prov_name and prov_name in self.providers:
            return self.providers[prov_name]

        # Try fallback order
        for name in self.fallback_order:
            if name in self.providers and self.providers[name].is_available:
                return self.providers[name]

        return None

    async def generate(self, req: LLMRequest) -> LLMResponse:
        """Generate via the right provider, with fallback."""
        provider = self.get_provider_for_model(req.model)
        if not provider:
            raise RuntimeError(
                f"No available provider for model '{req.model}'. "
                f"Check providers.yaml and set required API keys."
            )
        return await provider.generate(req)

    def generate_sync(self, req: LLMRequest) -> LLMResponse:
        """Synchronous generation."""
        provider = self.get_provider_for_model(req.model)
        if not provider:
            raise RuntimeError(
                f"No available provider for model '{req.model}'"
            )
        return provider.generate_sync(req)

    def list_available_providers(self) -> list[str]:
        return [n for n, p in self.providers.items() if p.is_available]

    def list_models(self) -> list[dict]:
        result = []
        for name, prov in self.providers.items():
            for m in prov.config.models:
                result.append({
                    "id": m.id,
                    "name": m.name,
                    "provider": name,
                    "tier": m.cost_tier,
                    "available": prov.is_available,
                })
        return result
