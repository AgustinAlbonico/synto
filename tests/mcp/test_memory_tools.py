"""Tests for the deterministic memory MCP tool layer."""

import os
import tempfile

import pytest

from synto.mcp.memory_tools import MemoryToolLayer
from synto.memory import MemoryItem, MemoryKind, MemoryStore


@pytest.fixture
def store():
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        path = f.name
    s = MemoryStore(path)
    yield s
    s.close()
    os.unlink(path)


@pytest.fixture
def tool_layer(store: MemoryStore):
    return MemoryToolLayer(store)


def test_get_tree_returns_project_feature_topic_counts(store: MemoryStore, tool_layer: MemoryToolLayer):
    pid = store.create_project("proj", "Project")
    fid = store.create_feature(pid, "auth", "Authentication")
    tid = store.create_topic(pid, "login", "Login Flow", feature_id=fid)

    store.add_memory_item(MemoryItem(project_id=pid, feature_id=fid, topic_id=tid, content="topic memory"))
    store.add_memory_item(MemoryItem(project_id=pid, feature_id=fid, content="feature memory"))
    store.add_memory_item(MemoryItem(project_id=pid, content="root memory"))

    tree = tool_layer.get_tree("proj")

    assert tree["project"]["slug"] == "proj"
    assert tree["root_memory_count"] == 1
    assert len(tree["features"]) == 1
    assert tree["features"][0]["slug"] == "auth"
    assert tree["features"][0]["memory_count"] == 2
    assert tree["features"][0]["topics"][0]["slug"] == "login"
    assert tree["features"][0]["topics"][0]["memory_count"] == 1


def test_build_pack_returns_bounded_pack(store: MemoryStore, tool_layer: MemoryToolLayer):
    pid = store.create_project("proj", "Project")
    store.add_memory_item(
        MemoryItem(
            project_id=pid,
            kind=MemoryKind.SOLUTION,
            title="Auth strategy",
            content="Use JWT access tokens and refresh tokens for API sessions.",
        )
    )

    pack = tool_layer.build_pack(
        agent_id="BackendImplementer",
        task="Implement login API",
        project_id="proj",
        token_budget=800,
    )

    assert pack["agent_id"] == "BackendImplementer"
    assert pack["token_budget"] == 800
    assert pack["total_tokens_estimate"] <= 800
    assert isinstance(pack["items"], list)


def test_forget_archives_memory(store: MemoryStore, tool_layer: MemoryToolLayer):
    pid = store.create_project("proj", "Project")
    mid = store.add_memory_item(MemoryItem(project_id=pid, content="temporary note"))

    forgotten_id = tool_layer.forget(mid)
    archived = store.get_memory_item(mid)

    assert forgotten_id == mid
    assert archived is not None
    assert archived.status.value == "archived"
