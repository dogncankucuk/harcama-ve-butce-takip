"""Simple data structures used across the app."""

from dataclasses import dataclass


@dataclass
class Transaction:
    """A single expense/income record.

    amount_minor: integer amount in kurus (TL * 100). Always positive; the
    sign is implied by `type` instead ("gelir" = income, "gider" = expense).
    date: ISO-8601 string "YYYY-MM-DD".
    type: "gelir" or "gider".
    """

    id: int | None
    amount_minor: int
    category: str
    date: str
    note: str
    type: str
