"""Persistent workflow state store for slots, artifacts, gates, approvals, and events."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any

from synto.memory.redaction import redact_secrets
from synto.registry import AgentRegistry
from synto.state.models import Approval, AgentSlot, Artifact, GateStatus, WorkflowState, utc_now


_ARTIFACT_SECTION_DEFAULTS = {
    "run_id": "",
    "project_id": "",
    "thread_id": "",
    "memory_db_path": "",
    "registry_path": "",
    "state_root": "",
    "checkpoint_db_path": "",
    "workflow": WorkflowState().to_dict(),
    "shared_state": {},
    "memory": {},
    "phase_outputs": {},
    "slots": {},
    "artifacts": {},
    "gates": {},
    "approvals": {},
    "events_count": 0,
    "last_event": None,
    "skill_events_count": 0,
    "last_skill_event": None,
    "result": "",
    "gate_passed": False,
    "gate_errors": [],
    "last_updated_at": utc_now(),
}


def _slugify(value: str) -> str:
    value = value.strip().lower()
    value = re.sub(r"[^a-z0-9._-]+", "-", value)
    value = re.sub(r"-+", "-", value)
    return value.strip("-") or "default"


class StateStore:
    """File-backed state store for the orchestration runtime.

    Layout:
    <project_root>/
      state/current-state.json
      state/checkpoints.sqlite
      state/events.jsonl
      artifacts/
      slots/
    """

    def __init__(
        self,
        project_id: str,
        root_dir: str = "",
        registry: AgentRegistry | None = None,
        registry_path: str = "",
    ):
        self.project_id = project_id or "default"
        self.project_slug = _slugify(self.project_id)
        self.project_root = Path(root_dir).resolve() if root_dir else (
            Path.cwd() / "workspace" / ".hermes-state" / "projects" / self.project_slug
        )
        self.state_dir = self.project_root / "state"
        self.artifacts_dir = self.project_root / "artifacts"
        self.slots_dir = self.project_root / "slots"
        self.current_state_path = self.state_dir / "current-state.json"
        self.events_log_path = self.state_dir / "events.jsonl"
        self.skill_events_log_path = self.state_dir / "skill-load-events.jsonl"
        self.checkpoint_db_path = self.state_dir / "checkpoints.sqlite"

        self.state_dir.mkdir(parents=True, exist_ok=True)
        self.artifacts_dir.mkdir(parents=True, exist_ok=True)
        self.slots_dir.mkdir(parents=True, exist_ok=True)

        if registry is not None:
            self.registry = registry
        elif registry_path:
            self.registry = AgentRegistry(registry_path)
            self.registry.load()
        else:
            self.registry = None

        if not self.current_state_path.exists():
            self._write_current_state(dict(_ARTIFACT_SECTION_DEFAULTS))

    def _read_current_state(self) -> dict[str, Any]:
        if not self.current_state_path.exists():
            return dict(_ARTIFACT_SECTION_DEFAULTS)
        return json.loads(self.current_state_path.read_text())

    def _write_current_state(self, payload: dict[str, Any]) -> None:
        clean = self._redact(payload)
        clean["last_updated_at"] = utc_now()
        self.current_state_path.write_text(json.dumps(clean, indent=2, ensure_ascii=False, sort_keys=True))

    def _merge_current_state(self, updates: dict[str, Any]) -> dict[str, Any]:
        current = self._read_current_state()
        current.update(self._redact(updates))
        self._write_current_state(current)
        return current

    def _redact(self, value: Any) -> Any:
        if isinstance(value, str):
            return redact_secrets(value)
        if isinstance(value, list):
            return [self._redact(item) for item in value]
        if isinstance(value, dict):
            return {k: self._redact(v) for k, v in value.items()}
        return value

    def _slot_allowlist(self, agent_name: str) -> set[str]:
        if not self.registry:
            return {f"{_slugify(agent_name).replace('.', '_')}_slot"}
        agent = self.registry.get_agent(agent_name) or {}
        return {entry for entry in agent.get("writes", []) if isinstance(entry, str) and entry.endswith("_slot")}

    def write_slot(
        self,
        agent_name: str,
        slot_name: str,
        data: dict[str, Any],
        *,
        status: str = "done",
        summary: str | None = None,
        produced_artifacts: list[str] | None = None,
        issues: list[str] | None = None,
        next_actions: list[str] | None = None,
    ) -> dict[str, Any]:
        allowed = self._slot_allowlist(agent_name)
        if allowed and slot_name not in allowed:
            raise PermissionError(f"{agent_name} cannot write slot '{slot_name}'")

        slot = AgentSlot(
            owner=agent_name,
            status=status,
            summary=summary,
            data=self._redact(data),
            produced_artifacts=produced_artifacts or [],
            issues=issues or [],
            next_actions=next_actions or [],
        )
        slot_payload = slot.to_dict()
        (self.slots_dir / f"{slot_name}.json").write_text(json.dumps(slot_payload, indent=2, ensure_ascii=False, sort_keys=True))

        current = self._read_current_state()
        current.setdefault("slots", {})[slot_name] = slot_payload
        self._write_current_state(current)
        return slot_payload

    def get_slot(self, slot_name: str) -> dict[str, Any] | None:
        slot_path = self.slots_dir / f"{slot_name}.json"
        if not slot_path.exists():
            return None
        return json.loads(slot_path.read_text())

    def write_artifact(
        self,
        artifact_id: str,
        phase_dir: str,
        content: Any,
        *,
        created_by: str,
        kind: str = "markdown",
        status: str = "draft",
        summary: str = "",
    ) -> dict[str, Any]:
        current = self._read_current_state()
        existing = current.setdefault("artifacts", {}).get(artifact_id)
        version = (existing or {}).get("version", 0) + 1

        phase_path = self.artifacts_dir / phase_dir
        phase_path.mkdir(parents=True, exist_ok=True)

        if isinstance(content, (dict, list)):
            serialized = json.dumps(self._redact(content), indent=2, ensure_ascii=False, sort_keys=True)
            ext = ".json"
            resolved_kind = "json"
        else:
            serialized = str(self._redact(content))
            ext = ".md"
            resolved_kind = kind

        versioned_path = phase_path / f"{artifact_id}.v{version}{ext}"
        canonical_path = phase_path / f"{artifact_id}{ext}"
        versioned_path.write_text(serialized)
        canonical_path.write_text(serialized)

        ts = utc_now()
        artifact = Artifact(
            artifact_id=artifact_id,
            kind=resolved_kind,
            path=str(canonical_path),
            version=version,
            created_by=created_by,
            created_at=(existing or {}).get("created_at", ts),
            updated_at=ts,
            status=status,
            summary=summary,
            content_hash=hashlib.sha256(serialized.encode("utf-8")).hexdigest(),
        )
        payload = artifact.to_dict()
        current["artifacts"][artifact_id] = payload
        self._write_current_state(current)
        return payload

    def get_artifact(self, artifact_id: str) -> dict[str, Any] | None:
        return self._read_current_state().get("artifacts", {}).get(artifact_id)

    def artifact_versions(self, artifact_ids: list[str]) -> dict[str, int]:
        current = self._read_current_state().get("artifacts", {})
        return {
            artifact_id: current[artifact_id]["version"]
            for artifact_id in artifact_ids
            if artifact_id in current
        }

    def set_gate_status(
        self,
        gate_id: str,
        status: str,
        *,
        checked_by: str,
        required_artifacts: list[str] | None = None,
        blocking_issues: list[str] | None = None,
        warnings: list[str] | None = None,
    ) -> dict[str, Any]:
        gate = GateStatus(
            gate_id=gate_id,
            status=status,
            checked_by=checked_by,
            checked_at=utc_now(),
            required_artifacts=required_artifacts or [],
            blocking_issues=blocking_issues or [],
            warnings=warnings or [],
        )
        payload = gate.to_dict()
        current = self._read_current_state()
        current.setdefault("gates", {})[gate_id] = payload
        self._write_current_state(current)
        return payload

    def record_approval(
        self,
        gate: str,
        status: str,
        *,
        requested_by: str,
        artifact_versions: dict[str, int] | None = None,
        user_response: str | None = None,
    ) -> dict[str, Any]:
        current = self._read_current_state()
        existing = current.setdefault("approvals", {}).get(gate)
        approval = Approval(
            approval_id=gate,
            gate=gate,
            status=status,
            requested_by=requested_by,
            requested_at=(existing or {}).get("requested_at", utc_now()),
            answered_at=utc_now() if status != "pending" else None,
            user_response=user_response,
            artifact_versions=artifact_versions or {},
        )
        payload = approval.to_dict()
        current["approvals"][gate] = payload
        self._write_current_state(current)
        return payload

    def append_events(self, events: list[dict[str, Any]]) -> None:
        if not events:
            return
        with self.events_log_path.open("a", encoding="utf-8") as fh:
            for event in self._redact(events):
                fh.write(json.dumps(event, ensure_ascii=False, sort_keys=True) + "\n")

        current = self._read_current_state()
        current["events_count"] = int(current.get("events_count", 0)) + len(events)
        current["last_event"] = self._redact(events[-1])
        self._write_current_state(current)

    def append_skill_events(self, events: list[dict[str, Any]]) -> None:
        if not events:
            return
        with self.skill_events_log_path.open("a", encoding="utf-8") as fh:
            for event in self._redact(events):
                fh.write(json.dumps(event, ensure_ascii=False, sort_keys=True) + "\n")

        current = self._read_current_state()
        current["skill_events_count"] = int(current.get("skill_events_count", 0)) + len(events)
        current["last_skill_event"] = self._redact(events[-1])
        self._write_current_state(current)

    def write_runtime_metadata(self, updates: dict[str, Any]) -> dict[str, Any]:
        return self._merge_current_state(updates)

    def snapshot(self) -> dict[str, Any]:
        return self._read_current_state()
