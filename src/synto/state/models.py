"""Structured state models for workflow persistence and UI consumption."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Literal


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class WorkflowState:
    current_phase: str = ""
    completed_phases: list[str] = field(default_factory=list)
    pending_phases: list[str] = field(default_factory=list)
    retry_counts: dict[str, int] = field(default_factory=dict)
    max_retries: int = 3
    execution_mode: Literal["automatic", "interactive"] = "automatic"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class Approval:
    approval_id: str
    gate: str
    status: Literal["pending", "approved", "rejected", "changes_requested"]
    requested_by: str
    requested_at: str = field(default_factory=utc_now)
    answered_at: str | None = None
    user_response: str | None = None
    artifact_versions: dict[str, int] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class GateStatus:
    gate_id: str
    status: Literal["not_started", "pending", "passed", "failed", "blocked"]
    checked_by: str
    checked_at: str | None = None
    required_artifacts: list[str] = field(default_factory=list)
    blocking_issues: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class Artifact:
    artifact_id: str
    kind: str
    path: str
    version: int
    created_by: str
    created_at: str = field(default_factory=utc_now)
    updated_at: str = field(default_factory=utc_now)
    status: Literal["draft", "approved", "superseded", "rejected"] = "draft"
    summary: str = ""
    content_hash: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class AgentSlot:
    owner: str
    status: Literal["empty", "working", "done", "failed", "needs_input"] = "done"
    updated_at: str = field(default_factory=utc_now)
    summary: str | None = None
    data: dict[str, Any] = field(default_factory=dict)
    produced_artifacts: list[str] = field(default_factory=list)
    issues: list[str] = field(default_factory=list)
    next_actions: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
