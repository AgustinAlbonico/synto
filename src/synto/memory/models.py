"""Pydantic models for the memory system."""

from __future__ import annotations

import json
import re
import time
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional
from uuid import uuid4

from pydantic import BaseModel, Field, field_validator


class MemoryKind(str, Enum):
    """Types of memory items."""
    DECISION = "decision"
    PROBLEM = "problem"
    SOLUTION = "solution"
    CONTEXT = "context"
    PREFERENCE = "preference"
    FACT = "fact"
    PATTERN = "pattern"
    CONFIG = "config"
    NOTE = "note"


class MemoryStatus(str, Enum):
    """Lifecycle status of a memory item."""
    ACTIVE = "active"
    ARCHIVED = "archived"
    CONFLICTED = "conflicted"
    DEPRECATED = "deprecated"


class MemoryItem(BaseModel):
    """Core memory item model."""
    id: str = Field(default_factory=lambda: uuid4().hex[:12])
    project_id: str = Field(..., min_length=1)
    feature_id: str = ""
    topic_id: str = ""
    kind: MemoryKind = MemoryKind.NOTE
    status: MemoryStatus = MemoryStatus.ACTIVE
    title: str = ""
    content: str = Field(..., min_length=1)
    tags: list[str] = Field(default_factory=list)
    importance: float = Field(default=0.5, ge=0.0, le=1.0)
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: float = Field(default_factory=time.time)
    updated_at: float = Field(default_factory=time.time)

    @field_validator("content")
    @classmethod
    def content_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("content cannot be empty")
        return v

    @property
    def created_iso(self) -> str:
        return datetime.fromtimestamp(self.created_at, tz=timezone.utc).isoformat()

    @property
    def updated_iso(self) -> str:
        return datetime.fromtimestamp(self.updated_at, tz=timezone.utc).isoformat()

    def word_count(self) -> int:
        return len(self.content.split())

    def to_db_row(self) -> dict:
        return {
            "id": self.id,
            "project_id": self.project_id,
            "feature_id": self.feature_id or None,
            "topic_id": self.topic_id or None,
            "kind": self.kind.value,
            "status": self.status.value,
            "title": self.title,
            "content": self.content,
            "tags": json.dumps(self.tags),
            "importance": self.importance,
            "confidence": self.confidence,
            "metadata": json.dumps(self.metadata),
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_db_row(cls, row: dict) -> "MemoryItem":
        return cls(
            id=row["id"],
            project_id=row["project_id"],
            feature_id=row.get("feature_id") or "",
            topic_id=row.get("topic_id") or "",
            kind=MemoryKind(row.get("kind", "note")),
            status=MemoryStatus(row.get("status", "active")),
            title=row.get("title", ""),
            content=row["content"],
            tags=json.loads(row["tags"]) if row.get("tags") else [],
            importance=row.get("importance", 0.5),
            confidence=row.get("confidence", 0.5),
            metadata=json.loads(row["metadata"]) if row.get("metadata") else {},
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )


class MemoryCandidate(BaseModel):
    """Proposed memory item pending review."""
    id: str = Field(default_factory=lambda: uuid4().hex[:12])
    source_agent: str = ""
    kind: MemoryKind = MemoryKind.NOTE
    title: str = ""
    content: str = Field(..., min_length=1)
    project_id: str = ""
    feature_id: str = ""
    topic_id: str = ""
    tags: list[str] = Field(default_factory=list)
    reasoning: str = ""
    created_at: float = Field(default_factory=time.time)

    def to_memory_item(self, project_id: str = "") -> MemoryItem:
        return MemoryItem(
            project_id=project_id or self.project_id,
            feature_id=self.feature_id,
            topic_id=self.topic_id,
            kind=self.kind,
            title=self.title,
            content=self.content,
            tags=self.tags,
            metadata={"source_agent": self.source_agent, "candidate_id": self.id},
        )


class MemoryLink(BaseModel):
    """Relationship between two memory items."""
    id: str = Field(default_factory=lambda: uuid4().hex[:12])
    source_id: str
    target_id: str
    link_type: str = "related"
    strength: float = Field(default=0.5, ge=0.0, le=1.0)

    @field_validator("source_id", "target_id")
    @classmethod
    def ids_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("ID cannot be empty")
        return v


class MemoryPackItem(BaseModel):
    """A single item inside a MemoryPack."""
    id: str
    title: str
    snippet: str  # truncated content
    source: str  # project/feature/topic path
    importance: float
    link_back: Optional[str] = None  # why this was included


class MemoryPack(BaseModel):
    """Bounded context package for an agent."""
    agent_id: str
    task_summary: str = ""
    items: list[MemoryPackItem] = Field(default_factory=list)
    total_tokens_estimate: int = 0
    token_budget: int = 4000

    def add_item(self, item: MemoryPackItem) -> bool:
        estimated = len(item.snippet) // 4  # rough char-to-token ratio
        if self.total_tokens_estimate + estimated > self.token_budget:
            return False
        self.items.append(item)
        self.total_tokens_estimate += estimated
        return True


class TaskContext(BaseModel):
    """Context for a task/run."""
    task: str
    project_id: str
    agent_ids: list[str] = Field(default_factory=list)
    feature_id: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)


class MemorySearchResult(BaseModel):
    """Result of a memory search."""
    item: MemoryItem
    score: float
    matched_fields: list[str] = Field(default_factory=list)


class MemoryAuditEntry(BaseModel):
    """Audit log entry."""
    timestamp: float = Field(default_factory=time.time)
    action: str  # "add", "update", "delete", "commit", "reject", "link"
    actor: str  # agent name or "human"
    target_id: str = ""
    details: str = ""
