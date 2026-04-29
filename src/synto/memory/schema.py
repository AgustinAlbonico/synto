"""SQLite schema initialization for MemoryStore."""

SCHEMA_SQL = """
-- Projects table
CREATE TABLE IF NOT EXISTS projects (
    id TEXT PRIMARY KEY,
    slug TEXT UNIQUE NOT NULL,
    name TEXT NOT NULL,
    created_at REAL NOT NULL
);

-- Features table
CREATE TABLE IF NOT EXISTS features (
    id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL REFERENCES projects(id),
    slug TEXT NOT NULL,
    name TEXT NOT NULL,
    created_at REAL NOT NULL,
    UNIQUE(project_id, slug)
);

-- Topics table
CREATE TABLE IF NOT EXISTS topics (
    id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL REFERENCES projects(id),
    feature_id TEXT DEFAULT '' REFERENCES features(id),
    slug TEXT NOT NULL,
    name TEXT NOT NULL,
    created_at REAL NOT NULL,
    UNIQUE(project_id, slug)
);

-- Main memory items table
CREATE TABLE IF NOT EXISTS memory_items (
    id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL REFERENCES projects(id),
    feature_id TEXT DEFAULT NULL REFERENCES features(id),
    topic_id TEXT DEFAULT NULL REFERENCES topics(id),
    kind TEXT NOT NULL DEFAULT 'note',
    status TEXT NOT NULL DEFAULT 'active',
    title TEXT DEFAULT '',
    content TEXT NOT NULL,
    tags TEXT DEFAULT '[]',
    importance REAL DEFAULT 0.5,
    confidence REAL DEFAULT 0.5,
    metadata TEXT DEFAULT '{}',
    created_at REAL NOT NULL,
    updated_at REAL NOT NULL
);

-- FTS5 virtual table for full-text search
CREATE VIRTUAL TABLE IF NOT EXISTS memory_items_fts
USING fts5(content, title, tags, kind,
           content='memory_items', content_rowid='rowid');

-- Triggers for FTS5 sync
CREATE TRIGGER IF NOT EXISTS mi_ai AFTER INSERT ON memory_items
BEGIN
    INSERT INTO memory_items_fts(rowid, content, title, tags, kind)
    VALUES (new.rowid, new.content, new.title, new.tags, new.kind);
END;

CREATE TRIGGER IF NOT EXISTS mi_ad AFTER DELETE ON memory_items
BEGIN
    INSERT INTO memory_items_fts(memory_items_fts, rowid, content, title, tags, kind)
    VALUES ('delete', old.rowid, old.content, old.title, old.tags, old.kind);
END;

CREATE TRIGGER IF NOT EXISTS mi_au AFTER UPDATE ON memory_items
BEGIN
    INSERT INTO memory_items_fts(memory_items_fts, rowid, content, title, tags, kind)
    VALUES ('delete', old.rowid, old.content, old.title, old.tags, old.kind);
    INSERT INTO memory_items_fts(rowid, content, title, tags, kind)
    VALUES (new.rowid, new.content, new.title, new.tags, new.kind);
END;

-- Memory links (graph relationships)
CREATE TABLE IF NOT EXISTS memory_links (
    id TEXT PRIMARY KEY,
    source_id TEXT NOT NULL REFERENCES memory_items(id),
    target_id TEXT NOT NULL REFERENCES memory_items(id),
    link_type TEXT NOT NULL DEFAULT 'related',
    strength REAL DEFAULT 0.5,
    created_at REAL NOT NULL
);

-- Memory candidates (pending review)
CREATE TABLE IF NOT EXISTS memory_candidates (
    id TEXT PRIMARY KEY,
    source_agent TEXT DEFAULT '',
    kind TEXT NOT NULL DEFAULT 'note',
    title TEXT DEFAULT '',
    content TEXT NOT NULL,
    project_id TEXT DEFAULT '',
    feature_id TEXT DEFAULT '',
    topic_id TEXT DEFAULT '',
    tags TEXT DEFAULT '[]',
    reasoning TEXT DEFAULT '',
    created_at REAL NOT NULL
);

-- Audit log
CREATE TABLE IF NOT EXISTS memory_audit (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp REAL NOT NULL,
    action TEXT NOT NULL,
    actor TEXT NOT NULL,
    target_id TEXT DEFAULT '',
    details TEXT DEFAULT ''
);

-- Sessions (runs)
CREATE TABLE IF NOT EXISTS sessions (
    id TEXT PRIMARY KEY,
    project_id TEXT REFERENCES projects(id),
    task TEXT NOT NULL,
    started_at REAL NOT NULL,
    finished_at REAL,
    status TEXT DEFAULT 'running',
    metadata TEXT DEFAULT '{}'
);

-- Access log (which agent read what)
CREATE TABLE IF NOT EXISTS memory_access_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp REAL NOT NULL,
    agent_id TEXT NOT NULL,
    memory_id TEXT NOT NULL REFERENCES memory_items(id),
    action TEXT NOT NULL DEFAULT 'read'
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_mi_project ON memory_items(project_id);
CREATE INDEX IF NOT EXISTS idx_mi_status ON memory_items(status);
CREATE INDEX IF NOT EXISTS idx_mi_kind ON memory_items(kind);
CREATE INDEX IF NOT EXISTS idx_mi_hierarchy ON memory_items(project_id, feature_id, topic_id);
CREATE INDEX IF NOT EXISTS idx_ml_source ON memory_links(source_id);
CREATE INDEX IF NOT EXISTS idx_ml_target ON memory_links(target_id);
CREATE INDEX IF NOT EXISTS idx_mc_project ON memory_candidates(project_id);
CREATE INDEX IF NOT EXISTS idx_audit_target ON memory_audit(target_id);
CREATE INDEX IF NOT EXISTS idx_sessions_project ON sessions(project_id);
"""
