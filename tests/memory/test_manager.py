"""Regression tests for MemoryManager behavior."""

import os
import tempfile

import pytest

from synto.memory import MemoryCandidate, MemoryKind, MemoryManager, MemoryStore


@pytest.fixture
def store():
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        path = f.name
    s = MemoryStore(path)
    yield s
    s.close()
    os.unlink(path)


def test_auto_commit_safe_consumes_redacted_candidate(store: MemoryStore):
    pid = store.create_project("proj", "Project")
    cid = store.add_candidate(
        MemoryCandidate(
            project_id=pid,
            kind=MemoryKind.SOLUTION,
            content="api_key=[REDACTED]",
            source_agent="tester",
        )
    )

    mgr = MemoryManager(store)
    item_id = mgr.auto_commit_safe(cid, actor="tester")

    assert item_id is not None
    assert store.get_memory_item(item_id) is not None
    assert store.list_candidates() == []
