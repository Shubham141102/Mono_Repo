"""
Database layer: schema + every SQL query the app runs.

Works with SQLite locally (no setup) and Postgres (Supabase) in production.
Set DATABASE_URL in .streamlit/secrets.toml to switch to Postgres.

Privacy rule: EVERY query that touches user data filters by user_id.
"""
import os

import streamlit as st
from sqlalchemy import (
    Boolean, CheckConstraint, Column, Date, DateTime, ForeignKey, Index, Integer,
    MetaData, Numeric, String, Table, UniqueConstraint, bindparam, create_engine,
    event, func, text,
)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
KINDS = ("expense", "income")
PAYMENT_METHODS = ["UPI", "Card", "Cash", "Bank transfer", "Other"]

DEFAULT_CATEGORIES = [
    ("Food & Dining", "expense", "🍔"), ("Groceries", "expense", "🛒"),
    ("Rent", "expense", "🏠"), ("Transport", "expense", "🚗"),
    ("Bills & Utilities", "expense", "💡"), ("Shopping", "expense", "🛍️"),
    ("Health", "expense", "💊"), ("Entertainment", "expense", "🎬"),
    ("Education", "expense", "📚"), ("Travel", "expense", "✈️"),
    ("Other", "expense", "📦"),
    ("Salary", "income", "💼"), ("Freelance", "income", "💻"),
    ("Investments", "income", "📈"), ("Gift", "income", "🎁"),
    ("Other", "income", "💰"),
]

# ---------------------------------------------------------------- schema
metadata = MetaData()

users = Table(
    "users", metadata,
    Column("id", Integer, primary_key=True),
    Column("name", String(100), nullable=False),
    Column("email", String(255), nullable=False, unique=True),
    Column("password_hash", String(100), nullable=False),
    Column("role", String(10), nullable=False, server_default="user"),
    Column("is_active", Boolean, nullable=False, server_default=text("true")),
    Column("created_at", DateTime, nullable=False, server_default=func.now()),
    CheckConstraint("role IN ('user', 'admin')", name="ck_users_role"),
)

categories = Table(
    "categories", metadata,
    Column("id", Integer, primary_key=True),
    # NULL user_id = built-in category everyone can use
    Column("user_id", Integer, ForeignKey("users.id", ondelete="CASCADE")),
    Column("name", String(50), nullable=False),
    Column("kind", String(10), nullable=False),
    Column("icon", String(10), nullable=False, server_default="📦"),
    CheckConstraint("kind IN ('expense', 'income')", name="ck_categories_kind"),
)

