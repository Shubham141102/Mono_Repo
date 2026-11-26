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
    ("Food & Dining", "expense", "🍔"), ("Bills & Utilities", "expense", "💡"),
    ("Transportation", "expense", "🚗"), ("Shopping", "expense", "🛍️"),
    ("Entertainment", "expense", "🎬"), ("Health & Medical", "expense", "🏥"),
    ("Education", "expense", "📚"), ("Rent & Housing", "expense", "🏠"),
    ("Travel", "expense", "✈️"), ("Personal Care", "expense", "💇"),
    ("Other", "expense", "📦"),
    ("Salary", "income", "💼"), ("Freelancing", "income", "💻"),
    ("Business Income", "income", "🏢"), ("Investment Returns", "income", "📈"),
    ("Interest", "income", "🏦"), ("Rental Income", "income", "🏠"),
    ("Gifts", "income", "🎁"), ("Cashback", "income", "💳"),
    ("Bonus", "income", "🏆"), ("Other Income", "income", "💰"),
]
# older built-in names -> new names (migrated in place, transactions keep their category)
DEFAULT_RENAMES = [
    ("expense", "Rent", "Rent & Housing"), ("expense", "Transport", "Transportation"),
    ("expense", "Health", "Health & Medical"), ("income", "Freelance", "Freelancing"),
    ("income", "Investments", "Investment Returns"), ("income", "Gift", "Gifts"),
    ("income", "Other", "Other Income"),
]
# older built-ins folded into another (their transactions move over)
DEFAULT_MERGES = [("expense", "Groceries", "Food & Dining")]

# 8 colour-blind-safe category colours (validated categorical palette)
COLORS = {
    "Blue": "#2a78d6", "Orange": "#eb6834", "Aqua": "#1baf7a", "Yellow": "#eda100",
    "Magenta": "#e87ba4", "Green": "#008300", "Violet": "#6250d6", "Red": "#e34948",
}
SORTS = {
    "Newest first": "t.txn_date DESC, t.id DESC",
    "Oldest first": "t.txn_date ASC, t.id ASC",
    "Amount: high to low": "t.amount DESC, t.id DESC",
    "Amount: low to high": "t.amount ASC, t.id ASC",
}

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

