"""CSV export/import for transactions.

Columns: amount_minor, category, date, note, type. Using minor units (not
display TL strings) keeps export/import a lossless round trip.
"""

import csv
import sqlite3

import db

FIELDNAMES = ["amount_minor", "category", "date", "note", "type"]


def export_csv(conn: sqlite3.Connection, path: str) -> None:
    transactions = db.get_transactions(conn)
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        writer.writeheader()
        for t in transactions:
            writer.writerow(
                {
                    "amount_minor": t.amount_minor,
                    "category": t.category,
                    "date": t.date,
                    "note": t.note,
                    "type": t.type,
                }
            )


def import_csv(conn: sqlite3.Connection, path: str) -> int:
    """Insert every row from the CSV as a new transaction. Returns count imported.

    Missing or invalid 'type' values default to 'gider' (expense), matching
    the app's default transaction type.

    The whole file is imported as a single transaction: if any row fails
    validation, nothing from this import is persisted (rollback) and the
    error identifies which data row (1-based, header excluded) failed.
    """
    count = 0
    with open(path, "r", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row_num, row in enumerate(reader, start=1):
            try:
                row_type = (row.get("type") or "").strip()
                if row_type not in db.VALID_TYPES:
                    row_type = "gider"
                db.add_transaction(
                    conn,
                    amount_minor=int(row["amount_minor"]),
                    category=row["category"],
                    date=row["date"],
                    note=row.get("note", ""),
                    type=row_type,
                    commit=False,
                )
            except (ValueError, KeyError) as exc:
                conn.rollback()
                raise ValueError(f"CSV import failed at row {row_num} ({row}): {exc}") from exc
            count += 1
    conn.commit()
    return count