hidden_categories = Table(
    # a row here = this user has archived this category (built-in or custom)
    "hidden_categories", metadata,
    Column("user_id", Integer, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
    Column("category_id", Integer, ForeignKey("categories.id", ondelete="CASCADE"), primary_key=True),
)

transactions = Table(
    "transactions", metadata,
    Column("id", Integer, primary_key=True),
    Column("user_id", Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
    Column("category_id", Integer, ForeignKey("categories.id"), nullable=False),
    Column("kind", String(10), nullable=False),
    Column("amount", Numeric(12, 2), nullable=False),
    Column("txn_date", Date, nullable=False),
    Column("payment_method", String(20), nullable=False, server_default="UPI"),
    Column("tags", String(255), nullable=False, server_default=""),  # comma-separated
    Column("note", String(500), nullable=False, server_default=""),
    Column("created_at", DateTime, nullable=False, server_default=func.now()),
    Column("updated_at", DateTime, nullable=False, server_default=func.now()),
    CheckConstraint("amount > 0", name="ck_txn_amount_positive"),
    CheckConstraint("kind IN ('expense', 'income')", name="ck_txn_kind"),
    Index("ix_txn_user_date", "user_id", "txn_date"),
)

budgets = Table(
    "budgets", metadata,
    Column("id", Integer, primary_key=True),
    Column("user_id", Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
    Column("category_id", Integer, ForeignKey("categories.id"), nullable=False),
    Column("month", Date, nullable=False),  # always the 1st of the month
    Column("limit_amount", Numeric(12, 2), nullable=False),
    CheckConstraint("limit_amount > 0", name="ck_budget_positive"),
    UniqueConstraint("user_id", "category_id", "month", name="uq_budget_user_cat_month"),
)


# ---------------------------------------------------------------- engine
def _secret(name, default=""):
    try:
        return st.secrets.get(name, default)
    except Exception:
        return os.environ.get(name, default)


@st.cache_resource
def get_engine():
    url = _secret("DATABASE_URL") or f"sqlite:///{os.path.join(BASE_DIR, 'expenses.db')}"
    engine = create_engine(url, pool_pre_ping=True)
    if engine.dialect.name == "sqlite":
        @event.listens_for(engine, "connect")
        def _fk_on(dbapi_conn, _):
            dbapi_conn.execute("PRAGMA foreign_keys = ON")
    return engine


@st.cache_resource
def init_db():
    """Create tables (if missing) and seed default categories once."""
    engine = get_engine()
    metadata.create_all(engine)
    with engine.begin() as conn:
        n = conn.execute(text("SELECT COUNT(*) FROM categories WHERE user_id IS NULL")).scalar()
        if n == 0:
            conn.execute(
                text("INSERT INTO categories (user_id, name, kind, icon) VALUES (NULL, :n, :k, :i)"),
                [{"n": n_, "k": k, "i": i} for n_, k, i in DEFAULT_CATEGORIES],
            )
    return True


def run(sql, params=None, *, write=False):
    """Execute SQL. Returns list of dict rows for reads, rowcount for writes."""
    engine = get_engine()
    if write:
        with engine.begin() as conn:
            return conn.execute(sql if not isinstance(sql, str) else text(sql), params or {}).rowcount
    with engine.connect() as conn:
        res = conn.execute(sql if not isinstance(sql, str) else text(sql), params or {})
        return [dict(r._mapping) for r in res]


# ---------------------------------------------------------------- users
def count_users():
    return run("SELECT COUNT(*) AS n FROM users")[0]["n"]


def get_user_by_email(email):
    rows = run("SELECT * FROM users WHERE email = :e", {"e": email})
    return rows[0] if rows else None


def create_user(name, email, password_hash, role="user"):
    run(
        "INSERT INTO users (name, email, password_hash, role) VALUES (:n, :e, :p, :r)",
        {"n": name, "e": email, "p": password_hash, "r": role},
        write=True,
    )


# ---------------------------------------------------------------- categories
def get_categories(user_id, kind=None, include_archived=True):
    """Built-in categories + the user's own custom ones, with archive flag and record count."""
    sql = """
        SELECT c.id, c.name, c.kind, c.icon,
               CASE WHEN c.user_id IS NULL THEN 0 ELSE 1 END AS is_custom,
               CASE WHEN h.category_id IS NULL THEN 0 ELSE 1 END AS archived,
               (SELECT COUNT(*) FROM transactions t
                 WHERE t.category_id = c.id AND t.user_id = :uid) AS records
        FROM categories c
        LEFT JOIN hidden_categories h ON h.category_id = c.id AND h.user_id = :uid
        WHERE (c.user_id IS NULL OR c.user_id = :uid)
    """
    params = {"uid": user_id}
    if kind:
        sql += " AND c.kind = :kind"
        params["kind"] = kind
    if not include_archived:
        sql += " AND h.category_id IS NULL"
    sql += " ORDER BY c.kind, c.name"
    return run(sql, params)


def _name_taken(user_id, kind, name, exclude_id=None):
    rows = run(
        """SELECT id FROM categories
           WHERE (user_id IS NULL OR user_id = :uid) AND kind = :kind
             AND LOWER(name) = LOWER(:name)""",
        {"uid": user_id, "kind": kind, "name": name},
    )
    return any(r["id"] != exclude_id for r in rows)


def add_category(user_id, kind, name, icon):
    name = name.strip()
    if not name or len(name) > 50:
        raise ValueError("Name must be 1-50 characters.")
    if kind not in KINDS:
        raise ValueError("Invalid type.")
    if _name_taken(user_id, kind, name):
        raise ValueError(f"A {kind} category named '{name}' already exists.")
    run("INSERT INTO categories (user_id, name, kind, icon) VALUES (:uid, :n, :k, :i)",
        {"uid": user_id, "n": name, "k": kind, "i": (icon or "📦").strip()[:10]}, write=True)


def update_category(user_id, category_id, name, icon):
    """Rename / change icon. Only the user's own custom categories."""
    name = name.strip()
    rows = run("SELECT kind FROM categories WHERE id = :cid AND user_id = :uid",
               {"cid": category_id, "uid": user_id})
    if not rows:
        raise ValueError("Built-in categories can't be renamed.")
    if not name or len(name) > 50:
        raise ValueError("Name must be 1-50 characters.")
    if _name_taken(user_id, rows[0]["kind"], name, exclude_id=category_id):
        raise ValueError(f"A category named '{name}' already exists.")
    return run("UPDATE categories SET name = :n, icon = :i WHERE id = :cid AND user_id = :uid",
               {"n": name, "i": (icon or "📦").strip()[:10], "cid": category_id, "uid": user_id},
               write=True)


def set_archived(user_id, category_id, archived):
    if archived:
        if run("SELECT 1 FROM hidden_categories WHERE user_id = :uid AND category_id = :cid",
               {"uid": user_id, "cid": category_id}):
            return 0
        if not run("SELECT 1 FROM categories WHERE id = :cid AND (user_id IS NULL OR user_id = :uid)",
                   {"cid": category_id, "uid": user_id}):
            raise ValueError("Category not found.")
        return run("INSERT INTO hidden_categories (user_id, category_id) VALUES (:uid, :cid)",
                   {"uid": user_id, "cid": category_id}, write=True)
    return run("DELETE FROM hidden_categories WHERE user_id = :uid AND category_id = :cid",
               {"uid": user_id, "cid": category_id}, write=True)


def delete_category(user_id, category_id):
    """Only custom categories with zero records can be deleted; otherwise archive."""
    used = run("SELECT COUNT(*) AS n FROM transactions WHERE category_id = :cid", {"cid": category_id})[0]["n"]
    if used:
        raise ValueError(f"It has {used} records. Archive it instead.")
    n = run("DELETE FROM categories WHERE id = :cid AND user_id = :uid",
            {"cid": category_id, "uid": user_id}, write=True)
    if not n:
        raise ValueError("Built-in categories can't be deleted (archive them instead).")
    return n


def category_allowed(user_id, category_id, kind):
    rows = run(
        """SELECT 1 FROM categories
           WHERE id = :cid AND kind = :kind AND (user_id IS NULL OR user_id = :uid)""",
        {"cid": category_id, "kind": kind, "uid": user_id},
    )
    return bool(rows)


# ---------------------------------------------------------------- transactions
def add_transaction(user_id, kind, amount, category_id, txn_date, payment_method, tags, note):
    if not category_allowed(user_id, category_id, kind):
        raise ValueError("Invalid category.")
    run(
        """INSERT INTO transactions
               (user_id, kind, amount, category_id, txn_date, payment_method, tags, note)
           VALUES (:uid, :kind, :amt, :cid, :d, :pm, :tags, :note)""",
        {"uid": user_id, "kind": kind, "amt": float(amount), "cid": category_id,
         "d": txn_date.isoformat(), "pm": payment_method, "tags": tags, "note": note},
        write=True,
    )


def list_transactions(user_id, start, end, kind=None, category_ids=None, limit=None):
    sql = """
        SELECT t.id, t.txn_date, t.kind, t.category_id, c.name AS category, c.icon,
               t.amount, t.payment_method, t.tags, t.note
        FROM transactions t
        JOIN categories c ON c.id = t.category_id
        WHERE t.user_id = :uid AND t.txn_date BETWEEN :start AND :end
    """
    params = {"uid": user_id, "start": start.isoformat(), "end": end.isoformat()}
    if kind:
        sql += " AND t.kind = :kind"
        params["kind"] = kind
    if category_ids:
        sql += " AND t.category_id IN :cids"
        params["cids"] = list(category_ids)
    sql += " ORDER BY t.txn_date DESC, t.id DESC"
    if limit:
        sql += f" LIMIT {int(limit)}"
    stmt = text(sql)
    if category_ids:
        stmt = stmt.bindparams(bindparam("cids", expanding=True))
    return run(stmt, params)


def update_transaction(user_id, txn_id, kind, amount, category_id, txn_date, payment_method, tags, note):
    if not category_allowed(user_id, category_id, kind):
        raise ValueError("Invalid category.")
    return run(
        """UPDATE transactions
           SET amount = :amt, category_id = :cid, txn_date = :d, payment_method = :pm,
               tags = :tags, note = :note, updated_at = CURRENT_TIMESTAMP
           WHERE id = :id AND user_id = :uid""",
        {"amt": float(amount), "cid": category_id, "d": txn_date.isoformat(), "pm": payment_method,
         "tags": tags, "note": note, "id": txn_id, "uid": user_id},
        write=True,
    )


def delete_transaction(user_id, txn_id):
    return run(
        "DELETE FROM transactions WHERE id = :id AND user_id = :uid",
        {"id": txn_id, "uid": user_id},
        write=True,
    )


def _month_expr(col):
    """'YYYY-MM' of a date column, in this database's SQL dialect."""
    if get_engine().dialect.name == "sqlite":
        return f"strftime('%Y-%m', {col})"
    return f"to_char({col}, 'YYYY-MM')"


def monthly_summary(user_id, since):
    """Income / expense per month since a date. GROUP BY month."""
    m = _month_expr("txn_date")
    return run(
        f"""SELECT {m} AS month,
                   SUM(CASE WHEN kind = 'income'  THEN amount ELSE 0 END) AS income,
                   SUM(CASE WHEN kind = 'expense' THEN amount ELSE 0 END) AS expense
            FROM transactions
            WHERE user_id = :uid AND txn_date >= :since
            GROUP BY {m}
            ORDER BY month DESC""",
        {"uid": user_id, "since": since.isoformat()},
    )


def category_breakdown(user_id, kind, start, end):
    """Total per category for one type and date range, largest first. GROUP BY category."""
    return run(
        """SELECT c.id, c.name, c.icon, SUM(t.amount) AS total, COUNT(*) AS n
           FROM transactions t
           JOIN categories c ON c.id = t.category_id
           WHERE t.user_id = :uid AND t.kind = :kind
             AND t.txn_date BETWEEN :start AND :end
           GROUP BY c.id, c.name, c.icon
           ORDER BY total DESC""",
        {"uid": user_id, "kind": kind, "start": start.isoformat(), "end": end.isoformat()},
    )


def totals(user_id, start, end):
    """Income / expense totals for a date range (preview of the Phase 2 dashboard)."""
    rows = run(
        """SELECT
               COALESCE(SUM(CASE WHEN kind = 'income'  THEN amount END), 0) AS income,
               COALESCE(SUM(CASE WHEN kind = 'expense' THEN amount END), 0) AS expense
           FROM transactions
           WHERE user_id = :uid AND txn_date BETWEEN :start AND :end""",
        {"uid": user_id, "start": start.isoformat(), "end": end.isoformat()},
    )
    return float(rows[0]["income"]), float(rows[0]["expense"])
