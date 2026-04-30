"""Workspace stack detection utilities for the Synto web UI."""

from __future__ import annotations

import json
import re
import tomllib
from pathlib import Path
from typing import Any


STACK_META: dict[str, dict[str, str]] = {
    "node": {"name": "Node.js", "icon": "⬢", "category": "runtime"},
    "typescript": {"name": "TypeScript", "icon": "TS", "category": "language"},
    "javascript": {"name": "JavaScript", "icon": "JS", "category": "language"},
    "react": {"name": "React", "icon": "⚛", "category": "frontend"},
    "vite": {"name": "Vite", "icon": "⚡", "category": "frontend"},
    "nextjs": {"name": "Next.js", "icon": "▲", "category": "frontend"},
    "vue": {"name": "Vue", "icon": "V", "category": "frontend"},
    "svelte": {"name": "Svelte", "icon": "S", "category": "frontend"},
    "nestjs": {"name": "NestJS", "icon": "N", "category": "backend"},
    "express": {"name": "Express", "icon": "Ex", "category": "backend"},
    "python": {"name": "Python", "icon": "🐍", "category": "language"},
    "fastapi": {"name": "FastAPI", "icon": "⚡", "category": "backend"},
    "django": {"name": "Django", "icon": "Dj", "category": "backend"},
    "flask": {"name": "Flask", "icon": "Fl", "category": "backend"},
    "pytest": {"name": "pytest", "icon": "✓", "category": "testing"},
    "pnpm": {"name": "pnpm", "icon": "pn", "category": "tooling"},
    "npm": {"name": "npm", "icon": "npm", "category": "tooling"},
    "yarn": {"name": "Yarn", "icon": "Y", "category": "tooling"},
    "turbo": {"name": "Turborepo", "icon": "T", "category": "monorepo"},
    "docker": {"name": "Docker", "icon": "🐳", "category": "infra"},
    "postgres": {"name": "PostgreSQL", "icon": "🐘", "category": "database"},
    "sqlite": {"name": "SQLite", "icon": "◧", "category": "database"},
    "prisma": {"name": "Prisma", "icon": "◇", "category": "database"},
    "electron": {"name": "Electron", "icon": "⚛", "category": "desktop"},
    "tauri": {"name": "Tauri", "icon": "✦", "category": "desktop"},
    "rust": {"name": "Rust", "icon": "Rs", "category": "language"},
    "go": {"name": "Go", "icon": "Go", "category": "language"},
}

_PACKAGE_SIGNALS: dict[str, str] = {
    "react": "react",
    "@vitejs/plugin-react": "react",
    "vite": "vite",
    "next": "nextjs",
    "vue": "vue",
    "svelte": "svelte",
    "@nestjs/core": "nestjs",
    "express": "express",
    "typescript": "typescript",
    "ts-node": "typescript",
    "tsx": "typescript",
    "electron": "electron",
    "@tauri-apps/api": "tauri",
    "prisma": "prisma",
    "@prisma/client": "prisma",
}

_PYTHON_SIGNALS: dict[str, str] = {
    "fastapi": "fastapi",
    "django": "django",
    "flask": "flask",
    "pytest": "pytest",
    "sqlite": "sqlite",
}


WINDOWS_PATH_RE = re.compile(r"^([a-zA-Z]):[\\/](.*)$")


def normalize_user_path(raw_path: str) -> Path:
    """Normalize Linux and Windows paths for the WSL-hosted web process."""
    value = str(raw_path or "").strip().strip('"')
    match = WINDOWS_PATH_RE.match(value)
    if match:
        drive, rest = match.groups()
        value = f"/mnt/{drive.lower()}/{rest.replace('\\\\', '/').replace('\\', '/')}"
    return Path(value).expanduser().resolve()


def _add_signal(signals: dict[str, dict[str, Any]], key: str, reason: str, root: Path) -> None:
    meta = STACK_META.get(key)
    if not meta:
        return
    item = signals.setdefault(
        key,
        {
            "id": key,
            "name": meta["name"],
            "icon": meta["icon"],
            "category": meta["category"],
            "reasons": [],
            "paths": [],
            "confidence": 0.72,
        },
    )
    if reason not in item["reasons"]:
        item["reasons"].append(reason)
    root_str = str(root)
    if root_str not in item["paths"]:
        item["paths"].append(root_str)
    item["confidence"] = min(0.98, item["confidence"] + 0.06)


def _read_json(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return data if isinstance(data, dict) else {}


def _read_text(path: Path, max_chars: int = 120_000) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="ignore")[:max_chars]
    except Exception:
        return ""


def _candidate_package_jsons(root: Path) -> list[Path]:
    candidates = [root / "package.json"]
    for pattern in ("*/package.json", "apps/*/package.json", "packages/*/package.json"):
        candidates.extend(root.glob(pattern))
    return [p for p in candidates if p.exists() and "node_modules" not in p.parts]


