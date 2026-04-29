"""Tests for SkillRegistry."""

import tempfile
from pathlib import Path

from synto.registry import SkillRegistry


def _create_skill(dir_path: Path, name: str, description: str = "", external: bool = False) -> Path:
    skill_dir = dir_path / name
    skill_dir.mkdir(parents=True, exist_ok=True)
    content = f"---\nname: {name}\ndescription: {description}\ntags: [test]\n---\n# {name}\n\nSkill content here."
    f = skill_dir / "SKILL.md"
    f.write_text(content)
    return f


def test_discover_skills(tmp_path: Path):
    _create_skill(tmp_path, "code-review", "Review code quality")
    _create_skill(tmp_path, "testing", "Write and run tests")

    reg = SkillRegistry(skills_dirs=[str(tmp_path)])
    reg.discover()
    assert "code-review" in reg.skill_names
    assert "testing" in reg.skill_names


def test_get_metadata(tmp_path: Path):
    _create_skill(tmp_path, "my-skill", "A test skill")

    reg = SkillRegistry(skills_dirs=[str(tmp_path)])
    meta = reg.get_metadata("my-skill")
    assert meta is not None
    assert meta.description == "A test skill"


def test_load_skill_content(tmp_path: Path):
    _create_skill(tmp_path, "full-skill", "Full content test")

    reg = SkillRegistry(skills_dirs=[str(tmp_path)])
    content = reg.load_skill("full-skill")
    assert content is not None
    assert "Skill content here" in content


def test_load_nonexistent_skill(tmp_path: Path):
    reg = SkillRegistry(skills_dirs=[str(tmp_path)])
    assert reg.load_skill("does-not-exist") is None


def test_quarantine_external(tmp_path: Path):
    internal = tmp_path / "internal"
    external = tmp_path / "external"
    internal.mkdir()
    external.mkdir()

    _create_skill(internal, "internal-skill", "Internal")
    _create_skill(external, "external-skill", "External")

    reg = SkillRegistry(skills_dirs=[str(internal)])
    reg.add_external_dir(str(external))
    reg.discover()

    assert reg.is_quarantined("external-skill")
    assert not reg.is_quarantined("internal-skill")


def test_skill_metadata_to_dict(tmp_path: Path):
    _create_skill(tmp_path, "dict-skill", "Dict test")

    reg = SkillRegistry(skills_dirs=[str(tmp_path)])
    meta = reg.get_metadata("dict-skill")
    d = meta.to_dict()
    assert d["name"] == "dict-skill"
    assert d["description"] == "Dict test"


def test_empty_directory(tmp_path: Path):
    reg = SkillRegistry(skills_dirs=[str(tmp_path)])
    reg.discover()
    assert reg.skill_names == []


def test_nonexistent_directory():
    reg = SkillRegistry(skills_dirs=["/nonexistent/path"])
    reg.discover()  # Should not raise
    assert reg.skill_names == []
