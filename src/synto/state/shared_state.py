"""SharedState / Blackboard — shared context across agents in a LangGraph run."""

from dataclasses import dataclass, field
from typing import Any, Optional
from datetime import datetime


@dataclass
class BlackboardEntry:
    """A single entry on the shared blackboard."""
    key: str
    value: Any
    source_agent: str = ""
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    ttl: Optional[int] = None  # seconds, None = no expiry


class SharedState:
    """Simple key-value blackboard for agent communication.

    Agents read/write to this state during LangGraph execution.
    Supports scoped keys (e.g. "planning:prd", "impl:code_review").
    """

    def __init__(self):
        self._store: dict[str, BlackboardEntry] = {}

    def put(self, key: str, value: Any, source_agent: str = "", ttl: Optional[int] = None) -> None:
        self._store[key] = BlackboardEntry(
            key=key, value=value, source_agent=source_agent, ttl=ttl
        )

    def get(self, key: str, default: Any = None) -> Any:
        entry = self._store.get(key)
        if entry is None:
            return default
        return entry.value

    def delete(self, key: str) -> None:
        self._store.pop(key, None)

    def keys(self, prefix: str = "") -> list[str]:
        if prefix:
            return [k for k in self._store if k.startswith(prefix)]
        return list(self._store.keys())

    def clear(self) -> None:
        self._store.clear()

    def snapshot(self) -> dict[str, Any]:
        """Return a serializable snapshot of the board."""
        return {k: v.value for k, v in self._store.items()}

    def merge(self, other: dict[str, Any], source_agent: str = "") -> None:
        for k, v in other.items():
            self.put(k, v, source_agent=source_agent)

    def size(self) -> int:
        return len(self._store)

    def __repr__(self) -> str:
        return f"SharedState(keys={list(self._store.keys())})"
