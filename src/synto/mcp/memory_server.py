"""Memory MCP Server — exposes memory tools via FastMCP."""

from __future__ import annotations

import os

from fastmcp import FastMCP

from synto.mcp.memory_tools import MemoryToolLayer
from synto.memory.store import MemoryStore

_store: MemoryStore | None = None
_tools: MemoryToolLayer | None = None


def get_store() -> MemoryStore:
    global _store
    db_path = os.environ.get("HERMES_MEMORY_DB", "memory_store.db")
    if _store is None or str(_store.db_path) != db_path:
        if _store is not None:
            try:
                _store.close()
            except Exception:
                pass
        _store = MemoryStore(db_path)
    return _store


def get_tools() -> MemoryToolLayer:
    global _tools
    store = get_store()
    if _tools is None or _tools.store is not store:
        _tools = MemoryToolLayer(store)
    return _tools


mcp = FastMCP("synto-memory")


@mcp.tool()
def memory_search(query: str, project_id: str = "", limit: int = 20) -> list[dict]:
    """Full-text search across memory items."""
    return get_tools().search(query=query, project_id=project_id, limit=limit)


@mcp.tool()
def memory_get_item(memory_id: str) -> dict | None:
    """Get a specific memory item by ID."""
    return get_tools().get_item(memory_id)


@mcp.tool()
def memory_get_tree(project_id: str) -> dict:
    """Return the project -> feature -> topic tree with memory counts."""
    return get_tools().get_tree(project_id)


@mcp.tool()
def memory_build_pack(agent_id: str, task: str, project_id: str, token_budget: int = 4000) -> dict:
    """Build a bounded memory pack for a specific agent and task."""
    return get_tools().build_pack(
        agent_id=agent_id,
        task=task,
        project_id=project_id,
        token_budget=token_budget,
    )


@mcp.tool()
def memory_add_candidate(
    project_id: str,
    content: str,
    source_agent: str = "",
    kind: str = "note",
    title: str = "",
    reasoning: str = "",
    feature_id: str = "",
    topic_id: str = "",
    tags: list[str] | None = None,
) -> str:
    """Add a memory candidate for review."""
    return get_tools().add_candidate(
        project_id=project_id,
        content=content,
        source_agent=source_agent,
        kind=kind,
        title=title,
        reasoning=reasoning,
        feature_id=feature_id,
        topic_id=topic_id,
        tags=tags,
    )


@mcp.tool()
def memory_list_candidates(project_id: str = "") -> list[dict]:
    """List pending memory candidates."""
    return get_tools().list_candidates(project_id=project_id)


@mcp.tool()
def memory_commit_candidate(candidate_id: str, actor: str = "mcp") -> str:
    """Commit a candidate to permanent memory. Returns item ID."""
    return get_tools().commit_candidate(candidate_id, actor=actor)


@mcp.tool()
def memory_reject_candidate(candidate_id: str, reason: str = "", actor: str = "mcp") -> str:
    """Reject and discard a candidate."""
    return get_tools().reject_candidate(candidate_id, reason=reason, actor=actor)


@mcp.tool()
def memory_link_items(source_id: str, target_id: str, link_type: str = "related") -> str:
    """Create a link between two memory items."""
    return get_tools().link_items(source_id, target_id, link_type)


@mcp.tool()
def memory_forget(memory_id: str, actor: str = "mcp") -> str:
    """Soft-delete/archive a memory item."""
    return get_tools().forget(memory_id, actor=actor)


@mcp.tool()
def memory_stats() -> dict:
    """Get memory store statistics."""
    return get_tools().stats()


@mcp.tool()
def memory_get_audit_log(limit: int = 50) -> list[dict]:
    """Get recent audit entries."""
    return get_tools().get_audit_log(limit=limit)


@mcp.tool()
def memory_list_projects() -> list[dict]:
    """List all projects."""
    return get_tools().list_projects()


@mcp.tool()
def memory_create_project(slug: str, name: str) -> str:
    """Create a new project if it does not already exist."""
    return get_tools().create_project(slug, name)


if __name__ == "__main__":
    mcp.run()
