import sqlite3
import json
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "knowledge.db"
UPLOADS_DIR = Path(__file__).parent.parent / "uploads"


def get_db():
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    UPLOADS_DIR.mkdir(exist_ok=True)
    conn = get_db()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source TEXT NOT NULL,
            source_id TEXT,
            title TEXT NOT NULL,
            content TEXT DEFAULT '',
            url TEXT DEFAULT '',
            thumbnail TEXT DEFAULT '',
            summary TEXT DEFAULT '',
            domain TEXT DEFAULT 'Uncategorized',
            tags TEXT DEFAULT '[]',
            created_at TEXT DEFAULT '',
            imported_at TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL DEFAULT ''
        );

        CREATE INDEX IF NOT EXISTS idx_items_domain ON items(domain);
        CREATE INDEX IF NOT EXISTS idx_items_source ON items(source);
        CREATE INDEX IF NOT EXISTS idx_items_imported ON items(imported_at);
    """)
    conn.commit()
    conn.close()


def item_to_dict(row) -> dict:
    d = dict(row)
    try:
        d["tags"] = json.loads(d.get("tags", "[]") or "[]")
    except Exception:
        d["tags"] = []
    return d


def insert_item(conn, item: dict) -> int | None:
    """Insert item, ignoring duplicates (same source + source_id). Returns new id or None."""
    if item.get("source_id"):
        existing = conn.execute(
            "SELECT id FROM items WHERE source=? AND source_id=?",
            (item["source"], item["source_id"])
        ).fetchone()
        if existing:
            return None

    tags = json.dumps(item.get("tags", []))
    cursor = conn.execute(
        """INSERT INTO items (source, source_id, title, content, url, thumbnail, summary, domain, tags, created_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            item.get("source", ""),
            item.get("source_id"),
            item.get("title", "Untitled"),
            item.get("content", ""),
            item.get("url", ""),
            item.get("thumbnail", ""),
            item.get("summary", ""),
            item.get("domain", "Uncategorized"),
            tags,
            item.get("created_at", ""),
        )
    )
    return cursor.lastrowid


def get_setting(key: str, default: str = "") -> str:
    conn = get_db()
    row = conn.execute("SELECT value FROM settings WHERE key=?", (key,)).fetchone()
    conn.close()
    return row["value"] if row else default


def set_setting(key: str, value: str):
    conn = get_db()
    conn.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", (key, value))
    conn.commit()
    conn.close()
