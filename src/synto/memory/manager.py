"""MemoryManager — consolidates candidates and manages memory lifecycle."""

import time

from synto.memory.models import (
    MemoryCandidate, MemoryItem, MemoryAuditEntry,
)
from synto.memory.store import MemoryStore
from synto.memory.redaction import redact_secrets, contains_secrets


class MemoryManager:
    """Manages memory lifecycle: candidates -> review -> commit/reject.
    
    Rules:
    - Always redact before saving
    - Basic deduplication
    - Audit log for all actions
    - Never auto-commit insecure content
    """

    def __init__(self, store: MemoryStore):
        self.store = store

    def add_candidate(self, candidate: MemoryCandidate) -> str:
        """Add a memory candidate for review."""
        candidate.content = redact_secrets(candidate.content)
        candidate.title = redact_secrets(candidate.title)
        return self.store.add_candidate(candidate)

    def commit_candidate(self, candidate_id: str, actor: str = "system") -> str:
        """Commit a candidate to permanent memory.
        
        Returns the new MemoryItem id.
        """
        return self.store.commit_candidate(candidate_id, actor=actor)

    def reject_candidate(self, candidate_id: str, reason: str = "", actor: str = "system") -> None:
        """Reject and discard a candidate."""
        self.store.reject_candidate(candidate_id, reason=reason, actor=actor)

    def list_candidates(self, project_id: str = "") -> list[dict]:
        """List all pending candidates."""
        return self.store.list_candidates(project_id=project_id)

    def auto_commit_safe(self, candidate_id: str, actor: str = "system") -> str | None:
        """Auto-commit if content passes security checks.
        
        Returns item_id if committed, None if rejected.
        """
        candidates = self.store.list_candidates()
        target = None
        for c in candidates:
            if c["id"] == candidate_id:
                target = c
                break

        if not target:
            return None

        # Security check first (before redaction, to catch real secrets)
        # If already redacted (contains [REDACTED]), it's safe to commit
        content = target.get("content", "")
        if "[REDACTED]" in content:
            # Parse JSON fields from DB
            import json as _json
            data = dict(target)
            for field in ("tags",):
                if isinstance(data.get(field), str):
                    try:
                        data[field] = _json.loads(data[field])
                    except Exception:
                        data[field] = []
            candidate = MemoryCandidate.model_validate(data)
            item = MemoryItem(
                project_id=candidate.project_id,
                feature_id=candidate.feature_id or "",
                topic_id=candidate.topic_id or "",
                kind=candidate.kind,
                title=candidate.title,
                content=candidate.content,
                tags=candidate.tags,
                metadata={"from_candidate": candidate.id, "source_agent": candidate.source_agent},
            )
            item_id = self.store.add_memory_item(item)
            self.store._audit("auto_commit_safe", "system", candidate_id, "committed (redacted)")
            return item_id
        
        # Security check
        if contains_secrets(content):
            self.reject_candidate(candidate_id, reason="contains_secrets", actor=actor)
            return None

        # Basic dedup: check if similar content already exists
        project_id = target.get("project_id", "")
        if project_id:
            existing = self.store.list_by_project(project_id)
            content_lower = target.get("content", "").lower()[:100]
            for item in existing:
                if content_lower and content_lower in item.content.lower()[:100]:
                    # Similar content exists, reject as duplicate
                    self.reject_candidate(candidate_id, reason="duplicate", actor=actor)
                    return None

        return self.commit_candidate(candidate_id, actor=actor)

    def consolidate_run(
        self,
        candidates: list[MemoryCandidate],
        actor: str = "system",
    ) -> dict:
        """Process all candidates from a run.
        
        Returns summary of actions taken.
        """
        committed = 0
        rejected = 0
        item_ids = []

        for candidate in candidates:
            # First add the candidate
            cid = self.add_candidate(candidate)
            # Then try auto-commit
            result = self.auto_commit_safe(cid, actor=actor)
            if result:
                committed += 1
                item_ids.append(result)
            else:
                rejected += 1

        return {
            "committed": committed,
            "rejected": rejected,
            "item_ids": item_ids,
        }

    def get_audit_log(self, limit: int = 50) -> list[dict]:
        """Get recent audit entries."""
        return self.store.get_audit_log(limit=limit)