category_colors = Table(
    # per-user colour choice, works for built-in and custom categories
    "category_colors", metadata,
    Column("user_id", Integer, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
    Column("category_id", Integer, ForeignKey("categories.id", ondelete="CASCADE"), primary_key=True),
    Column("color", String(7), nullable=False),
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
    """Create tables (if missing) and bring built-in categories up to date. Safe to run repeatedly."""
    engine = get_engine()
    metadata.create_all(engine)
    icons = {(k, n): i for n, k, i in DEFAULT_CATEGORIES}
    with engine.begin() as conn:
        def builtin(kind, name):
            return conn.execute(
                text("SELECT id FROM categories WHERE user_id IS NULL AND kind = :k AND name = :n"),
                {"k": kind, "n": name}).scalar()

        for kind, old, new in DEFAULT_RENAMES:
            oid = builtin(kind, old)
            if oid and not builtin(kind, new):
                conn.execute(text("UPDATE categories SET name = :n, icon = :i WHERE id = :id"),
                             {"n": new, "i": icons[(kind, new)], "id": oid})
        for kind, old, into in DEFAULT_MERGES:
            oid, tid = builtin(kind, old), builtin(kind, into)
            if oid and tid:
                conn.execute(text("UPDATE transactions SET category_id = :t WHERE category_id = :o"), {"t": tid, "o": oid})
                conn.execute(text("DELETE FROM hidden_categories WHERE category_id = :o"), {"o": oid})
                conn.execute(text("DELETE FROM category_colors WHERE category_id = :o"), {"o": oid})
                conn.execute(text("DELETE FROM categories WHERE id = :o"), {"o": oid})
        for name, kind, icon in DEFAULT_CATEGORIES:
            if not builtin(kind, name):
                conn.execute(text("INSERT INTO categories (user_id, name, kind, icon) VALUES (NULL, :n, :k, :i)"),
                             {"n": name, "k": kind, "i": icon})
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
        SELECT c.id, c.name, c.kind, c.icon, cc.color,
               CASE WHEN c.user_id IS NULL THEN 0 ELSE 1 END AS is_custom,
               CASE WHEN h.category_id IS NULL THEN 0 ELSE 1 END AS archived,
               (SELECT COUNT(*) FROM transactions t
                 WHERE t.category_id = c.id AND t.user_id = :uid) AS records
        FROM categories c
        LEFT JOIN hidden_categories h ON h.category_id = c.id AND h.user_id = :uid
        LEFT JOIN category_colors cc ON cc.category_id = c.id AND cc.user_id = :uid
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


def set_color(user_id, category_id, color):
    """color = one of COLORS' hex values, or None for automatic."""
    if color is not None and color not in COLORS.values():
        raise ValueError("Pick one of the preset colours.")
    if not run("SELECT 1 FROM categories WHERE id = :cid AND (user_id IS NULL OR user_id = :uid)",
               {"cid": category_id, "uid": user_id}):
        raise ValueError("Category not found.")
    with get_engine().begin() as conn:
        conn.execute(text("DELETE FROM category_colors WHERE user_id = :uid AND category_id = :cid"),
                     {"uid": user_id, "cid": category_id})
        if color:
            conn.execute(text("INSERT INTO category_colors (user_id, category_id, color) VALUES (:uid, :cid, :c)"),
                         {"uid": user_id, "cid": category_id, "c": color})


def reassign_and_delete(user_id, from_id, to_id):
    """Move all of the user's transactions from a custom category to another of the same type, then delete it."""
    src = run("SELECT kind FROM categories WHERE id = :f AND user_id = :uid", {"f": from_id, "uid": user_id})
    if not src:
        raise ValueError("Built-in categories can't be deleted (archive them instead).")
    if to_id == from_id or not category_allowed(user_id, to_id, src[0]["kind"]):
        raise ValueError("Pick a different category of the same type.")
    with get_engine().begin() as conn:  # one transaction: both happen or neither
        moved = conn.execute(
            text("""UPDATE transactions SET category_id = :t, updated_at = CURRENT_TIMESTAMP
                    WHERE category_id = :f AND user_id = :uid"""),
            {"t": to_id, "f": from_id, "uid": user_id}).rowcount
        conn.execute(text("DELETE FROM categories WHERE id = :f AND user_id = :uid"), {"f": from_id, "uid": user_id})
    return moved


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


def _txn_where(user_id, start, end, kind, category_ids, payment_methods, search):
    """Shared WHERE clause for listing and counting. Always scoped to the user."""
    where = "t.user_id = :uid AND t.txn_date BETWEEN :start AND :end"
    params = {"uid": user_id, "start": start.isoformat(), "end": end.isoformat()}
    expanding = []
    if kind:
        where += " AND t.kind = :kind"
        params["kind"] = kind
    if category_ids:
        where += " AND t.category_id IN :cids"
        params["cids"] = list(category_ids)
        expanding.append("cids")
    if payment_methods:
        where += " AND t.payment_method IN :pms"
        params["pms"] = list(payment_methods)
        expanding.append("pms")
    if search and search.strip():
        where += " AND (LOWER(t.note) LIKE :q OR LOWER(t.tags) LIKE :q OR LOWER(c.name) LIKE :q)"
        params["q"] = f"%{search.strip().lower()}%"
    return where, params, expanding


def _stmt(sql, expanding):
    stmt = text(sql)
    if expanding:
        stmt = stmt.bindparams(*[bindparam(n, expanding=True) for n in expanding])
    return stmt


def list_transactions(user_id, start, end, kind=None, category_ids=None, limit=None, *,
                      payment_methods=None, search="", sort="Newest first", offset=0):
    where, params, expanding = _txn_where(user_id, start, end, kind, category_ids, payment_methods, search)
    sql = f"""
        SELECT t.id, t.txn_date, t.kind, t.category_id, c.name AS category, c.icon,
               t.amount, t.payment_method, t.tags, t.note
        FROM transactions t
        JOIN categories c ON c.id = t.category_id
        WHERE {where}
        ORDER BY {SORTS.get(sort, SORTS['Newest first'])}
    """
    if limit:
        sql += f" LIMIT {int(limit)} OFFSET {int(offset)}"
    return run(_stmt(sql, expanding), params)


def count_transactions(user_id, start, end, kind=None, category_ids=None, *, payment_methods=None, search=""):
    where, params, expanding = _txn_where(user_id, start, end, kind, category_ids, payment_methods, search)
    sql = f"""SELECT COUNT(*) AS n,
                     COALESCE(SUM(CASE WHEN t.kind = 'income'  THEN t.amount END), 0) AS income,
                     COALESCE(SUM(CASE WHEN t.kind = 'expense' THEN t.amount END), 0) AS expense
              FROM transactions t JOIN categories c ON c.id = t.category_id
              WHERE {where}"""
    r = run(_stmt(sql, expanding), params)[0]
    return int(r["n"]), float(r["income"]), float(r["expense"])


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
        """SELECT c.id, c.name, c.icon, cc.color, SUM(t.amount) AS total, COUNT(*) AS n
           FROM transactions t
           JOIN categories c ON c.id = t.category_id
           LEFT JOIN category_colors cc ON cc.category_id = c.id AND cc.user_id = :uid
           WHERE t.user_id = :uid AND t.kind = :kind
             AND t.txn_date BETWEEN :start AND :end
           GROUP BY c.id, c.name, c.icon, cc.color
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
