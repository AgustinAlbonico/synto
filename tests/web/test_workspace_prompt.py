from __future__ import annotations

from pathlib import Path

from synto.web.prompt_improver import improve_prompt
from synto.web.workspace_stack import detect_stack, normalize_user_path


def test_normalize_windows_path_to_wsl():
    path = normalize_user_path(r"C:\Users\agust\Desktop\demo")
    assert str(path).startswith("/mnt/c/Users/agust/Desktop/demo")


def test_detect_stack_node_react_vite_pnpm(tmp_path: Path):
    (tmp_path / "package.json").write_text(
        '{"packageManager":"pnpm@9.0.0","dependencies":{"react":"latest","vite":"latest","typescript":"latest"}}',
        encoding="utf-8",
    )
    (tmp_path / "tsconfig.json").write_text("{}", encoding="utf-8")
    (tmp_path / "pnpm-workspace.yaml").write_text("packages: []", encoding="utf-8")

    stack = detect_stack([str(tmp_path)])
    names = {item["name"] for item in stack["items"]}

    assert "Node.js" in names
    assert "React" in names
    assert "Vite" in names
    assert "TypeScript" in names
    assert "pnpm" in names
    assert stack["paths"] == [str(tmp_path)]


def test_detect_stack_python_fastapi_pytest(tmp_path: Path):
    (tmp_path / "pyproject.toml").write_text(
        """
[project]
dependencies = ["fastapi", "pytest"]

[tool.pytest.ini_options]
testpaths = ["tests"]
""".strip(),
        encoding="utf-8",
    )

    stack = detect_stack([str(tmp_path)])
    names = {item["name"] for item in stack["items"]}

    assert "Python" in names
    assert "FastAPI" in names
    assert "pytest" in names


def test_improve_prompt_includes_workspace_stack_context(tmp_path: Path):
    result = improve_prompt(
        "Agregar login con email",
        workspace={"name": "crm", "paths": [str(tmp_path)]},
        stack={"items": [{"name": "React"}, {"name": "FastAPI"}], "paths": [str(tmp_path)]},
    )

    assert "Objetivo" in result["improved_prompt"]
    assert "Agregar login con email" in result["improved_prompt"]
    assert "Stack detectado: React, FastAPI" in result["improved_prompt"]
    assert result["improvements"]