def _scan_package_json(root: Path, path: Path, signals: dict[str, dict[str, Any]]) -> None:
    pkg = _read_json(path)
    if not pkg:
        return
    _add_signal(signals, "node", f"{path.name} detectado", root)
    package_manager = str(pkg.get("packageManager", "")).lower()
    if package_manager.startswith("pnpm"):
        _add_signal(signals, "pnpm", "packageManager usa pnpm", root)
    elif package_manager.startswith("yarn"):
        _add_signal(signals, "yarn", "packageManager usa Yarn", root)
    elif package_manager.startswith("npm"):
        _add_signal(signals, "npm", "packageManager usa npm", root)

    deps: dict[str, Any] = {}
    for key in ("dependencies", "devDependencies", "peerDependencies", "optionalDependencies"):
        value = pkg.get(key)
        if isinstance(value, dict):
            deps.update(value)
    for dep_name, stack_key in _PACKAGE_SIGNALS.items():
        if dep_name in deps:
            _add_signal(signals, stack_key, f"dependency {dep_name}", root)

    scripts = " ".join(str(v).lower() for v in (pkg.get("scripts") or {}).values())
    if "vite" in scripts:
        _add_signal(signals, "vite", "scripts usan vite", root)
    if "next" in scripts:
        _add_signal(signals, "nextjs", "scripts usan next", root)


def _scan_python(root: Path, signals: dict[str, dict[str, Any]]) -> None:
    pyproject = root / "pyproject.toml"
    requirements = root / "requirements.txt"
    if pyproject.exists():
        _add_signal(signals, "python", "pyproject.toml detectado", root)
        try:
            data = tomllib.loads(_read_text(pyproject))
        except Exception:
            data = {}
        raw_deps = data.get("project", {}).get("dependencies", []) if isinstance(data, dict) else []
        dep_text = "\n".join(str(dep).lower() for dep in raw_deps)
        tool_section = data.get("tool", {}) if isinstance(data, dict) else {}
        if isinstance(tool_section, dict) and "pytest" in tool_section:
            _add_signal(signals, "pytest", "tool.pytest en pyproject", root)
        for dep_name, stack_key in _PYTHON_SIGNALS.items():
            if dep_name in dep_text:
                _add_signal(signals, stack_key, f"dependency {dep_name}", root)
    if requirements.exists():
        _add_signal(signals, "python", "requirements.txt detectado", root)
        text = _read_text(requirements).lower()
        for dep_name, stack_key in _PYTHON_SIGNALS.items():
            if dep_name in text:
                _add_signal(signals, stack_key, f"requirements incluye {dep_name}", root)


def _scan_common_files(root: Path, signals: dict[str, dict[str, Any]]) -> None:
    if (root / "tsconfig.json").exists():
        _add_signal(signals, "typescript", "tsconfig.json detectado", root)
    if (root / "pnpm-workspace.yaml").exists() or (root / "pnpm-lock.yaml").exists():
        _add_signal(signals, "pnpm", "workspace/lockfile pnpm detectado", root)
    if (root / "package-lock.json").exists():
        _add_signal(signals, "npm", "package-lock.json detectado", root)
    if (root / "yarn.lock").exists():
        _add_signal(signals, "yarn", "yarn.lock detectado", root)
    if (root / "turbo.json").exists():
        _add_signal(signals, "turbo", "turbo.json detectado", root)
    if (root / "Dockerfile").exists() or list(root.glob("docker-compose*.yml")) or list(root.glob("docker-compose*.yaml")):
        _add_signal(signals, "docker", "Dockerfile/docker-compose detectado", root)
    compose_text = "\n".join(_read_text(p).lower() for p in list(root.glob("docker-compose*.yml")) + list(root.glob("docker-compose*.yaml")))
    if "postgres" in compose_text or "postgresql" in compose_text:
        _add_signal(signals, "postgres", "docker-compose menciona postgres", root)
    if (root / "prisma" / "schema.prisma").exists():
        _add_signal(signals, "prisma", "prisma/schema.prisma detectado", root)
    if (root / "src-tauri").exists() or (root / "tauri.conf.json").exists():
        _add_signal(signals, "tauri", "src-tauri/tauri.conf detectado", root)
        _add_signal(signals, "rust", "Tauri usa Rust", root)
    if (root / "Cargo.toml").exists():
        _add_signal(signals, "rust", "Cargo.toml detectado", root)
    if (root / "go.mod").exists():
        _add_signal(signals, "go", "go.mod detectado", root)
    if (root / "memory_store.db").exists() or list(root.glob("*.sqlite")) or list(root.glob("*.sqlite3")):
        _add_signal(signals, "sqlite", "base SQLite local detectada", root)


def detect_stack(raw_paths: list[str]) -> dict[str, Any]:
    """Detect the technology stack for one or more workspace folders."""
    roots: list[Path] = []
    invalid: list[str] = []
    for raw in raw_paths:
        path = normalize_user_path(raw)
        if path.exists() and path.is_dir():
            if path not in roots:
                roots.append(path)
        else:
            invalid.append(str(raw))

    signals: dict[str, dict[str, Any]] = {}
    for root in roots:
        for package_json in _candidate_package_jsons(root):
            _scan_package_json(root, package_json, signals)
        _scan_python(root, signals)
        _scan_common_files(root, signals)

    items = sorted(
        signals.values(),
        key=lambda item: (
            {"language": 0, "runtime": 1, "frontend": 2, "backend": 3, "database": 4, "infra": 5, "tooling": 6, "monorepo": 7, "desktop": 8, "testing": 9}.get(item["category"], 10),
            item["name"],
        ),
    )
    primary_language = next((item["name"] for item in items if item["category"] == "language"), "")
    summary = " · ".join(item["name"] for item in items[:8]) if items else "No se detectó stack todavía"
    return {
        "paths": [str(root) for root in roots],
        "invalid_paths": invalid,
        "items": items,
        "summary": summary,
        "primary_language": primary_language,
        "confidence": round(sum(item["confidence"] for item in items) / len(items), 2) if items else 0,
    }
