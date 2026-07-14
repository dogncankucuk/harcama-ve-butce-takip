"""SQLite data layer: schema, CRUD, filtering and aggregation queries.

Amounts are stored as integer minor units (kurus = TL * 100) to avoid
floating point rounding drift. Dates are stored as ISO-8601 TEXT
("YYYY-MM-DD") so lexicographic ordering equals chronological ordering.
"""

import re
import sqlite3
from datetime import date as _date

from models import Transaction

_SCHEMA = """
CREATE TABLE IF NOT EXISTS transactions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    amount_minor INTEGER NOT NULL,
    category TEXT NOT NULL,
    date TEXT NOT NULL,
    note TEXT NOT NULL DEFAULT '',
    type TEXT NOT NULL DEFAULT 'gider' CHECK (type IN ('gelir', 'gider'))
);

CREATE TABLE IF NOT EXISTS settings (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
"""

BUDGET_KEY = "monthly_budget_minor"
VALID_TYPES = {"gelir", "gider"}


def connect(db_path: str) -> sqlite3.Connection:
    """Open a connection and make sure the schema exists."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.executescript(_SCHEMA)
    conn.commit()
    return conn


def _validate_date(date_str: str) -> str:
    """Raise ValueError if date_str is not a strict 'YYYY-MM-DD' calendar date.

    date.fromisoformat alone is too lenient (accepts "20260701",
    "2026-W27-3", etc.) which breaks strftime('%Y-%m', date) aggregation
    and lexicographic date_from/date_to filtering downstream.
    """
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", date_str):
        raise ValueError(f"date must be in 'YYYY-MM-DD' format, got {date_str!r}")
    _date.fromisoformat(date_str)
    return date_str


def _validate_amount(amount_minor: int) -> int:
    if amount_minor <= 0:
        raise ValueError("amount_minor must be a positive integer (kurus)")
    return amount_minor


def _validate_type(type: str) -> str:
    if type not in VALID_TYPES:
        raise ValueError("type must be 'gelir' or 'gider'")
    return type


def add_transaction(
    conn: sqlite3.Connection,
    amount_minor: int,
    category: str,
    date: str,
    note: str = "",
    type: str = "gider",
    commit: bool = True,
) -> int:
    _validate_amount(amount_minor)
    _validate_date(date)
    _validate_type(type)
    if not category:
        raise ValueError("category must not be empty")
    cur = conn.execute(
        "INSERT INTO transactions (amount_minor, category, date, note, type) VALUES (?, ?, ?, ?, ?)",
        (amount_minor, category, date, note, type),
    )
    if commit:
        conn.commit()
    return cur.lastrowid


def update_transaction(
    conn: sqlite3.Connection,
    transaction_id: int,
    amount_minor: int,
    category: str,
    date: str,
    note: str = "",
    type: str = "gider",
) -> None:
    _validate_amount(amount_minor)
    _validate_date(date)
    _validate_type(type)
    if not category:
        raise ValueError("category must not be empty")
    conn.execute(
        "UPDATE transactions SET amount_minor = ?, category = ?, date = ?, note = ?, type = ? WHERE id = ?",
        (amount_minor, category, date, note, type, transaction_id),
    )
    conn.commit()


def delete_transaction(conn: sqlite3.Connection, transaction_id: int) -> None:
    conn.execute("DELETE FROM transactions WHERE id = ?", (transaction_id,))
    conn.commit()


def get_transactions(
    conn: sqlite3.Connection,
    category: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    search_text: str | None = None,
    type: str | None = None,
) -> list[Transaction]:
    """Return transactions matching the given filters, newest date first."""
    query = "SELECT id, amount_minor, category, date, note, type FROM transactions WHERE 1=1"
    params: list = []
    if category:
        query += " AND category = ?"
        params.append(category)
    if date_from:
        query += " AND date >= ?"
        params.append(date_from)
    if date_to:
        query += " AND date <= ?"
        params.append(date_to)
    if search_text:
        query += " AND note LIKE ?"
        params.append(f"%{search_text}%")
    if type:
        query += " AND type = ?"
        params.append(type)
    query += " ORDER BY date DESC, id DESC"
    rows = conn.execute(query, params).fetchall()
    return [
        Transaction(
            id=r["id"],
            amount_minor=r["amount_minor"],
            category=r["category"],
            date=r["date"],
            note=r["note"],
            type=r["type"],
        )
        for r in rows
    ]


def get_categories(conn: sqlite3.Connection) -> list[str]:
    rows = conn.execute("SELECT DISTINCT category FROM transactions ORDER BY category").fetchall()
    return [r["category"] for r in rows]


def category_totals_for_month(conn: sqlite3.Connection, month: str, type: str | None = None) -> dict[str, int]:
    """Category -> total_minor for a single 'YYYY-MM' month, optionally filtered by type."""
    query = "SELECT category, SUM(amount_minor) AS total FROM transactions WHERE strftime('%Y-%m', date) = ?"
    params: list = [month]
    if type:
        query += " AND type = ?"
        params.append(type)
    query += " GROUP BY category ORDER BY category"
    rows = conn.execute(query, params).fetchall()
    return {r["category"]: r["total"] for r in rows}


def monthly_totals(conn: sqlite3.Connection) -> dict[str, dict[str, int]]:
    """month ('YYYY-MM') -> {'gelir': total_minor, 'gider': total_minor}, only for months with data."""
    rows = conn.execute(
        """
        SELECT strftime('%Y-%m', date) AS month, type, SUM(amount_minor) AS total
        FROM transactions
        GROUP BY month, type
        ORDER BY month
        """
    ).fetchall()
    result: dict[str, dict[str, int]] = {}
    for r in rows:
        result.setdefault(r["month"], {"gelir": 0, "gider": 0})[r["type"]] = r["total"]
    return result


def monthly_net(conn: sqlite3.Connection, month: str) -> int:
    """Net balance (gelir - gider) in minor units for a given 'YYYY-MM' month."""
    row = conn.execute(
        """
        SELECT
            COALESCE(SUM(CASE WHEN type = 'gelir' THEN amount_minor ELSE 0 END), 0) AS income,
            COALESCE(SUM(CASE WHEN type = 'gider' THEN amount_minor ELSE 0 END), 0) AS expense
        FROM transactions
        WHERE strftime('%Y-%m', date) = ?
        """,
        (month,),
    ).fetchone()
    return row["income"] - row["expense"]


def get_month_spending(conn: sqlite3.Connection, month: str) -> int:
    """Total minor units spent (type='gider' only) in a given 'YYYY-MM' month."""
    row = conn.execute(
        "SELECT SUM(amount_minor) AS total FROM transactions WHERE strftime('%Y-%m', date) = ? AND type = 'gider'",
        (month,),
    ).fetchone()
    return row["total"] or 0


def get_budget(conn: sqlite3.Connection) -> int | None:
    row = conn.execute("SELECT value FROM settings WHERE key = ?", (BUDGET_KEY,)).fetchone()
    return int(row["value"]) if row else None


def set_budget(conn: sqlite3.Connection, amount_minor: int) -> None:
    _validate_amount(amount_minor)
    conn.execute(
        "INSERT INTO settings (key, value) VALUES (?, ?) "
        "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
        (BUDGET_KEY, str(amount_minor)),
    )
    conn.commit()


def is_over_budget(spent_minor: int, budget_minor: int | None) -> bool:
    """Pure boundary check: spending strictly greater than the budget."""
    if budget_minor is None:
        return False
    return spent_minor > budget_minor
