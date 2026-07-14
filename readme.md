# Harcama & Bütçe Takip

A desktop personal finance / budget tracker built with Python and PySide6 (Qt).
Record income (`gelir`) and expense (`gider`) transactions, filter and search
them, set a monthly budget with overspend warnings, and view spending via
embedded matplotlib charts. Data is stored locally in a SQLite database
(`harcama.db`), created automatically next to `main.py` on first run.

## Tech stack

- Python 3.14
- [PySide6](https://doc.qt.io/qtforpython/) 6.11.1 — Qt GUI
- [matplotlib](https://matplotlib.org/) 3.11.0 — embedded charts (`backend_qtagg`)
- SQLite via the stdlib `sqlite3` module — no ORM
- [pytest](https://docs.pytest.org/) — test suite

## Setup

```bash
pip install -r requirements.txt
```

## Running the app

```bash
python main.py
```

This opens (or creates) `harcama.db` in the project directory and launches
the main window.

## Running tests

```bash
pytest tests/ -v
```

30 tests cover CRUD operations, strict date validation, budget boundary
logic, mixed income/expense aggregation, filtering, and CSV round-trip /
atomicity.

## Features

- Add, edit, and delete transactions (amount, category, date, note, type).
- Transaction type: `gelir` (income) or `gider` (expense).
- Filter/search by category, date range, free-text note search, and type.
- Set a monthly budget; see current-month spend vs. budget with an overspend
  warning, and the net balance (gelir − gider) for the month.
- Charts (matplotlib, embedded in the Qt window):
  - Current month's expense breakdown by category (bar chart).
  - Monthly totals over time, income and expense as two series (line chart).
- CSV export and import. Import is all-or-nothing: if any row fails
  validation, nothing from that file is persisted.

### Out of scope (intentionally)

Recurring transactions, multiple accounts, and savings goals are not
supported — these were explicitly excluded from this project's scope.

## Data storage notes

- Amounts are stored as positive integers in minor units (kuruş = TL × 100)
  to avoid floating-point rounding drift; the sign is implied by `type`.
- Dates are stored as strict ISO-8601 text (`YYYY-MM-DD`) so that
  lexicographic ordering matches chronological ordering and
  `strftime('%Y-%m', date)` grouping works correctly. Other ISO date
  variants (e.g. `20260701`, week-dates) are rejected at insert/update time.
