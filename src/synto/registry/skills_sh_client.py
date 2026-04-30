"""Skills marketplace client — searches skills from the open skills.sh ecosystem.

Strategy: query GitHub directly for repositories containing SKILL.md files
that match the agent-skills / skills.sh naming conventions.

This avoids depending on a hosted API service.
"""

from __future__ import annotations

import os
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import httpx


@dataclass
class RemoteSkill:
    """A skill discovered from the GitHub-backed skills registry."""

    id: str
    name: str
    description: str
    owner: str
    repo: str
    source: str = "github"
    tags: list[str] = field(default_factory=list)
    path: str = "SKILL.md"  # path within the repo
    content: str | None = None
    stargazers: int = 0

    @property
    def skill_id(self) -> str:
        return f"{self.owner}/{self.repo}/{self.id}"

    @property
    def github_url(self) -> str:
        return f"https://github.com/{self.owner}/{self.repo}"


class SkillsClient:
    """Search and fetch skills from the skills.sh ecosystem via GitHub.

    Searches GitHub for repositories following the skills.sh convention:
    - Repository name contains "skill" or "skills"
    - Contains at least one SKILL.md file
    - Optionally filters by topic

    Usage:
        client = SkillsClient()
        results = client.search("docker deploy")
    """

    def __init__(
        self,
        token: str | None = None,
        timeout: float = 30.0,
        cache_dir: str | None = None,
        cache_ttl: int = 300,
    ):
        self.token = token or os.environ.get("GITHUB_TOKEN", "")
        self.timeout = timeout
        self.cache_dir = Path(cache_dir) if cache_dir else Path.home() / ".cache" / "synto" / "skills-market"
        self.cache_ttl = cache_ttl
        self._client = httpx.Client(timeout=timeout)
        self._cache_dir = self.cache_dir
        self._cache_dir.mkdir(parents=True, exist_ok=True)

    # ── Public API ───────────────────────────────────────────────────────────

    def search(
        self,
        query: str = "",
        *,
        language: str | None = None,
        limit: int = 10,
    ) -> list[RemoteSkill]:
        """Search skills via GitHub code search for SKILL.md files.

        Uses GitHub's search API to find repositories with SKILL.md files
        matching the query, sorted by stars.
        """
        if not query:
            query = "SKILL.md agent skill"
        else:
            query = f"{query} SKILL.md agent skill"

        params: dict[str, Any] = {
            "q": query,
            "sort": "stars",
            "order": "desc",
            "per_page": min(limit, 30),
            "type": "repositories",
        }
        if language:
            params["q"] += f" language:{language}"

        data = self._github_get("/search/repositories", params)
        items = data.get("items", [])
        results = []
        for item in items:
            # Extract skill name from repo
            name = item.get("name", "")
            owner = item.get("owner", {}).get("login", "")
            description = item.get("description", "") or ""
            topics = item.get("topics", []) or []
            stars = item.get("stargazers_count", 0) or 0

            # Build skill ID — use repo name as disambiguation
            skill_id = f"{owner}/{name}/sk"

            results.append(
                RemoteSkill(
                    id=name,
                    name=name.replace("-", " ").replace("_", " "),
                    description=description,
                    owner=owner,
                    repo=name,
                    tags=topics[:10],
                    stargazers=stars,
                )
            )

        return results

    def get_content(self, skill_id: str) -> str | None:
        """Fetch the SKILL.md content for a given skill."""
        # skill_id: "owner/repo/skillId" — skillId is often the repo name or a sub-path
        parts = skill_id.split("/", 2)
        if len(parts) < 2:
            return None
        owner, repo = parts[0], parts[1]

        # Try SKILL.md at repo root first
        for filename in ["SKILL.md", "skill.md", "README.md"]:
            content = self._fetch_file_content(owner, repo, filename)
            if content:
                return content
        return None

    def install_to(
        self,
        skill_id: str,
        target_dir: str | Path,
        *,
        force: bool = False,
    ) -> dict[str, Any]:
        """Download a skill's SKILL.md to a local skills directory."""
        target = Path(target_dir)
        content = self.get_content(skill_id)
        if content is None:
            return {"status": "error", "error": f"Could not fetch: {skill_id}"}

        parts = skill_id.split("/", 2)
        owner, repo = parts[0], parts[1]
        safe_name = f"{owner}-{repo}"
        skill_dir = target / safe_name

        if skill_dir.exists() and not force:
            return {"status": "skipped", "path": str(skill_dir), "reason": "already exists"}

        skill_dir.mkdir(parents=True, exist_ok=True)
        (skill_dir / "SKILL.md").write_text(content, encoding="utf-8")

        return {
            "status": "installed",
            "path": str(skill_dir),
            "skill_id": skill_id,
            "files_installed": ["SKILL.md"],
        }

    # ── GitHub Helpers ───────────────────────────────────────────────────────

    def _github_get(self, path: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        url = f"https://api.github.com{path}"
        cache_key = self._cache_key(url, params)
        cached = self._read_cache(cache_key)
        if cached is not None:
            return cached

        headers = {
            "Accept": "application/vnd.github+json",
            "User-Agent": "synto-skills-client/1.0",
        }
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"

        time.sleep(0.5)  # Rate limit courtesy
        resp = self._client.get(url, params=params or {}, headers=headers)
        resp.raise_for_status()
        data = resp.json()
        self._write_cache(cache_key, data)
        return data

    def _fetch_file_content(self, owner: str, repo: str, path: str) -> str | None:
        url = f"https://api.github.com/repos/{owner}/{repo}/contents/{path}"
        headers = {
            "Accept": "application/vnd.github+json",
            "User-Agent": "synto-skills-client/1.0",
        }
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"

        try:
            time.sleep(0.3)
            resp = self._client.get(url, headers=headers, timeout=15)
            if resp.status_code != 200:
                return None
            import base64
            data = resp.json()
            content_b64 = data.get("content", "")
            if not content_b64:
                return None
            # Remove newlines in base64 string
            content_b64 = content_b64.replace("\n", "")
            return base64.b64decode(content_b64).decode("utf-8", errors="replace")
        except Exception:
            return None

    # ── Cache ────────────────────────────────────────────────────────────────

    def _cache_key(self, url: str, params: dict[str, Any] | None) -> str:
        import hashlib
        key = f"{url}?{httpx.QueryParams(params or {})}".encode()
        return hashlib.sha256(key).hexdigest()[:16]

    def _read_cache(self, key: str) -> dict[str, Any] | None:
        cache_file = self._cache_dir / f"{key}.json"
        if not cache_file.exists():
            return None
        try:
            import json
            age = time.time() - cache_file.stat().st_mtime
            if age > self.cache_ttl:
                return None
            return json.loads(cache_file.read_text())
        except Exception:
            return None

    def _write_cache(self, key: str, data: dict[str, Any]) -> None:
        try:
            import json
            cache_file = self._cache_dir / f"{key}.json"
            cache_file.write_text(json.dumps(data), encoding="utf-8")
        except Exception:
            pass


# ── Singleton ────────────────────────────────────────────────────────────────

_default_client: SkillsClient | None = None


def get_client() -> SkillsClient:
    global _default_client
    if _default_client is None:
        _default_client = SkillsClient()
    return _default_client
