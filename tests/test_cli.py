"""CLI smoke tests."""

import os
import re
import tempfile
from pathlib import Path

import yaml

from synto import cli
from synto.memory import MemoryStore


def _invoke(monkeypatch, capsys, argv):
    monkeypatch.setattr("sys.argv", argv)
    cli.main()
    return capsys.readouterr()


def test_cli_run_executes_workflow(monkeypatch, capsys):
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name

    try:
        out = _invoke(
            monkeypatch,
            capsys,
            ["synto", "run", "Build a login API endpoint", "--project", "cli-proj", "--memory-db", db_path],
        )
        assert "[orchestrator] Running: Build a login API endpoint" in out.out
        assert "=== Run Complete ===" in out.out
    finally:
        os.unlink(db_path)


def test_cli_memory_tree_and_forget(monkeypatch, capsys):
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name

    try:
        add_out = _invoke(
            monkeypatch,
            capsys,
            ["synto", "memory", "add", "remember this", "--project", "cli-proj", "--db", db_path],
        )
        match = re.search(r"Memory added: #(\w+)", add_out.out)
        assert match is not None
        memory_id = match.group(1)

        tree_out = _invoke(
            monkeypatch,
            capsys,
            ["synto", "memory", "tree", "--project", "cli-proj", "--db", db_path],
        )
        assert '"project"' in tree_out.out
        assert '"slug": "cli-proj"' in tree_out.out

        forget_out = _invoke(
            monkeypatch,
            capsys,
            ["synto", "memory", "forget", "--id", memory_id, "--db", db_path],
        )
        assert f"Memory archived: {memory_id}" in forget_out.out

        store = MemoryStore(db_path)
        archived = store.get_memory_item(memory_id)
        store.close()
        assert archived is not None
        assert archived.status.value == "archived"
    finally:
        os.unlink(db_path)


def test_cli_registry_phase_filter(monkeypatch, capsys, tmp_path: Path):
    registry_path = tmp_path / "registry.yaml"
    registry_path.write_text(yaml.safe_dump({
        "agents": {
            "Architect": {
                "role": "Architect",
                "model_profile": "strategic",
                "restrictions": [],
                "mcp_capabilities": [],
                "phase": "planning",
            },
            "Builder": {
                "role": "Builder",
                "model_profile": "heavy_coding",
                "restrictions": [],
                "mcp_capabilities": [],
                "phases": ["implementation"],
            },
        }
    }))

    out = _invoke(
        monkeypatch,
        capsys,
        ["synto", "registry", "--registry", str(registry_path), "--phase", "planning"],
    )

    assert "Loaded 1 agents" in out.out
    assert "Architect" in out.out
    assert "Builder" not in out.out
