from __future__ import annotations

import json
from pathlib import Path

import yaml

from synto.registry import SkillLoader, SkillRegistry
from synto.state import StateStore


def _create_skill(
    root: Path,
    name: str,
    *,
    description: str = "",
    tags: list[str] | None = None,
    body: str = "Skill content here.",
    extra: dict | None = None,
) -> Path:
    skill_dir = root / name
    skill_dir.mkdir(parents=True, exist_ok=True)
    frontmatter = {"name": name, "description": description}
    if tags is not None:
        frontmatter["tags"] = tags
    if extra:
        frontmatter.update(extra)
    content = "---\n" + yaml.safe_dump(frontmatter, sort_keys=False) + "---\n" + f"# {name}\n\n{body}"
    skill_file = skill_dir / "SKILL.md"
    skill_file.write_text(content, encoding="utf-8")
    return skill_file


def test_skill_registry_infers_tags_when_frontmatter_has_none(tmp_path: Path):
    _create_skill(
        tmp_path,
        "pytest-helper",
        description="Run pytest suites, write tests, and report coverage",
        tags=None,
    )

    registry = SkillRegistry(skills_dirs=[str(tmp_path)])
    meta = registry.get_metadata("pytest-helper")

    assert meta is not None
    assert "testing" in meta.tags


def test_skill_loader_resolves_required_manual_and_triggered_skills(tmp_path: Path):
    _create_skill(
        tmp_path,
        "test-driven-development",
        description="TDD workflow",
        tags=["testing", "tdd"],
        body="Always write tests before implementation.",
        extra={"triggers": [{"type": "keyword", "pattern": "pytest", "confidence": 0.9}]},
    )
    _create_skill(
        tmp_path,
        "codebase-inspection",
        description="Inspect codebase structure",
        tags=["codebase", "analysis"],
        body="Inspect files and summarize architecture.",
    )
    _create_skill(
        tmp_path,
        "frontend-design",
        description="Frontend visual design",
        tags=["frontend", "design"],
    )
    _create_skill(
        tmp_path,
        "dangerous-deploy",
        description="Deploy production services",
        tags=["deploy"],
    )
    assignment_path = tmp_path / "agent-skill-map.yaml"
    assignment_path.write_text(
        yaml.safe_dump(
            {
                "version": 1,
                "assignments": {
                    "Tester": {
                        "add": [
                            {"skill": "codebase-inspection", "priority": "required", "reason": "Repo map is required"},
                            {"skill": "dangerous-deploy", "priority": "required", "reason": "Should be denied"},
                        ]
                    }
                },
                "blocked_skills": [],
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    registry = SkillRegistry(skills_dirs=[str(tmp_path)])
    loader = SkillLoader(skill_registry=registry, assignment_path=str(assignment_path), max_full_skills=5)
    agent = {
        "id": "Tester",
        "base_skills": {
            "required": ["test-driven-development"],
            "optional": ["frontend-design"],
        },
        "dynamic_skill_policy": {
            "allowed_tags": ["testing", "tdd", "codebase", "analysis"],
            "denied_tags": ["deploy"],
        },
    }

    result = loader.resolve(
        agent_id="Tester",
        agent=agent,
        state={
            "task": "Add pytest coverage for the runtime",
            "current_phase": "tdd",
            "files_in_scope": ["tests/test_runtime.py"],
            "run_id": "run_123",
        },
    )

    assert result.skill_names == ["test-driven-development", "codebase-inspection"]
    assert "frontend-design" not in result.skill_names
    assert "dangerous-deploy" not in result.skill_names
    assert result.skipped["dangerous-deploy"] == "denied_by_agent_policy"
    assert "--- Skill: test-driven-development" in result.context
    assert "Always write tests before implementation" in result.context
    assert result.events[0]["type"] == "skill_loaded"
    assert result.events[0]["agent"] == "Tester"
    assert result.events[0]["run_id"] == "run_123"
    assert result.events[0]["mode"] == "full"
    assert result.events[0]["fingerprint"].startswith("sha256:")


def test_skill_loader_respects_allowed_agents_for_shared_repertoire(tmp_path: Path):
    _create_skill(
        tmp_path,
        "shared-docs",
        description="Documentation writing patterns",
        tags=["documentation", "writing"],
        body="Write clear docs.",
        extra={
            "allowed_agents": ["Tester", "TechnicalWriter"],
            "triggers": [{"type": "keyword", "pattern": "docs", "confidence": 0.8}],
        },
    )
    registry = SkillRegistry(skills_dirs=[str(tmp_path)])
    loader = SkillLoader(skill_registry=registry, max_full_skills=3)
    allowed_agent = {
        "id": "TechnicalWriter",
        "base_skills": {"required": [], "optional": []},
        "dynamic_skill_policy": {"allowed_tags": ["documentation", "writing"], "denied_tags": []},
    }
    blocked_agent = {
        "id": "BackendImplementer",
        "base_skills": {"required": [], "optional": []},
        "dynamic_skill_policy": {"allowed_tags": ["documentation", "writing"], "denied_tags": []},
    }

    allowed = loader.resolve("TechnicalWriter", allowed_agent, {"task": "Generate docs for the API"})
    blocked = loader.resolve("BackendImplementer", blocked_agent, {"task": "Generate docs for the API"})

    assert allowed.skill_names == ["shared-docs"]
    assert blocked.skill_names == []
    assert blocked.skipped["shared-docs"] == "not_allowed_for_agent"


def test_state_store_appends_skill_load_events(tmp_path: Path):
    store = StateStore("demo-project", root_dir=str(tmp_path / "runtime"))
    store.append_skill_events([
        {
            "type": "skill_loaded",
            "run_id": "run_123",
            "agent": "Tester",
            "skill": "test-driven-development",
            "mode": "full",
            "reason": "base_required",
            "trust": "builtin",
            "fingerprint": "sha256:abc",
        }
    ])

    log_path = tmp_path / "runtime" / "state" / "skill-load-events.jsonl"
    assert log_path.exists()
    line = json.loads(log_path.read_text(encoding="utf-8").strip())
    assert line["skill"] == "test-driven-development"
    snapshot = store.snapshot()
    assert snapshot["skill_events_count"] == 1
    assert snapshot["last_skill_event"]["agent"] == "Tester"
