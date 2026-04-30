"""Specialized agents for the Synto workflow — generated from AGENT-REGISTRY.yaml."""

from __future__ import annotations

from pathlib import Path

from synto.config.llm_router import LLMMultiProvider
from synto.agents.base import BaseAgent


# ─────────────────────────────────────────────────────────────
# MCP tool lists (expanded from mcp_capability_groups)
# ─────────────────────────────────────────────────────────────
_FILESYSTEM_READ = [
    "mcp_filesystem_read_text_file",
    "mcp_filesystem_list_directory",
    "mcp_filesystem_search_files",
]

_FILESYSTEM_WRITE = [
    "mcp_filesystem_write_file",
    "mcp_filesystem_edit_file",
    "mcp_filesystem_create_directory",
]

_GITHUB_READ = [
    "mcp_github_get_file_contents",
    "mcp_github_list_pull_requests",
    "mcp_github_get_pull_request",
    "mcp_github_get_pull_request_files",
]

_SHELL_READONLY = [
    "terminal_readonly_commands",
]

_SHELL_EXECUTE = [
    "terminal_safe_execute",
]

_WEB_RESEARCH = [
    "web_search",
    "web_extract",
]

_BROWSER = [
    "browser_navigate",
    "browser_snapshot",
    "browser_click",
    "browser_type",
]

_MEMORY = [
    "obsidian_vault",
    "fact_store",
    "session_search",
    "memory_search",
    "memory_get_item",
    "memory_get_tree",
    "memory_build_pack",
    "memory_add_candidate",
    "memory_list_candidates",
    "memory_commit_candidate",
    "memory_reject_candidate",
    "memory_link_items",
    "memory_forget",
    "memory_export_obsidian",
]
def _registry_prompt_fallback(agent_name: str) -> str:
    return (
        f"Fallback prompt for {agent_name}. Canonical system prompt lives in AGENT-REGISTRY.yaml "
        "and should be compiled through PromptCompiler/AgentFactory. If instantiated directly, "
        "stay within your declared role, tools, and restrictions."
    )


# ═══════════════════════════════════════════════════════════
# Layer 0 — User-facing orchestrator
# ═══════════════════════════════════════════════════════════

class HermesOrchestrator(BaseAgent):
    """Layer 0 — Single point of contact with the user and top-level coordinator."""

    name = "HermesOrchestrator"
    model_profile = "strategic"
    allowed_mcp_tools: list[str] = _FILESYSTEM_READ + _MEMORY

    system_prompt = _registry_prompt_fallback(name)


# ═══════════════════════════════════════════════════════════
# Layer 1 — Domain engineering lead
# ═══════════════════════════════════════════════════════════

class CodeOrchestrator(BaseAgent):
    """Layer 1 — Engineering lead for the Code domain. Coordinates the full technical workflow."""

    name = "CodeOrchestrator"
    model_profile = "strategic"
    allowed_mcp_tools: list[str] = _FILESYSTEM_READ + _FILESYSTEM_WRITE + _GITHUB_READ + _MEMORY

    system_prompt = _registry_prompt_fallback(name)


# ═══════════════════════════════════════════════════════════
# Layer 2 — Specialized agents
# ═══════════════════════════════════════════════════════════

class BusinessAnalyst(BaseAgent):
    """Layer 2 — Functional analyst. Understands the problem before any solution exists."""

    name = "BusinessAnalyst"
    model_profile = "strategic"
    allowed_mcp_tools: list[str] = _FILESYSTEM_READ + _MEMORY + _WEB_RESEARCH

    system_prompt = _registry_prompt_fallback(name)


class ProductManager(BaseAgent):
    """Layer 2 — Operational product owner. Converts discovery into an actionable PRD."""

    name = "ProductManager"
    model_profile = "strategic"
    allowed_mcp_tools: list[str] = _FILESYSTEM_READ + _FILESYSTEM_WRITE + _MEMORY

    system_prompt = _registry_prompt_fallback(name)


class Planner(BaseAgent):
    """Layer 2 — Technical planner. Converts PRD into an executable task graph."""

    name = "Planner"
    model_profile = "strategic"
    allowed_mcp_tools: list[str] = _FILESYSTEM_READ + _GITHUB_READ

    system_prompt = _registry_prompt_fallback(name)


class CodebaseExplorer(BaseAgent):
    """Layer 2 — Codebase explorer. Maps the repository without modifying it."""

    name = "CodebaseExplorer"
    model_profile = "heavy_coding"
    allowed_mcp_tools: list[str] = _FILESYSTEM_READ + _GITHUB_READ + _SHELL_READONLY

    system_prompt = _registry_prompt_fallback(name)


class Architect(BaseAgent):
    """Layer 2 — Technical architect for backend/API/data."""

    name = "Architect"
    model_profile = "strategic"
    allowed_mcp_tools: list[str] = _FILESYSTEM_READ + _FILESYSTEM_WRITE

    system_prompt = _registry_prompt_fallback(name)


class SystemDesigner(BaseAgent):
    """Layer 2 — UI/UX designer and design system guardian."""

    name = "SystemDesigner"
    model_profile = "strategic"
    allowed_mcp_tools: list[str] = _FILESYSTEM_READ + _FILESYSTEM_WRITE + _BROWSER

    system_prompt = _registry_prompt_fallback(name)


