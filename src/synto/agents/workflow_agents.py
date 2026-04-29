"""Specialized agents for the Synto workflow."""

from __future__ import annotations
from synto.config.llm_router import LLMMultiProvider
from synto.agents.base import BaseAgent


class DiscoveryAgent(BaseAgent):
    """Understands the task, gathers context, identifies constraints."""

    name = "DiscoveryAgent"
    system_prompt = (
        "You are a Discovery Agent. Your job is to analyze tasks, "
        "identify requirements, constraints, dependencies, and edge cases. "
        "Output a structured analysis with sections: Requirements, Constraints, "
        "Dependencies, Risks, and Recommendations."
    )
    model_override = ""  # uses balanced profile


class PlannerAgent(BaseAgent):
    """Creates detailed implementation plans."""

    name = "PlannerAgent"
    system_prompt = (
        "You are a Planner Agent. Given a task and discovery analysis, "
        "create a detailed, step-by-step implementation plan. "
        "Include: Architecture decisions, file structure, component breakdown, "
        "data flow, testing strategy, and estimated complexity. "
        "Be specific and actionable."
    )
    model_override = ""  # uses premium profile


class ImplementerAgent(BaseAgent):
    """Executes the plan — generates code, configs, etc."""

    name = "ImplementerAgent"
    system_prompt = (
        "You are an Implementer Agent. Given a plan, generate the actual code "
        "and configuration needed. Output production-quality code with proper "
        "error handling, comments, and structure. Use code blocks for each file."
    )
    model_override = ""  # uses premium profile


class TesterAgent(BaseAgent):
    """Generates and runs tests."""

    name = "TesterAgent"
    system_prompt = (
        "You are a Tester Agent. Given the implementation, generate comprehensive "
        "tests including unit tests, integration tests, and edge cases. "
        "Identify potential bugs and suggest fixes."
    )
    model_override = ""  # uses balanced profile


class QAGateAgent(BaseAgent):
    """Evaluates quality gates — pass/fail with reasoning."""

    name = "QAGateAgent"
    system_prompt = (
        "You are a Quality Gate Agent. Evaluate whether the implementation "
        "meets the plan and requirements. Check for: correctness, completeness, "
        "error handling, and test coverage. "
        "Respond with: PASSED or FAILED, followed by detailed reasoning."
    )
    model_override = ""  # uses premium profile


def create_agents(router: LLMMultiProvider | None = None, memory_by_agent: dict = {}) -> dict[str, BaseAgent]:
    """Factory: create all workflow agents with the given router."""
    agents = {}
    for cls in (DiscoveryAgent, PlannerAgent, ImplementerAgent, TesterAgent, QAGateAgent):
        mem = memory_by_agent.get(cls.name, {}).get("items", 0)
        ctx = f"[Agent has {mem} memory items loaded]" if mem else ""
        agent = cls(router=router, memory_context=ctx)
        agents[cls.name] = agent
    return agents
