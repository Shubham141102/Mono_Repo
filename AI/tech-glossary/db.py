"""SQLite storage for saved glossary terms."""
import json
import sqlite3
from datetime import datetime
from pathlib import Path

DB_PATH = Path(__file__).parent / "glossary.db"


def _conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init():
    with _conn() as c:
        c.execute(
            """CREATE TABLE IF NOT EXISTS terms (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                lookup_key TEXT UNIQUE,      -- normalized term + chosen meaning
                name TEXT,
                category TEXT,
                subcategory TEXT,
                tags TEXT,                   -- JSON list
                data TEXT,                   -- full JSON entry from Claude
                notes TEXT DEFAULT '',
                created_at TEXT
            )"""
        )
        # Columns added later: add them to existing databases without losing data.
        cols = {r["name"] for r in c.execute("PRAGMA table_info(terms)")}
        for name, ddl in [("deep_dive", "TEXT DEFAULT ''"), ("deep_dive_meta", "TEXT DEFAULT ''")]:
            if name not in cols:
                c.execute(f"ALTER TABLE terms ADD COLUMN {name} {ddl}")


def make_key(term: str, sense: str | None) -> str:
    return f"{term.strip().lower()}::{(sense or '').strip().lower()}"


def get_by_key(key: str):
    with _conn() as c:
        row = c.execute("SELECT * FROM terms WHERE lookup_key = ?", (key,)).fetchone()
    return _row(row) if row else None


def save(key: str, entry: dict) -> int:
    with _conn() as c:
        cur = c.execute(
            """INSERT INTO terms (lookup_key, name, category, subcategory, tags, data, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?)
               ON CONFLICT(lookup_key) DO UPDATE SET
                 name=excluded.name, category=excluded.category,
                 subcategory=excluded.subcategory, tags=excluded.tags, data=excluded.data""",
            (
                key,
                entry["name"],
                entry["category"],
                entry["subcategory"],
                json.dumps(entry["tags"]),
                json.dumps(entry),
                datetime.now().isoformat(timespec="seconds"),
            ),
        )
        return cur.lastrowid


def update_notes(term_id: int, notes: str):
    with _conn() as c:
        c.execute("UPDATE terms SET notes = ? WHERE id = ?", (notes, term_id))


def set_placement(term_id: int, category: str, subcategory: str):
    """Move a term to another Area > Topic (keeps the stored JSON in sync)."""
    with _conn() as c:
        row = c.execute("SELECT data FROM terms WHERE id = ?", (term_id,)).fetchone()
        if not row:
            return
        data = json.loads(row["data"])
        data["category"], data["subcategory"] = category, subcategory
        c.execute("UPDATE terms SET category = ?, subcategory = ?, data = ? WHERE id = ?",
                  (category, subcategory, json.dumps(data), term_id))


def set_deep_dive(term_id: int, text: str, meta: str):
    """Save the long-form deep dive. meta is e.g. 'Claude · 2026-11-20'."""
    with _conn() as c:
        c.execute("UPDATE terms SET deep_dive = ?, deep_dive_meta = ? WHERE id = ?", (text, meta, term_id))


def delete(term_id: int):
    with _conn() as c:
        c.execute("DELETE FROM terms WHERE id = ?", (term_id,))


def all_terms():
    with _conn() as c:
        rows = c.execute("SELECT * FROM terms ORDER BY category, subcategory, name").fetchall()
    return [_row(r) for r in rows]


def category_tree() -> dict[str, list[str]]:
    """Existing categories -> subcategories, so Claude can reuse them."""
    with _conn() as c:
        rows = c.execute(
            "SELECT DISTINCT category, subcategory FROM terms ORDER BY category, subcategory"
        ).fetchall()
    tree: dict[str, list[str]] = {}
    for r in rows:
        tree.setdefault(r["category"], []).append(r["subcategory"])
    return tree


def _row(r) -> dict:
    d = dict(r)
    d["tags"] = json.loads(d["tags"] or "[]")
    d["data"] = json.loads(d["data"])
    return d
