"""Tests for the FastMCP memory server contract."""

import asyncio
import os
import tempfile

import pytest

from synto.memory import MemoryItem, MemoryStore
from synto.mcp.memory_tools import MemoryToolLayer
import synto.mcp.memory_server as memory_server


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


def test_memory_server_lists_complete_toolset():
    tools = asyncio.run(memory_server.mcp.list_tools())
    names = {tool.name for tool in tools}

    assert "memory_search" in names
    assert "memory_get_item" in names
    assert "memory_get_tree" in names
    assert "memory_build_pack" in names
    assert "memory_add_candidate" in names
    assert "memory_forget" in names


def test_memory_server_functions_delegate_to_tool_layer(monkeypatch, store: MemoryStore, tool_layer: MemoryToolLayer):
    pid = store.create_project("proj", "Project")
    mid = store.add_memory_item(MemoryItem(project_id=pid, content="server memory"))

    monkeypatch.setattr(memory_server, "get_tools", lambda: tool_layer)

    item = memory_server.memory_get_item(mid)
    tree = memory_server.memory_get_tree("proj")

    assert item is not None
    assert item["content"] == "server memory"
    assert tree["project"]["slug"] == "proj"
