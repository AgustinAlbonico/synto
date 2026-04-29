"""Memory MCP Server — exposes memory tools via FastMCP."""

import os
from fastmcp import FastMCP

from synto.memory.store import MemoryStore
from synto.memory.models import MemoryCandidate, MemoryKind

_db_path = os.environ.get("HERMES_MEMORY_DB", "memory_store.db")
_store: MemoryStore | None = None

def get_store() -> MemoryStore:
    global _store
    if _store is None:
        _store = MemoryStore(_db_path)
    return _store

mcp = FastMCP("hermes-memory")


@mcp.tool()
def memory_search(query: str, project_id: str = "", limit: int = 20) -> list[dict]:
    """Full-text search across memory items."""
    store = get_store()
    results = store.search(query, project_id=project_id, limit=limit)
    return [
        {
            "id": r.item.id,
            "project_id": r.item.project_id,
            "kind": r.item.kind.value,
            "title": r.item.title,
            "content": r.item.content[:300],
            "score": round(r.score, 3),
            "importance": r.item.importance,
        }
        for r in results
    ]


@mcp.tool()
def memory_get_item(memory_id: str) -> dict | None:
    """Get a specific memory item by ID."""
    store = get_store()
    item = store.get_memory_item(memory_id)
    if not item:
        return None
    return {
        "id": item.id,
        "project_id": item.project_id,
        "feature_id": item.feature_id,
        "topic_id": item.topic_id,
        "kind": item.kind.value,
        "status": item.status.value,
        "title": item.title,
        "content": item.content,
        "tags": item.tags,
        "importance": item.importance,
        "confidence": item.confidence,
        "metadata": item.metadata,
    }


@mcp.tool()
def memory_add_item(project_id: str, content: str, kind: str = "note", title: str = "", feature_id: str = "", topic_id: str = "", tags: list[str] | None = None, importance: float = 0.5) -> str:
    """Add a new memory item."""
    store = get_store()
    from synto.memory import MemoryItem, MemoryKind
    item = MemoryItem(
        project_id=project_id,
        feature_id=feature_id,
        topic_id=topic_id,
        kind=MemoryKind(kind),
        title=title,
        content=content,
        tags=tags or [],
        importance=importance,
    )
    return store.add_memory_item(item)


@mcp.tool()
def memory_list_candidates(project_id: str = "") -> list[dict]:
    """List pending memory candidates."""
    store = get_store()
    return store.list_candidates(project_id=project_id)


@mcp.tool()
def memory_commit_candidate(candidate_id: str, actor: str = "mcp") -> str:
    """Commit a candidate to permanent memory. Returns item ID."""
    store = get_store()
    return store.commit_candidate(candidate_id, actor=actor)


@mcp.tool()
def memory_reject_candidate(candidate_id: str, reason: str = "", actor: str = "mcp") -> str:
    """Reject and discard a candidate."""
    store = get_store()
    store.reject_candidate(candidate_id, reason=reason, actor=actor)
    return "rejected"


@mcp.tool()
def memory_add_candidate(project_id: str, content: str, source_agent: str = "", kind: str = "note", title: str = "", reasoning: str = "") -> str:
    """Add a memory candidate for review."""
    store = get_store()
    c = MemoryCandidate(
        source_agent=source_agent,
        kind=MemoryKind(kind),
        title=title,
        content=content,
        project_id=project_id,
        reasoning=reasoning,
    )
    return store.add_candidate(c)


@mcp.tool()
def memory_stats() -> dict:
    """Get memory store statistics."""
    store = get_store()
    return store.stats()


@mcp.tool()
def memory_get_audit_log(limit: int = 50) -> list[dict]:
    """Get recent audit entries."""
    store = get_store()
    return store.get_audit_log(limit=limit)


@mcp.tool()
def memory_list_projects() -> list[dict]:
    """List all projects."""
    store = get_store()
    return store.list_projects()


@mcp.tool()
def memory_create_project(slug: str, name: str) -> str:
    """Create a new project."""
    store = get_store()
    return store.create_project(slug, name)


@mcp.tool()
def memory_link_items(source_id: str, target_id: str, link_type: str = "related") -> str:
    """Create a link between two memory items."""
    store = get_store()
    return store.link_items(source_id, target_id, link_type)


@mcp.tool()
def memory_get_links(memory_id: str) -> list[dict]:
    """Get all links for a memory item."""
    store = get_store()
    links = store.get_links(memory_id)
    return [
        {"id": l.id, "source": l.source_id, "target": l.target_id, "type": l.link_type, "strength": l.strength}
        for l in links
    ]


if __name__ == "__main__":
    mcp.run()
