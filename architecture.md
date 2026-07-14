# Architecture

## Entry point

`main.py` creates the `QApplication`, opens/creates `harcama.db` (SQLite
file next to the script) via `db.connect()`, and shows `MainWindow`.

## Module layout

```
main.py                    entry point
models.py                  Transaction dataclass (shared data shape)
db.py                       SQLite schema, validation, CRUD, aggregation
csv_io.py                  CSV export/import (built on db.py)
ui/main_window.py          main window: table, filters, budget panel, charts
ui/transaction_dialog.py   add/edit transaction modal
tests/                     pytest suite (db, aggregation, csv_io)
```

Dependencies flow one direction: `ui/` depends on `db.py` and `csv_io.py`;
`csv_io.py` depends on `db.py`; both depend on `models.py`. The UI never
talks to SQLite directly — all reads/writes go through `db.py`'s functions,
so validation (date format, positive amounts, transaction type) is enforced
in one place regardless of caller (UI, CSV import, or tests).

## Data layer (`db.py`)

SQLite via stdlib `sqlite3`, no ORM. Two tables:

- `transactions(id, amount_minor, category, date, note, type)` — `type` is
  constrained to `'gelir'` (income) or `'gider'` (expense) via a `CHECK`
  constraint.
- `settings(key, value)` — currently holds a single row for the monthly
  budget (`monthly_budget_minor`).

Key design decisions:

- **Amounts** are stored as positive integer minor units (kuruş = TL × 100)
  to avoid floating-point rounding drift in sums. Sign is implied by `type`,
  not by the amount.
- **Dates** are stored as strict `YYYY-MM-DD` text and validated with a
  regex before being passed to `date.fromisoformat` — `fromisoformat` alone
  accepts other ISO-8601 variants (e.g. `20260701`, `2026-W27-3`) that would
  silently break `strftime('%Y-%m', date)` grouping and lexicographic
  date-range filtering. This validation is exercised directly by
  `tests/test_db.py`.
- **Aggregation** (`category_totals_for_month`, `monthly_totals`,
  `monthly_net`, `get_month_spending`) is done in SQL via `strftime` and
  `GROUP BY`/`SUM`, not in Python, so the UI just renders whatever the query
  returns.

## CSV import/export (`csv_io.py`)

Round-trips the same columns as the `transactions` table (minor units, not
display strings, to stay lossless). Import is all-or-nothing: each row is
inserted with `commit=False`; if any row fails validation, the whole
transaction is rolled back and the error names the offending row.

## UI (`ui/`)

- `MainWindow` builds four regions: a filter bar (category/type/date
  range/note search), a transaction table, a budget panel (set budget,
  current-month spend vs. budget with overspend warning, net balance), and
  a chart panel.
- `TransactionDialog` is a modal `QDialog` used for both add and edit;
  callers read the result via `get_transaction()`.
- Charts are embedded matplotlib figures using
  `matplotlib.backends.backend_qtagg.FigureCanvasQTAgg` with an explicit
  `Figure` object (not the `pyplot` global state API), so multiple windows/
  redraws don't leak global matplotlib state. Each refresh calls
  `ax.clear()` then `canvas.draw_idle()`. Two chart modes share one canvas:
  current-month category breakdown (bar) and monthly gelir/gider totals
  over time (line, two series).

## Tests (`tests/`)

Pytest, using in-memory SQLite (`db.connect(":memory:")`) for isolation —
no test touches the real `harcama.db`. Split by concern:
`test_db.py` (CRUD + validation), `test_aggregation.py` (grouping/totals
correctness, including mixed income/expense), `test_csv_io.py` (export/
import round-trip and rollback-on-bad-row behavior).
