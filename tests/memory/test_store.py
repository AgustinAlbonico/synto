"""Tests for the full MemoryStore with schema."""

import os
import tempfile
import pytest

from synto.memory import (
    MemoryStore, MemoryItem, MemoryKind, MemoryStatus,
    MemoryCandidate,
)


@pytest.fixture
def store():
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        path = f.name
    s = MemoryStore(path)
    yield s
    s.close()
    os.unlink(path)


def test_create_project(store: MemoryStore):
    pid = store.create_project("test-proj", "Test Project")
    assert pid
    proj = store.get_project("test-proj")
    assert proj is not None
    assert proj["name"] == "Test Project"


def test_project_slug_unique(store: MemoryStore):
    store.create_project("p1", "Project One")
    with pytest.raises(Exception):
        store.create_project("p1", "Duplicate")


def test_create_feature(store: MemoryStore):
    pid = store.create_project("proj", "Project")
    fid = store.create_feature(pid, "auth", "Authentication")
    assert fid
    features = store.list_features(pid)
    assert len(features) == 1
    assert features[0]["name"] == "Authentication"


def test_create_topic(store: MemoryStore):
    pid = store.create_project("proj", "Project")
    fid = store.create_feature(pid, "auth", "Auth")
    tid = store.create_topic(pid, "login", "Login Flow", feature_id=fid)
    assert tid


def test_add_and_get_memory(store: MemoryStore):
    pid = store.create_project("proj", "Project")
    item = MemoryItem(
        project_id=pid,
        kind=MemoryKind.DECISION,
        content="Use PostgreSQL for production",
    )
    mid = store.add_memory_item(item)
    assert mid == item.id
    retrieved = store.get_memory_item(mid)
    assert retrieved is not None
    assert retrieved.content == "Use PostgreSQL for production"
    assert retrieved.kind == MemoryKind.DECISION


def test_update_memory(store: MemoryStore):
    pid = store.create_project("proj", "Project")
    item = MemoryItem(project_id=pid, content="original")
    mid = store.add_memory_item(item)
    retrieved = store.get_memory_item(mid)
    retrieved.content = "updated content"
    store.update_memory_item(retrieved)
    assert store.get_memory_item(mid).content == "updated content"


def test_delete_memory_archives(store: MemoryStore):
    pid = store.create_project("proj", "Project")
    item = MemoryItem(project_id=pid, content="to delete")
    mid = store.add_memory_item(item)
    store.delete_memory_item(mid)
    # Should be archived, not gone
    retrieved = store.get_memory_item(mid)
    assert retrieved is not None
    assert retrieved.status == MemoryStatus.ARCHIVED
    # Should not appear in list_by_project
    assert mid not in [i.id for i in store.list_by_project(pid)]


def test_list_by_project(store: MemoryStore):
    pid1 = store.create_project("alpha", "Alpha")
    pid2 = store.create_project("beta", "Beta")
    store.add_memory_item(MemoryItem(project_id=pid1, content="a1"))
    store.add_memory_item(MemoryItem(project_id=pid1, content="a2"))
    store.add_memory_item(MemoryItem(project_id=pid2, content="b1"))
    assert len(store.list_by_project(pid1)) == 2
    assert len(store.list_by_project(pid2)) == 1


def test_list_by_hierarchy(store: MemoryStore):
    pid = store.create_project("proj", "Project")
    fid = store.create_feature(pid, "feat", "Feature")
    tid = store.create_topic(pid, "topic", "Topic", feature_id=fid)
    store.add_memory_item(MemoryItem(project_id=pid, feature_id=fid, topic_id=tid, content="m1"))
    store.add_memory_item(MemoryItem(project_id=pid, feature_id=fid, content="m2"))
    store.add_memory_item(MemoryItem(project_id=pid, content="m3"))

    by_topic = store.list_by_hierarchy(pid, feature_id=fid, topic_id=tid)
    assert len(by_topic) == 1

    by_feature = store.list_by_hierarchy(pid, feature_id=fid)
    assert len(by_feature) == 2


def test_search_fts(store: MemoryStore):
    pid = store.create_project("proj", "Project")
    store.add_memory_item(MemoryItem(project_id=pid, content="The quick brown fox"))
    store.add_memory_item(MemoryItem(project_id=pid, content="The lazy dog sleeps"))

    results = store.search("fox")
    assert len(results) >= 1
    assert any("fox" in r.item.content for r in results)


def test_link_items(store: MemoryStore):
    pid = store.create_project("proj", "Project")
    id1 = store.add_memory_item(MemoryItem(project_id=pid, content="source"))
    id2 = store.add_memory_item(MemoryItem(project_id=pid, content="target"))
    lid = store.link_items(id1, id2, "depends_on", 0.8)
    assert lid
    links = store.get_links(id1)
    assert len(links) == 1
    assert links[0].target_id == id2


def test_candidates(store: MemoryStore):
    pid = store.create_project("proj", "Project")
    c = MemoryCandidate(
        source_agent="test-agent",
        kind=MemoryKind.SOLUTION,
        content="Fix the bug",
        project_id=pid,
    )
    cid = store.add_candidate(c)
    assert cid == c.id

    candidates = store.list_candidates()
    assert len(candidates) == 1

    item_id = store.commit_candidate(cid, actor="manager")
    assert item_id
    assert store.get_memory_item(item_id) is not None

    # Candidate should be gone
    assert len(store.list_candidates()) == 0


def test_reject_candidate(store: MemoryStore):
    pid = store.create_project("proj", "Project")
    c = MemoryCandidate(content="bad idea", project_id=pid)
    cid = store.add_candidate(c)
    store.reject_candidate(cid, reason="not useful")
    assert len(store.list_candidates()) == 0


def test_audit_log(store: MemoryStore):
    pid = store.create_project("proj", "Project")
    store.add_memory_item(MemoryItem(project_id=pid, content="test"))
    log = store.get_audit_log()
    assert len(log) >= 1
    assert any(e["action"] == "add" for e in log)


def test_stats(store: MemoryStore):
    pid = store.create_project("proj", "Project")
    store.add_memory_item(MemoryItem(project_id=pid, content="a"))
    store.add_memory_item(MemoryItem(project_id=pid, content="b"))
    stats = store.stats()
    assert stats["total_memories"] == 2
    assert stats["projects"] == 1


def test_redaction_on_save(store: MemoryStore):
    pid = store.create_project("proj", "Project")
    item = MemoryItem(project_id=pid, content="password=secret123")
    store.add_memory_item(item)
    retrieved = store.get_memory_item(item.id)
    assert "secret123" not in retrieved.content
    assert "[REDACTED]" in retrieved.content


def test_list_projects(store: MemoryStore):
    store.create_project("a", "Alpha")
    store.create_project("b", "Beta")
    projects = store.list_projects()
    assert len(projects) == 2
