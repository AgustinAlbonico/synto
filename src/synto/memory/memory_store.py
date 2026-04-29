"""MemoryStore — SQLite + FTS5 persistent memory backend."""

import json
import sqlite3
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional

# --- Data models ---

@dataclass
class MemoryItem:
    """Single memory entry."""
    id: Optional[int] = None
    project: str = ""
    feature: str = ""
    topic: str = ""
    content: str = ""
    metadata: dict = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    trust: float = 0.5

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "project": self.project,
            "feature": self.feature,
            "topic": self.topic,
            "content": self.content,
            "metadata": json.dumps(self.metadata),
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "trust": self.trust,
        }

    @classmethod
    def from_row(cls, row: dict) -> "MemoryItem":
        return cls(
            id=row["id"],
            project=row["project"],
            feature=row["feature"],
            topic=row["topic"],
            content=row["content"],
            metadata=json.loads(row["metadata"]) if row["metadata"] else {},
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            trust=row.get("trust", 0.5),
        )


# --- MemoryStore ---

class MemoryStore:
    """SQLite + FTS5 memory store with hierarchical organization.

    Hierarchy: Project -> Feature -> Topic -> MemoryItem
    Lightweight graph via memory_links table.
    """

    def __init__(self, db_path: str = "memory_store.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(str(self.db_path))
        self.conn.row_factory = sqlite3.Row
        self._init_db()

    def _init_db(self):
        conn = self.conn
        c = conn.cursor()

        # Main memory table
        c.execute("""
            CREATE TABLE IF NOT EXISTS memories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project TEXT NOT NULL,
                feature TEXT NOT NULL DEFAULT '',
                topic TEXT NOT NULL DEFAULT '',
                content TEXT NOT NULL,
                metadata TEXT DEFAULT '{}',
                created_at REAL NOT NULL,
                updated_at REAL NOT NULL,
                trust REAL DEFAULT 0.5
            )
        """)

        # FTS5 virtual table for full-text search
        c.execute("""
            CREATE VIRTUAL TABLE IF NOT EXISTS memories_fts
            USING fts5(content, project, feature, topic,
                       content='memories', content_rowid='id')
        """)

        # Triggers to keep FTS in sync
        c.execute("""
            CREATE TRIGGER IF NOT EXISTS memories_ai AFTER INSERT ON memories
            BEGIN
                INSERT INTO memories_fts(rowid, content, project, feature, topic)
                VALUES (new.id, new.content, new.project, new.feature, new.topic);
            END
        """)

        c.execute("""
            CREATE TRIGGER IF NOT EXISTS memories_ad AFTER DELETE ON memories
            BEGIN
                INSERT INTO memories_fts(memories_fts, rowid, content, project, feature, topic)
                VALUES ('delete', old.id, old.content, old.project, old.feature, old.topic);
            END
        """)

        c.execute("""
            CREATE TRIGGER IF NOT EXISTS memories_au AFTER UPDATE ON memories
            BEGIN
                INSERT INTO memories_fts(memories_fts, rowid, content, project, feature, topic)
                VALUES ('delete', old.id, old.content, old.project, old.feature, old.topic);
                INSERT INTO memories_fts(rowid, content, project, feature, topic)
                VALUES (new.id, new.content, new.project, new.feature, new.topic);
            END
        """)

        # Memory links (lightweight graph)
        c.execute("""
            CREATE TABLE IF NOT EXISTS memory_links (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source_id INTEGER NOT NULL REFERENCES memories(id),
                target_id INTEGER NOT NULL REFERENCES memories(id),
                link_type TEXT NOT NULL DEFAULT 'related',
                created_at REAL NOT NULL
            )
        """)

        # Indexes
        c.execute("""
            CREATE INDEX IF NOT EXISTS idx_memories_project
            ON memories(project)
        """)
        c.execute("""
            CREATE INDEX IF NOT EXISTS idx_memories_hierarchy
            ON memories(project, feature, topic)
        """)

        conn.commit()

    # --- CRUD ---

    def add(self, item: MemoryItem) -> int:
        """Insert a memory item. Returns the new id."""
        c = self.conn.cursor()
        d = item.to_dict()
        c.execute(
            "INSERT INTO memories (project, feature, topic, content, metadata, created_at, updated_at, trust) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (d["project"], d["feature"], d["topic"], d["content"],
             d["metadata"], d["created_at"], d["updated_at"], d["trust"]),
        )
        self.conn.commit()
        return c.lastrowid

    def get(self, memory_id: int) -> Optional[MemoryItem]:
        c = self.conn.cursor()
        c.execute("SELECT * FROM memories WHERE id = ?", (memory_id,))
        row = c.fetchone()
        return MemoryItem.from_row(dict(row)) if row else None

    def update(self, item: MemoryItem) -> None:
        item.updated_at = time.time()
        d = item.to_dict()
        self.conn.execute(
            "UPDATE memories SET project=?, feature=?, topic=?, content=?, metadata=?, updated_at=?, trust=? WHERE id=?",
            (d["project"], d["feature"], d["topic"], d["content"],
             d["metadata"], d["updated_at"], d["trust"], d["id"]),
        )
        self.conn.commit()

    def delete(self, memory_id: int) -> None:
        self.conn.execute("DELETE FROM memories WHERE id = ?", (memory_id,))
        self.conn.commit()

    # --- Queries ---

    def search(self, query: str, project: str = "", limit: int = 20) -> list[MemoryItem]:
        """Full-text search via FTS5."""
        c = self.conn.cursor()
        if project:
            c.execute(
                """SELECT m.* FROM memories m
                   JOIN memories_fts f ON m.id = f.rowid
                   WHERE memories_fts MATCH ? AND m.project = ?
                   ORDER BY rank LIMIT ?""",
                (query, project, limit),
            )
        else:
            c.execute(
                """SELECT m.* FROM memories m
                   JOIN memories_fts f ON m.id = f.rowid
                   WHERE memories_fts MATCH ?
                   ORDER BY rank LIMIT ?""",
                (query, limit),
            )
        return [MemoryItem.from_row(dict(r)) for r in c.fetchall()]

    def list_by_project(self, project: str) -> list[MemoryItem]:
        c = self.conn.cursor()
        c.execute(
            "SELECT * FROM memories WHERE project = ? ORDER BY updated_at DESC",
            (project,),
        )
        return [MemoryItem.from_row(dict(r)) for r in c.fetchall()]

    def list_by_hierarchy(
        self, project: str, feature: str = "", topic: str = ""
    ) -> list[MemoryItem]:
        filters = ["project = ?"]
        params = [project]
        if feature:
            filters.append("feature = ?")
            params.append(feature)
        if topic:
            filters.append("topic = ?")
            params.append(topic)

        c = self.conn.cursor()
        c.execute(
            f"SELECT * FROM memories WHERE {' AND '.join(filters)} ORDER BY updated_at DESC",
            params,
        )
        return [MemoryItem.from_row(dict(r)) for r in c.fetchall()]

    def get_projects(self) -> list[str]:
        c = self.conn.cursor()
        c.execute("SELECT DISTINCT project FROM memories ORDER BY project")
        return [r["project"] for r in c.fetchall()]

    # --- Links ---

    def link(self, source_id: int, target_id: int, link_type: str = "related") -> None:
        self.conn.execute(
            "INSERT INTO memory_links (source_id, target_id, link_type, created_at) VALUES (?, ?, ?, ?)",
            (source_id, target_id, link_type, time.time()),
        )
        self.conn.commit()

    def get_links(self, memory_id: int) -> list[tuple[int, str]]:
        c = self.conn.cursor()
        c.execute(
            "SELECT target_id, link_type FROM memory_links WHERE source_id = ?",
            (memory_id,),
        )
        return [(r["target_id"], r["link_type"]) for r in c.fetchall()]

    def stats(self) -> dict:
        c = self.conn.cursor()
        c.execute("SELECT COUNT(*) as count FROM memories")
        total = c.fetchone()["count"]
        c.execute("SELECT COUNT(DISTINCT project) as count FROM memories")
        projects = c.fetchone()["count"]
        c.execute("SELECT COUNT(*) as count FROM memory_links")
        links = c.fetchone()["count"]
        return {"total_memories": total, "projects": projects, "links": links}

    def close(self):
        self.conn.close()

    def __del__(self):
        try:
            self.close()
        except Exception:
            pass