class Tester(BaseAgent):
    """Layer 2 — TDD specialist and test execution expert."""

    name = "Tester"
    model_profile = "balanced"
    allowed_mcp_tools: list[str] = _FILESYSTEM_READ + _FILESYSTEM_WRITE + _SHELL_EXECUTE

    system_prompt = _registry_prompt_fallback(name)


class BackendImplementer(BaseAgent):
    """Layer 2 — Backend developer. Implements APIs, DB, and business logic."""

    name = "BackendImplementer"
    model_profile = "heavy_coding"
    allowed_mcp_tools: list[str] = _FILESYSTEM_READ + _FILESYSTEM_WRITE + _SHELL_EXECUTE + _GITHUB_READ

    system_prompt = _registry_prompt_fallback(name)


# ═══════════════════════════════════════════════════════════
# Layer 2 — Specialized agents (continued)
# ═══════════════════════════════════════════════════════════

class FrontendImplementer(BaseAgent):
    """Layer 2 — Frontend developer. Implements UI respecting the design system."""

    name = "FrontendImplementer"
    model_profile = "heavy_coding"
    allowed_mcp_tools: list[str] = _FILESYSTEM_READ + _FILESYSTEM_WRITE + _SHELL_EXECUTE + _BROWSER

    system_prompt = _registry_prompt_fallback(name)


class ContractAligner(BaseAgent):
    """Layer 2 — Contract verifier for frontend-backend alignment."""

    name = "ContractAligner"
    model_profile = "balanced"
    allowed_mcp_tools: list[str] = _FILESYSTEM_READ + _SHELL_READONLY

    system_prompt = _registry_prompt_fallback(name)


class Reviewer(BaseAgent):
    """Layer 2 — General code reviewer."""

    name = "Reviewer"
    model_profile = "balanced"
    allowed_mcp_tools: list[str] = _FILESYSTEM_READ + _GITHUB_READ

    system_prompt = _registry_prompt_fallback(name)


class SecurityReviewer(BaseAgent):
    """Layer 2 — Security review specialist."""

    name = "SecurityReviewer"
    model_profile = "balanced"
    allowed_mcp_tools: list[str] = _FILESYSTEM_READ + _SHELL_READONLY + _GITHUB_READ

    system_prompt = _registry_prompt_fallback(name)


class QAGatekeeper(BaseAgent):
    """Layer 2 — Final quality gate against PRD, spec, tests, and design system."""

    name = "QAGatekeeper"
    model_profile = "strategic"
    allowed_mcp_tools: list[str] = _FILESYSTEM_READ + _SHELL_READONLY

    system_prompt = _registry_prompt_fallback(name)


class DependencyChecker(BaseAgent):
    """Layer 2 — Impact and compatibility verifier."""

    name = "DependencyChecker"
    model_profile = "balanced"
    allowed_mcp_tools: list[str] = _FILESYSTEM_READ + _SHELL_READONLY + _GITHUB_READ

    system_prompt = _registry_prompt_fallback(name)


class TechnicalWriter(BaseAgent):
    """Layer 2 — Technical writer and deliverable artifact generator."""

    name = "TechnicalWriter"
    model_profile = "balanced"
    allowed_mcp_tools: list[str] = _FILESYSTEM_READ + _FILESYSTEM_WRITE + _MEMORY

    system_prompt = _registry_prompt_fallback(name)


class ReleaseManager(BaseAgent):
    """Layer 2 — Branch, PR, release notes, and versioning manager."""

    name = "ReleaseManager"
    model_profile = "balanced"
    allowed_mcp_tools: list[str] = _FILESYSTEM_READ + _GITHUB_READ + [
        "mcp_github_create_branch",
        "mcp_github_create_pull_request",
        "mcp_github_push_files",
        "mcp_github_create_or_update_file",
    ] + _SHELL_READONLY

    system_prompt = _registry_prompt_fallback(name)


class Builder(BaseAgent):
    """Layer 2 — DevOps builder/deployer. Executes deploys and operational verifications."""

    name = "Builder"
    model_profile = "balanced"
    allowed_mcp_tools: list[str] = _FILESYSTEM_READ + _SHELL_EXECUTE + _GITHUB_READ

    system_prompt = _registry_prompt_fallback(name)


def _load_default_registry(registry_path: str | Path | None = None):
    """Load the canonical agent registry for compatibility entrypoints."""
    from synto.registry import AgentRegistry

    path = Path(registry_path) if registry_path else Path(__file__).resolve().parents[3] / "AGENT-REGISTRY.yaml"
    if not path.exists():
        return None
    registry = AgentRegistry(str(path))
    registry.load()
    return registry


def create_all_agents(
    router: LLMMultiProvider | None = None,
    memory_by_agent: dict | None = None,
    *,
    registry=None,
    registry_path: str | Path | None = None,
    shared_memory_context: str = "",
) -> dict[str, BaseAgent]:
    """Compatibility wrapper around AgentFactory + PromptCompiler.

    New runtime code should instantiate AgentFactory directly. This legacy helper
    still exists for callers that import it, but it must not bypass the registry
    prompt source of truth.
    """
    from synto.agents.factory import AgentFactory

    resolved_registry = registry if registry is not None else _load_default_registry(registry_path)
    factory = AgentFactory(router=router, registry=resolved_registry)
    return factory.create_all(
        memory_by_agent=memory_by_agent,
        shared_memory_context=shared_memory_context,
    )
