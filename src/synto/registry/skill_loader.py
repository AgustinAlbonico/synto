"""Dynamic skill loading and injection for Synto agents."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
import hashlib
from pathlib import Path
import re
from typing import Any

import yaml

from synto.memory.redaction import redact_secrets
from synto.registry.skill_registry import SkillMetadata, SkillRegistry


_PRIORITY = {
    "base_required": 100,
    "manual_required": 90,
    "phase_required": 80,
    "trigger": 60,
    "manual_preferred": 55,
    "base_optional": 30,
    "manual_optional": 25,
}

_MANUAL_PRIORITY_REASON = {
    "required": "manual_required",
    "preferred": "manual_preferred",
    "optional": "manual_optional",
}


@dataclass(slots=True)
class SkillDoc:
    """A full skill document selected for a single agent invocation."""

    name: str
    content: str
    mode: str
    reason: str
    priority: int
    trust: str
    metadata: dict[str, Any] = field(default_factory=dict)
    token_estimate: int = 0
    fingerprint: str = ""


@dataclass(slots=True)
class SkillLoadResult:
    """Result of resolving skills for an agent invocation."""

    docs: list[SkillDoc] = field(default_factory=list)
    events: list[dict[str, Any]] = field(default_factory=list)
    skipped: dict[str, str] = field(default_factory=dict)

    @property
    def skill_names(self) -> list[str]:
        return [doc.name for doc in self.docs]

    @property
    def context(self) -> str:
        sections: list[str] = []
        for doc in self.docs:
            sections.append(
                f"--- Skill: {doc.name} | reason: {doc.reason} | trust: {doc.trust} ---\n"
                f"{doc.content.strip()}"
            )
        return "\n\n".join(sections)


@dataclass(slots=True)
class _Candidate:
    name: str
    reason: str
    priority: int
    source_detail: str = ""
    order: int = 0


class SkillLoader:
    """Resolve the smallest useful skill set for one agent invocation.

    The loader combines:
    - agent base skills from AGENT-REGISTRY.yaml;
    - manual assignments from config/agent-skill-map.yaml;
    - trigger matches against the current task/phase/files;
    - per-agent allow/deny policies and skill-level allowed_agents;
    - a small budget so agents never load the whole repertoire.
    """

    def __init__(
        self,
        skill_registry: SkillRegistry,
        *,
        assignment_path: str = "",
        max_full_skills: int = 5,
        max_skill_tokens: int = 20_000,
        max_single_skill_tokens: int = 8_000,
    ):
        self.skill_registry = skill_registry
        self.assignment_path = Path(assignment_path).expanduser() if assignment_path else None
        self.max_full_skills = max(1, int(max_full_skills))
        self.max_skill_tokens = max(1, int(max_skill_tokens))
        self.max_single_skill_tokens = max(1, int(max_single_skill_tokens))
        self._assignment_cache: dict[str, Any] | None = None

    def resolve(
        self,
        agent_id: str,
        agent: dict[str, Any],
        state: dict[str, Any] | None = None,
        *,
        task: str = "",
        files_in_scope: list[str] | None = None,
    ) -> SkillLoadResult:
        state = dict(state or {})
        effective_task = "\n".join(
            part for part in [str(state.get("task", "") or ""), task] if part
        )
        phase = str(state.get("current_phase") or state.get("phase") or "")
        files = files_in_scope or state.get("files_in_scope") or state.get("files") or []
        if not isinstance(files, list):
            files = [str(files)]

        candidates = self._build_candidates(agent_id, agent, effective_task, phase, files)
        result = SkillLoadResult()
        total_tokens = 0
        loaded_count = 0

        for candidate in candidates:
            meta = self.skill_registry.get_metadata(candidate.name)
            if meta is None:
                result.skipped.setdefault(candidate.name, "missing")
                continue

            block_reason = self._blocked_reason(agent_id, meta, candidate, agent)
            if block_reason:
                result.skipped.setdefault(candidate.name, block_reason)
                continue

            content = self.skill_registry.load_skill(candidate.name)
            if not content:
                result.skipped.setdefault(candidate.name, "missing_content")
                continue
            content = redact_secrets(content)
            token_estimate = self._estimate_tokens(content)
            if token_estimate > self.max_single_skill_tokens:
                result.skipped.setdefault(candidate.name, "single_skill_budget_exceeded")
                continue
            if loaded_count >= self.max_full_skills or total_tokens + token_estimate > self.max_skill_tokens:
                result.skipped.setdefault(candidate.name, "budget_exceeded")
                continue

            fingerprint = "sha256:" + hashlib.sha256(content.encode("utf-8")).hexdigest()
            trust = self._trust_for(meta)
            doc = SkillDoc(
                name=candidate.name,
                content=content,
                mode="full",
                reason=candidate.reason,
                priority=candidate.priority,
                trust=trust,
                metadata=meta.to_dict(),
                token_estimate=token_estimate,
                fingerprint=fingerprint,
            )
            result.docs.append(doc)
            result.events.append(
                {
                    "type": "skill_loaded",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "run_id": str(state.get("run_id", "") or ""),
                    "thread_id": str(state.get("thread_id", "") or ""),
                    "agent": agent_id,
                    "skill": candidate.name,
                    "mode": doc.mode,
                    "reason": candidate.reason,
                    "source_detail": candidate.source_detail,
                    "priority": candidate.priority,
                    "trust": trust,
                    "tags": list(meta.tags),
                    "fingerprint": fingerprint,
                }
            )
            total_tokens += token_estimate
            loaded_count += 1

        return result

    def _build_candidates(
        self,
        agent_id: str,
        agent: dict[str, Any],
        task: str,
        phase: str,
        files: list[str],
    ) -> list[_Candidate]:
        seen: dict[str, _Candidate] = {}
        order = 0

        def add(name: str, reason: str, source_detail: str = "") -> None:
            nonlocal order
            if not name:
                return
            candidate = _Candidate(
                name=str(name),
                reason=reason,
                priority=_PRIORITY.get(reason, _PRIORITY.get(reason.split(":", 1)[0], 10)),
                source_detail=source_detail,
                order=order,
            )
            order += 1
            existing = seen.get(candidate.name)
            if existing is None or candidate.priority > existing.priority:
                seen[candidate.name] = candidate

        base = agent.get("base_skills", {}) or {}
        if isinstance(base, dict):
            for name in base.get("required", []) or []:
                add(name, "base_required")
            for name in base.get("optional", []) or []:
                add(name, "base_optional")

        assignments = self._assignments_for(agent_id)
        for removed in assignments.get("remove", []) or []:
            seen.pop(str(removed), None)
        for item in assignments.get("add", []) or []:
            if isinstance(item, str):
                add(item, "manual_required")
                continue
            if not isinstance(item, dict):
                continue
            priority = str(item.get("priority", "required") or "required")
            reason = _MANUAL_PRIORITY_REASON.get(priority, "manual_required")
            add(str(item.get("skill", "") or ""), reason, str(item.get("reason", "") or ""))

        # Dynamic repertoire: only add skills that match an explicit or inferred trigger.
        for meta in self.skill_registry.get_all_metadata().values():
            if meta.name in seen:
                continue
            detail = self._trigger_detail(meta, task, phase, files)
            if detail:
                add(meta.name, "trigger", detail)

        return sorted(seen.values(), key=lambda item: (-item.priority, item.order, item.name))

    def _blocked_reason(
        self,
        agent_id: str,
        meta: SkillMetadata,
        candidate: _Candidate,
        agent: dict[str, Any],
    ) -> str:
        if meta.name in self._blocked_skills():
            return "blocked"
        if self.skill_registry.is_quarantined(meta.name):
            return "quarantined"

        allowed_agents = list(meta.allowed_agents or [])
        if allowed_agents and agent_id not in allowed_agents:
            return "not_allowed_for_agent"

        policy = agent.get("dynamic_skill_policy", {}) or {}
        allowed_tags = {str(tag).lower() for tag in policy.get("allowed_tags", []) or []}
        denied_tags = {str(tag).lower() for tag in policy.get("denied_tags", []) or []}
        tags = {str(tag).lower() for tag in meta.tags or []}
        if denied_tags and tags.intersection(denied_tags):
            return "denied_by_agent_policy"

        assigned_or_required = candidate.reason in {"base_required", "manual_required", "manual_preferred"}
        if allowed_tags and tags and not tags.intersection(allowed_tags) and not assigned_or_required:
            return "not_allowed_by_agent_policy"

        return ""

    def _trigger_detail(self, meta: SkillMetadata, task: str, phase: str, files: list[str]) -> str:
        haystack = "\n".join([task, phase, "\n".join(str(f) for f in files)]).lower()
        for trigger in meta.triggers or []:
            if not isinstance(trigger, dict):
                continue
            trigger_type = str(trigger.get("type", "keyword") or "keyword")
            pattern = str(trigger.get("pattern", "") or "")
            if not pattern:
                continue
            if trigger_type == "keyword" and pattern.lower() in haystack:
                return f"keyword:{pattern}"
            if trigger_type == "phase" and pattern.lower() == phase.lower():
                return f"phase:{pattern}"
            if trigger_type == "file_glob" and self._file_glob_matches(pattern, files):
                return f"file_glob:{pattern}"
            if trigger_type == "regex":
                try:
                    if re.search(pattern, haystack, flags=re.IGNORECASE):
                        return f"regex:{pattern}"
                except re.error:
                    continue

        # Inferred trigger: require a reasonably specific skill token/tag in the task.
        tokens = self._skill_tokens(meta)
        for token in tokens:
            if token in haystack:
                return f"inferred:{token}"
        return ""

    def _skill_tokens(self, meta: SkillMetadata) -> list[str]:
        raw = " ".join([meta.name, meta.description, " ".join(meta.tags)])
        tokens = []
        for token in re.split(r"[^a-zA-Z0-9_+-]+", raw.lower()):
            if len(token) >= 4 and token not in {"skill", "with", "from", "using", "agent"}:
                tokens.append(token)
        return list(dict.fromkeys(tokens))

    def _file_glob_matches(self, pattern: str, files: list[str]) -> bool:
        from fnmatch import fnmatch

        return any(fnmatch(str(path), pattern) for path in files)

    def _assignments_for(self, agent_id: str) -> dict[str, Any]:
        assignments = self._assignment_config().get("assignments", {}) or {}
        value = assignments.get(agent_id, {})
        return value if isinstance(value, dict) else {}

    def _blocked_skills(self) -> set[str]:
        return {str(item) for item in self._assignment_config().get("blocked_skills", []) or []}

    def _assignment_config(self) -> dict[str, Any]:
        if self._assignment_cache is not None:
            return self._assignment_cache
        if not self.assignment_path or not self.assignment_path.exists():
            self._assignment_cache = {}
            return self._assignment_cache
        try:
            parsed = yaml.safe_load(self.assignment_path.read_text(encoding="utf-8")) or {}
            self._assignment_cache = parsed if isinstance(parsed, dict) else {}
        except Exception:
            self._assignment_cache = {}
        return self._assignment_cache

    def _trust_for(self, meta: SkillMetadata) -> str:
        override = (self._assignment_config().get("skill_overrides", {}) or {}).get(meta.name, {})
        if isinstance(override, dict) and override.get("trust"):
            return str(override["trust"])
        return meta.trust or "builtin"

    def _estimate_tokens(self, content: str) -> int:
        return max(1, len(content) // 4)
