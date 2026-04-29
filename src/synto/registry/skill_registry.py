"""SkillRegistry — discovers and manages available skills."""

import json
from pathlib import Path
from typing import Any, Optional


class SkillMetadata:
    """Lightweight skill metadata (always available)."""

    def __init__(self, name: str, description: str = "", path: str = "", tags: list[str] | None = None):
        self.name = name
        self.description = description
        self.path = path
        self.tags = tags or []

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "description": self.description,
            "path": self.path,
            "tags": self.tags,
        }


class SkillRegistry:
    """Discovers skills from directories without loading full content.
    
    Rules:
    - Metadata always available
    - Full skill content lazy-loaded on demand
    - External skills in quarantine
    - Never load all skills to all agents
    """

    def __init__(self, skills_dirs: list[str] | None = None):
        self.skills_dirs = skills_dirs or []
        self._metadata: dict[str, SkillMetadata] = {}
        self._quarantine: set[str] = set()
        self._discovered = False

    def discover(self) -> None:
        """Scan directories for SKILL.md files."""
        for dir_path in self.skills_dirs:
            p = Path(dir_path)
            if not p.exists():
                continue
            self._scan_directory(p, external=False)

        self._discovered = True

    def _scan_directory(self, parent: Path, external: bool) -> None:
        """Recursively scan for SKILL.md files."""
        for child in parent.iterdir():
            if child.is_dir():
                if child.name.startswith(".") or child.name == "node_modules":
                    continue
                skill_file = child / "SKILL.md"
                if skill_file.exists():
                    meta = self._extract_metadata(skill_file)
                    if external:
                        self._quarantine.add(meta.name)
                    self._metadata[meta.name] = meta
                self._scan_directory(child, external=external)

    def _extract_metadata(self, skill_path: Path) -> SkillMetadata:
        """Extract metadata from SKILL.md frontmatter."""
        content = skill_path.read_text()
        name = skill_path.parent.name
        description = ""
        tags = []

        # Try to parse YAML frontmatter
        if content.startswith("---"):
            parts = content.split("---", 2)
            if len(parts) >= 3:
                import yaml
                try:
                    frontmatter = yaml.safe_load(parts[1])
                    if frontmatter:
                        name = frontmatter.get("name", name)
                        description = frontmatter.get("description", description)
                        tags = frontmatter.get("tags", tags)
                except Exception:
                    pass

        return SkillMetadata(
            name=name,
            description=description,
            path=str(skill_path),
            tags=tags,
        )

    def get_metadata(self, skill_name: str) -> Optional[SkillMetadata]:
        """Get metadata for a skill (always available)."""
        if not self._discovered:
            self.discover()
        return self._metadata.get(skill_name)

    def get_all_metadata(self) -> dict[str, SkillMetadata]:
        """Get metadata for all skills."""
        if not self._discovered:
            self.discover()
        return dict(self._metadata)

    def load_skill(self, skill_name: str) -> Optional[str]:
        """Load full skill content (lazy, on-demand)."""
        meta = self.get_metadata(skill_name)
        if not meta:
            return None
        try:
            return Path(meta.path).read_text()
        except Exception:
            return None

    def is_quarantined(self, skill_name: str) -> bool:
        """Check if a skill is in quarantine (external/untrusted)."""
        return skill_name in self._quarantine

    def list_quarantined(self) -> list[str]:
        return list(self._quarantine)

    def add_external_dir(self, dir_path: str) -> None:
        """Add an external skills directory (will be quarantined)."""
        p = Path(dir_path)
        if p.exists():
            self._scan_directory(p, external=True)

    @property
    def skill_names(self) -> list[str]:
        if not self._discovered:
            self.discover()
        return list(self._metadata.keys())
