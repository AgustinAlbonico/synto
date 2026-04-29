"""Tests for memory Pydantic models."""

import json
import pytest

from synto.memory.models import (
    MemoryItem, MemoryKind, MemoryStatus,
    MemoryCandidate, MemoryLink, MemoryPack,
    MemoryPackItem, TaskContext, MemorySearchResult, MemoryAuditEntry,
)


def test_create_memory_item():
    item = MemoryItem(
        project_id="test-proj",
        kind=MemoryKind.DECISION,
        content="Use UTC for all timestamps",
    )
    assert item.id
    assert item.kind == MemoryKind.DECISION
    assert item.status == MemoryStatus.ACTIVE
    assert item.content == "Use UTC for all timestamps"
    assert item.project_id == "test-proj"


def test_memory_item_requires_content():
    with pytest.raises(Exception):
        MemoryItem(project_id="p", content="")


def test_memory_item_requires_project_id():
    with pytest.raises(Exception):
        MemoryItem(content="some content")


def test_memory_item_db_roundtrip():
    item = MemoryItem(
        project_id="proj1",
        feature_id="auth",
        kind=MemoryKind.CONFIG,
        content="DB_HOST=localhost",
        tags=["config", "db"],
        metadata={"source": "setup"},
    )
    row = item.to_db_row()
    restored = MemoryItem.from_db_row(row)
    assert restored.id == item.id
    assert restored.kind == item.kind
    assert restored.tags == ["config", "db"]
    assert restored.metadata["source"] == "setup"


def test_memory_candidate_to_item():
    candidate = MemoryCandidate(
        source_agent="backend-agent",
        kind=MemoryKind.SOLUTION,
        title="Fix auth timeout",
        content="Increase timeout to 30s",
        project_id="proj1",
        reasoning="Users experiencing timeouts",
    )
    item = candidate.to_memory_item()
    assert item.kind == MemoryKind.SOLUTION
    assert item.content == "Increase timeout to 30s"
    assert item.metadata["source_agent"] == "backend-agent"


def test_memory_pack_respects_budget():
    pack = MemoryPack(agent_id="test", token_budget=100)
    item1 = MemoryPackItem(id="1", title="t1", snippet="short", source="p", importance=0.5)
    item2 = MemoryPackItem(id="2", title="t2", snippet="x" * 5000, source="p", importance=0.5)

    assert pack.add_item(item1) is True
    assert pack.add_item(item2) is False  # exceeds budget


def test_memory_pack_adds_items():
    pack = MemoryPack(agent_id="test", token_budget=10000)
    for i in range(5):
        item = MemoryPackItem(id=str(i), title=f"t{i}", snippet="hello world", source="p", importance=0.5)
        pack.add_item(item)
    assert len(pack.items) == 5
    assert pack.total_tokens_estimate > 0


def test_memory_link_validation():
    link = MemoryLink(source_id="a", target_id="b", link_type="depends_on", strength=0.8)
    assert link.link_type == "depends_on"

    with pytest.raises(Exception):
        MemoryLink(source_id="", target_id="b")


def test_task_context():
    ctx = TaskContext(task="build login", project_id="proj1", agent_ids=["auth-agent"])
    assert ctx.task == "build login"
    assert ctx.project_id == "proj1"
    assert len(ctx.agent_ids) == 1


def test_memory_audit_entry():
    entry = MemoryAuditEntry(action="commit", actor="memory-manager", target_id="abc123", details="approved")
    assert entry.action == "commit"
    assert entry.target_id == "abc123"


def test_memory_item_word_count():
    item = MemoryItem(project_id="p", content="one two three four five")
    assert item.word_count() == 5


def test_memory_item_importance_bounds():
    item = MemoryItem(project_id="p", content="test", importance=0.0)
    assert item.importance == 0.0

    with pytest.raises(Exception):
        MemoryItem(project_id="p", content="test", importance=1.5)


def test_memory_item_iso_timestamps():
    item = MemoryItem(project_id="p", content="test")
    assert "T" in item.created_iso
    assert "T" in item.updated_iso
