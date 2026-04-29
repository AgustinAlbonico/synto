"""Memory MCP Server — exposes MemoryStore as MCP tools.

Can run standalone as an MCP server or be embedded in LangGraph nodes.
Tools: add_memory, get_memory, update_memory, delete_memory, search_memories, list_memories, memory_stats, link_memories
"""

import os
from typing import Optional

from synto.memory import MemoryStore, MemoryItem

# Module-level store (singleton per process)
_store: Optional[MemoryStore] = None


def get_store() -> MemoryStore:
    global _store
    if _store is None:
        db_path = os.environ.get("HERMES_MEMORY_DB", "memory_store.db")
        _store = MemoryStore(db_path)
    return _store


# --- Tool functions (called by MCP framework) ---

def add_memory(project: str, feature: str, topic: str, content: str, metadata: str = "{}") -> dict:
    """Add a new memory item.
    
    Args:
        project: Project name
        feature: Feature name
        topic: Topic name
        content: Memory content
        metadata: JSON string with extra metadata
    """
    import json
    store = get_store()
    item = MemoryItem(
        project=project, feature=feature, topic=topic,
        content=content, metadata=json.loads(metadata)
    )
    mid = store.add(item)
    return {"id": mid, "status": "created"}


def get_memory(memory_id: int) -> Optional[dict]:
    """Get a memory item by ID."""
    store = get_store()
    item = store.get(memory_id)
    if item is None:
        return None
    return {
        "id": item.id, "project": item.project, "feature": item.feature,
        "topic": item.topic, "content": item.content,
        "metadata": item.metadata, "trust": item.trust,
    }


def update_memory(memory_id: int, content: str, trust: Optional[float] = None) -> dict:
    """Update an existing memory."""
    store = get_store()
    item = store.get(memory_id)
    if item is None:
        return {"status": "not_found"}
    item.content = content
    if trust is not None:
        item.trust = trust
    store.update(item)
    return {"status": "updated", "id": memory_id}


def delete_memory(memory_id: int) -> dict:
    """Delete a memory item."""
    store = get_store()
    store.delete(memory_id)
    return {"status": "deleted", "id": memory_id}


def search_memories(query: str, project: str = "", limit: int = 20) -> list[dict]:
    """Full-text search across memories."""
    store = get_store()
    results = store.search(query, project=project, limit=limit)
    return [
        {
            "id": r.id, "project": r.project, "feature": r.feature,
            "topic": r.topic, "content": r.content, "trust": r.trust,
        }
        for r in results
    ]


def list_memories(project: str, feature: str = "", topic: str = "") -> list[dict]:
    """List memories by project/feature/topic hierarchy."""
    store = get_store()
    if feature or topic:
        results = store.list_by_hierarchy(project, feature=feature, topic=topic)
    else:
        results = store.list_by_project(project)
    return [
        {
            "id": r.id, "project": r.project, "feature": r.feature,
            "topic": r.topic, "content": r.content, "trust": r.trust,
        }
        for r in results
    ]


def memory_stats() -> dict:
    """Get memory store statistics."""
    store = get_store()
    return store.stats()


def link_memories(source_id: int, target_id: int, link_type: str = "related") -> dict:
    """Create a link between two memories."""
    store = get_store()
    store.link(source_id, target_id, link_type)
    return {"status": "linked", "source": source_id, "target": target_id}
