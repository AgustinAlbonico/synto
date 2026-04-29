"""SkillRegistry — discovers and manages available skills."""

import json
from pathlib import Path
from typing import Any, Optional


class SkillMetadata:
    """Lightweight skill metadata (always available)."""

    def __init__(
        self,
        name: str,
        description: str = "",
        path: str = "",
        tags: list[str] | None = None,
        triggers: list[dict[str, Any]] | None = None,
        allowed_agents: list[str] | None = None,
        trust: str = "builtin",
    ):
        self.name = name
        self.description = description
        self.path = path
        self.tags = tags or []
        self.triggers = triggers or []
        self.allowed_agents = allowed_agents or []
        self.trust = trust or "builtin"

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "description": self.description,
            "path": self.path,
            "tags": self.tags,
            "triggers": self.triggers,
            "allowed_agents": self.allowed_agents,
            "trust": self.trust,
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
        """Extract metadata from SKILL.md frontmatter and infer useful tags."""
        content = skill_path.read_text(encoding="utf-8")
        name = skill_path.parent.name
        description = ""
        tags: list[str] = []
        triggers: list[dict[str, Any]] = []
        allowed_agents: list[str] = []
        trust = "builtin"

        # Try to parse YAML frontmatter
        if content.startswith("---"):
            parts = content.split("---", 2)
            if len(parts) >= 3:
                import yaml
                try:
                    frontmatter = yaml.safe_load(parts[1])
                    if isinstance(frontmatter, dict):
                        name = frontmatter.get("name", name)
                        description = frontmatter.get("description", description) or ""
                        tags = self._normalize_list(frontmatter.get("tags", tags))
                        triggers = self._normalize_triggers(frontmatter.get("triggers", triggers))
                        allowed_agents = self._normalize_list(frontmatter.get("allowed_agents", allowed_agents))
                        trust = str(frontmatter.get("trust", trust) or trust)
                        hermes_meta = (frontmatter.get("metadata") or {}).get("hermes", {}) if isinstance(frontmatter.get("metadata"), dict) else {}
                        if isinstance(hermes_meta, dict):
                            tags.extend(self._normalize_list(hermes_meta.get("tags", [])))
                except Exception:
                    pass

        tags = self._dedupe_tags(tags) or self._infer_tags(name, description, content)

        return SkillMetadata(
            name=name,
            description=description,
            path=str(skill_path),
            tags=tags,
            triggers=triggers,
            allowed_agents=allowed_agents,
            trust=trust,
        )

    def _normalize_list(self, value: Any) -> list[str]:
        if value is None:
            return []
        if isinstance(value, str):
            return [value]
        if isinstance(value, (list, tuple, set)):
            return [str(item) for item in value if str(item)]
        return []

    def _normalize_triggers(self, value: Any) -> list[dict[str, Any]]:
        if not isinstance(value, list):
            return []
        return [item for item in value if isinstance(item, dict)]

    def _dedupe_tags(self, tags: list[str]) -> list[str]:
        result: list[str] = []
        seen: set[str] = set()
        for tag in tags:
            clean = str(tag).strip().lower()
            if clean and clean not in seen:
                seen.add(clean)
                result.append(clean)
        return result

    def _infer_tags(self, name: str, description: str, content: str) -> list[str]:
        text = f"{name} {description} {content[:4000]}".lower()
        taxonomy = {
            "testing": ["test", "tests", "pytest", "tdd", "coverage", "qa", "e2e", "unit"],
            "frontend": ["frontend", "react", "ui", "ux", "css", "html", "component", "vite", "browser"],
            "backend": ["backend", "api", "server", "service", "fastapi", "nestjs", "database", "db"],
            "devops": ["deploy", "docker", "ci", "cd", "kubernetes", "cloudflare", "build", "release"],
            "deploy": ["deploy", "deployment", "release", "cloudflare"],
            "github": ["github", "pull request", " pr ", "git", "branch", "commit"],
            "documentation": ["docs", "documentation", "readme", "technical writer", "changelog"],
            "writing": ["write", "writing", "copy", "markdown", "document"],
            "research": ["research", "web_search", "arxiv", "paper", "literature"],
            "security": ["security", "secret", "vulnerability", "owasp", "auth", "permission"],
            "planning": ["plan", "planning", "task graph", "roadmap", "spec"],
            "memory": ["memory", "obsidian", "fact_store", "session_search"],
            "design": ["design", "diagram", "visual", "design system", "tokens"],
            "architecture": ["architecture", "architect", "adr", "system design"],
            "codebase": ["codebase", "inspect", "loc", "files", "repository"],
            "debugging": ["debug", "bug", "traceback", "root cause"],
            "review": ["review", "code review", "critique", "audit"],
            "product": ["product", "prd", "requirements", "acceptance criteria"],
        }
        inferred = [tag for tag, keywords in taxonomy.items() if any(keyword in text for keyword in keywords)]
        return self._dedupe_tags(inferred)

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
