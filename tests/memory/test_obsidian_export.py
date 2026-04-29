"""Tests for Obsidian export."""

import os
import tempfile
import pytest

from synto.memory import MemoryStore, MemoryItem, MemoryKind
from synto.memory.obsidian_export import export_to_obsidian, _memory_to_markdown


@pytest.fixture
def store():
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        path = f.name
    s = MemoryStore(path)
    yield s
    s.close()
    os.unlink(path)


def test_memory_to_markdown():
    item = MemoryItem(
        project_id="p",
        kind=MemoryKind.DECISION,
        title="Use PostgreSQL",
        content="We decided to use PostgreSQL for the main database",
        tags=["database", "decision"],
        importance=0.8,
    )
    md = _memory_to_markdown(item)
    assert "# Use PostgreSQL" in md
    assert "**Kind:** decision" in md
    assert "We decided to use PostgreSQL" in md
    assert "#database" in md
    assert "#decision" in md


def test_export_to_obsidian(store: MemoryStore):
    pid = store.create_project("myproj", "My Project")
    fid = store.create_feature(pid, "auth", "Auth")
    tid = store.create_topic(pid, "login", "Login", feature_id=fid)

    store.add_memory_item(MemoryItem(
        project_id=pid, feature_id=fid, topic_id=tid,
        kind=MemoryKind.DECISION, title="JWT Auth",
        content="Use JWT tokens for authentication",
    ))

    with tempfile.TemporaryDirectory() as tmpdir:
        files = export_to_obsidian(store, tmpdir, project_id=pid)
        assert len(files) == 1
        filepath = list(files.keys())[0]
        assert Path(filepath).exists()
        content = Path(filepath).read_text()
        assert "JWT Auth" in content


def test_export_empty_project(store: MemoryStore):
    pid = store.create_project("empty", "Empty Project")
    with tempfile.TemporaryDirectory() as tmpdir:
        files = export_to_obsidian(store, tmpdir, project_id=pid)
        assert len(files) == 0


from pathlib import Path
