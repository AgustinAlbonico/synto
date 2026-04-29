"""MemoryStore — SQLite + FTS5 persistent memory backend with full schema."""

import json
import sqlite3
import time
from pathlib import Path
from typing import Optional
from uuid import uuid4

from synto.memory.models import (
    MemoryItem, MemoryKind, MemoryStatus,
    MemoryCandidate, MemoryLink,
    MemorySearchResult, MemoryAuditEntry,
)
from synto.memory.schema import SCHEMA_SQL
from synto.memory.redaction import redact_secrets


class MemoryStore:
    """SQLite + FTS5 memory store with hierarchical organization.

    Hierarchy: Project -> Feature -> Topic -> MemoryItem
    Graph via memory_links. Candidates for pending review.
    Full audit trail.
    """

    def __init__(self, db_path: str = "memory_store.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(str(self.db_path))
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA journal_mode=WAL")
        self.conn.execute("PRAGMA foreign_keys=ON")
        self._init_db()

    def _init_db(self):
        self.conn.executescript(SCHEMA_SQL)
        self.conn.commit()

    # --- Audit helper ---

    def _audit(self, action: str, actor: str, target_id: str = "", details: str = ""):
        self.conn.execute(
            "INSERT INTO memory_audit (timestamp, action, actor, target_id, details) VALUES (?, ?, ?, ?, ?)",
            (time.time(), action, actor, target_id, details),
        )

    # --- Projects ---

    def create_project(self, slug: str, name: str) -> str:
        project_id = uuid4().hex[:12]
        self.conn.execute(
            "INSERT INTO projects (id, slug, name, created_at) VALUES (?, ?, ?, ?)",
            (project_id, slug, name, time.time()),
        )
        self.conn.commit()
        self._audit("create_project", "system", project_id, f"slug={slug}")
        return project_id

    def get_project(self, slug: str) -> Optional[dict]:
        c = self.conn.execute("SELECT * FROM projects WHERE slug = ? OR id = ?", (slug, slug))
        row = c.fetchone()
        return dict(row) if row else None

    def get_project_by_id(self, project_id: str) -> Optional[dict]:
        c = self.conn.execute("SELECT * FROM projects WHERE id = ?", (project_id,))
        row = c.fetchone()
        return dict(row) if row else None

    def list_projects(self) -> list[dict]:
        c = self.conn.execute("SELECT * FROM projects ORDER BY name")
        return [dict(r) for r in c.fetchall()]

    # --- Features ---

    def create_feature(self, project_id: str, slug: str, name: str) -> str:
        fid = uuid4().hex[:12]
        self.conn.execute(
            "INSERT INTO features (id, project_id, slug, name, created_at) VALUES (?, ?, ?, ?, ?)",
            (fid, project_id, slug, name, time.time()),
        )
        self.conn.commit()
        return fid

    def list_features(self, project_id: str) -> list[dict]:
        c = self.conn.execute(
            "SELECT * FROM features WHERE project_id = ? ORDER BY name",
            (project_id,),
        )
        return [dict(r) for r in c.fetchall()]

    # --- Topics ---

    def create_topic(self, project_id: str, slug: str, name: str, feature_id: str = "") -> str:
        tid = uuid4().hex[:12]
        self.conn.execute(
            "INSERT INTO topics (id, project_id, feature_id, slug, name, created_at) VALUES (?, ?, ?, ?, ?, ?)",
            (tid, project_id, feature_id, slug, name, time.time()),
        )
        self.conn.commit()
        return tid

    def list_topics(self, project_id: str, feature_id: str = "") -> list[dict]:
        if feature_id:
            c = self.conn.execute(
                "SELECT * FROM topics WHERE project_id = ? AND feature_id = ? ORDER BY name",
                (project_id, feature_id),
            )
        else:
            c = self.conn.execute(
                "SELECT * FROM topics WHERE project_id = ? ORDER BY name",
                (project_id,),
            )
        return [dict(r) for r in c.fetchall()]

    # --- Memory Items CRUD ---

    def add_memory_item(self, item: MemoryItem, actor: str = "system") -> str:
        item.content = redact_secrets(item.content)
        item.title = redact_secrets(item.title)
        d = item.to_db_row()
        self.conn.execute(
            "INSERT INTO memory_items (id, project_id, feature_id, topic_id, kind, status, title, content, tags, importance, confidence, metadata, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (d["id"], d["project_id"], d["feature_id"], d["topic_id"],
             d["kind"], d["status"], d["title"], d["content"],
             d["tags"], d["importance"], d["confidence"],
             d["metadata"], d["created_at"], d["updated_at"]),
        )
        self.conn.commit()
        self._audit("add", actor, item.id, f"kind={item.kind.value}")
        return item.id

    def get_memory_item(self, memory_id: str) -> Optional[MemoryItem]:
        c = self.conn.execute(
            "SELECT * FROM memory_items WHERE id = ?", (memory_id,),
        )
        row = c.fetchone()
        return MemoryItem.from_db_row(dict(row)) if row else None

    def update_memory_item(self, item: MemoryItem, actor: str = "system") -> None:
        item.content = redact_secrets(item.content)
        item.updated_at = time.time()
        d = item.to_db_row()
        self.conn.execute(
            "UPDATE memory_items SET project_id=?, feature_id=?, topic_id=?, kind=?, status=?, title=?, content=?, tags=?, importance=?, confidence=?, metadata=?, updated_at=? WHERE id=?",
            (d["project_id"], d["feature_id"], d["topic_id"], d["kind"],
             d["status"], d["title"], d["content"], d["tags"],
             d["importance"], d["confidence"], d["metadata"],
             d["updated_at"], d["id"]),
        )
        self.conn.commit()
        self._audit("update", actor, item.id)

    def delete_memory_item(self, memory_id: str, actor: str = "system") -> None:
        self.conn.execute(
            "UPDATE memory_items SET status='archived', updated_at=? WHERE id=?",
            (time.time(), memory_id),
        )
        self.conn.commit()
        self._audit("delete", actor, memory_id)

    # --- Search ---

    def search(self, query: str, project_id: str = "", limit: int = 20) -> list[MemorySearchResult]:
        # Convert simple space-separated queries to OR for better recall
        # But don't mangle queries that already have FTS operators
        fts_query = query
        terms = query.split()
        if len(terms) > 1 and " OR " not in query and " AND " not in query and '"' not in query:
            fts_query = " OR ".join(terms)
        else:
            fts_query = query

        if project_id:
            c = self.conn.execute(
                """SELECT m.*, fts.rank
                   FROM memory_items m
                   JOIN memory_items_fts fts ON m.rowid = fts.rowid
                   WHERE memory_items_fts MATCH ? AND m.project_id = ? AND m.status = 'active'
                   ORDER BY fts.rank
                   LIMIT ?""",
                (fts_query, project_id, limit),
            )
        else:
            c = self.conn.execute(
                """SELECT m.*, fts.rank
                   FROM memory_items m
                   JOIN memory_items_fts fts ON m.rowid = fts.rowid
                   WHERE memory_items_fts MATCH ? AND m.status = 'active'
                   ORDER BY fts.rank
                   LIMIT ?""",
                (fts_query, limit),
            )
        results = []
        for row in c.fetchall():
            d = dict(row)
            item = MemoryItem.from_db_row(d)
            # Normalize rank (FTS5 rank is negative, closer to 0 = better)
            score = max(0.0, min(1.0, 1.0 + d.get("rank", 0)))
            results.append(MemorySearchResult(item=item, score=score))
        return results

    def list_by_project(self, project_id: str) -> list[MemoryItem]:
        c = self.conn.execute(
            "SELECT * FROM memory_items WHERE project_id = ? AND status = 'active' ORDER BY updated_at DESC",
            (project_id,),
        )
        return [MemoryItem.from_db_row(dict(r)) for r in c.fetchall()]

    def list_by_hierarchy(self, project_id: str, feature_id: str = "", topic_id: str = "") -> list[MemoryItem]:
        filters = ["project_id = ?", "status = 'active'"]
        params: list[Any] = [project_id]
        if feature_id and not topic_id:
            # Items of this feature (any topic, including no topic)
            filters.append("feature_id = ?")
            params.append(feature_id)
        elif topic_id:
            filters.append("topic_id = ?")
            params.append(topic_id)
        # If no feature_id/topic_id, return all items for the project

        c = self.conn.execute(
            f"SELECT * FROM memory_items WHERE {' AND '.join(filters)} ORDER BY updated_at DESC",
            params,
        )
        return [MemoryItem.from_db_row(dict(r)) for r in c.fetchall()]

    # --- Links ---

    def link_items(self, source_id: str, target_id: str, link_type: str = "related", strength: float = 0.5, actor: str = "system") -> str:
        link = MemoryLink(source_id=source_id, target_id=target_id, link_type=link_type, strength=strength)
        self.conn.execute(
            "INSERT INTO memory_links (id, source_id, target_id, link_type, strength, created_at) VALUES (?, ?, ?, ?, ?, ?)",
            (link.id, link.source_id, link.target_id, link.link_type, link.strength, time.time()),
        )
        self.conn.commit()
        self._audit("link", actor, source_id, f"-> {target_id}")
        return link.id

    def get_links(self, memory_id: str) -> list[MemoryLink]:
        c = self.conn.execute(
            "SELECT * FROM memory_links WHERE source_id = ? OR target_id = ?",
            (memory_id, memory_id),
        )
        return [MemoryLink(**dict(r)) for r in c.fetchall()]

    # --- Candidates ---

    def add_candidate(self, candidate: MemoryCandidate) -> str:
        d = candidate.model_dump()
        self.conn.execute(
            "INSERT INTO memory_candidates (id, source_agent, kind, title, content, project_id, feature_id, topic_id, tags, reasoning, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (d["id"], d["source_agent"], d["kind"], d["title"], d["content"],
             d["project_id"], d["feature_id"], d["topic_id"],
             json.dumps(d["tags"]), d["reasoning"], d["created_at"]),
        )
        self.conn.commit()
        self._audit("add_candidate", d["source_agent"], d["id"])
        return candidate.id

    def list_candidates(self, project_id: str = "") -> list[dict]:
        if project_id:
            c = self.conn.execute(
                "SELECT * FROM memory_candidates WHERE project_id = ? ORDER BY created_at DESC",
                (project_id,),
            )
        else:
            c = self.conn.execute("SELECT * FROM memory_candidates ORDER BY created_at DESC")
        return [dict(r) for r in c.fetchall()]

    def commit_candidate(self, candidate_id: str, actor: str = "system") -> str:
        c = self.conn.execute("SELECT * FROM memory_candidates WHERE id = ?", (candidate_id,))
        row = c.fetchone()
        if not row:
            raise ValueError(f"Candidate {candidate_id} not found")

        # Resolve project: candidate may have slug, but FK needs UUID id
        project_slug = row["project_id"]
        project_row = self.conn.execute(
            "SELECT id FROM projects WHERE id = ? OR slug = ?",
            (project_slug, project_slug),
        ).fetchone()
        resolved_project_id = project_row["id"] if project_row else project_slug

        # Resolve feature if present
        feature_id = row["feature_id"]
        if feature_id:
            feat_row = self.conn.execute(
                "SELECT id FROM features WHERE id = ? OR slug = ? AND project_id = ?",
                (feature_id, feature_id, resolved_project_id),
            ).fetchone()
            feature_id = feat_row["id"] if feat_row else feature_id

        # Resolve topic if present
        topic_id = row["topic_id"]
        if topic_id:
            top_row = self.conn.execute(
                "SELECT id FROM topics WHERE id = ? OR slug = ? AND project_id = ?",
                (topic_id, topic_id, resolved_project_id),
            ).fetchone()
            topic_id = top_row["id"] if top_row else topic_id

        item = MemoryItem(
            project_id=resolved_project_id,
            feature_id=feature_id if feature_id else "",
            topic_id=topic_id if topic_id else "",
            kind=MemoryKind(row["kind"]),
            title=row["title"],
            content=row["content"],
            tags=json.loads(row["tags"]) if row["tags"] else [],
            metadata={"from_candidate": candidate_id, "source_agent": row["source_agent"]},
        )
        self.add_memory_item(item, actor=actor)

        self.conn.execute("DELETE FROM memory_candidates WHERE id = ?", (candidate_id,))
        self.conn.commit()
        self._audit("commit_candidate", actor, candidate_id)
        return item.id

    def reject_candidate(self, candidate_id: str, reason: str = "", actor: str = "system") -> None:
        self.conn.execute("DELETE FROM memory_candidates WHERE id = ?", (candidate_id,))
        self.conn.commit()
        self._audit("reject_candidate", actor, candidate_id, reason)

    # --- Audit ---

    def get_audit_log(self, limit: int = 50) -> list[dict]:
        c = self.conn.execute(
            "SELECT * FROM memory_audit ORDER BY timestamp DESC LIMIT ?",
            (limit,),
        )
        return [dict(r) for r in c.fetchall()]

    # --- Stats ---

    def stats(self) -> dict:
        c = self.conn.execute("SELECT COUNT(*) as count FROM memory_items WHERE status = 'active'")
        total = c.fetchone()["count"]
        c = self.conn.execute("SELECT COUNT(DISTINCT project_id) as count FROM memory_items")
        projects = c.fetchone()["count"]
        c = self.conn.execute("SELECT COUNT(*) as count FROM memory_links")
        links = c.fetchone()["count"]
        c = self.conn.execute("SELECT COUNT(*) as count FROM memory_candidates")
        candidates = c.fetchone()["count"]
        return {"total_memories": total, "projects": projects, "links": links, "candidates": candidates}

    def close(self):
        self.conn.close()

    def __del__(self):
        try:
            self.close()
        except Exception:
            pass
