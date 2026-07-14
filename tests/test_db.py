import pathlib
import sys

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

import db


@pytest.fixture
def conn():
    connection = db.connect(":memory:")
    yield connection
    connection.close()


def test_add_and_get_transaction(conn):
    tid = db.add_transaction(conn, amount_minor=1500, category="Yemek", date="2026-07-01", note="ogle yemegi")
    rows = db.get_transactions(conn)
    assert len(rows) == 1
    assert rows[0].id == tid
    assert rows[0].amount_minor == 1500
    assert rows[0].category == "Yemek"
    assert rows[0].date == "2026-07-01"
    assert rows[0].note == "ogle yemegi"
    assert rows[0].type == "gider"


def test_add_transaction_income_type(conn):
    tid = db.add_transaction(conn, amount_minor=250000, category="Maas", date="2026-07-01", note="", type="gelir")
    rows = db.get_transactions(conn)
    assert rows[0].id == tid
    assert rows[0].type == "gelir"


def test_invalid_type_rejected(conn):
    with pytest.raises(ValueError):
        db.add_transaction(conn, amount_minor=100, category="Diger", date="2026-07-01", note="", type="bosluk")


def test_update_transaction(conn):
    tid = db.add_transaction(conn, amount_minor=1000, category="Ulasim", date="2026-07-02", note="")
    db.update_transaction(conn, tid, amount_minor=2000, category="Ulasim", date="2026-07-03", note="taksi", type="gelir")
    rows = db.get_transactions(conn)
    assert len(rows) == 1
    assert rows[0].amount_minor == 2000
    assert rows[0].date == "2026-07-03"
    assert rows[0].note == "taksi"
    assert rows[0].type == "gelir"


def test_delete_transaction(conn):
    tid = db.add_transaction(conn, amount_minor=500, category="Eglence", date="2026-07-05", note="")
    db.delete_transaction(conn, tid)
    assert db.get_transactions(conn) == []


def test_malformed_date_rejected_on_insert(conn):
    with pytest.raises(ValueError):
        db.add_transaction(conn, amount_minor=100, category="Diger", date="2026-13-40", note="")
    assert db.get_transactions(conn) == []


def test_malformed_date_rejected_on_update(conn):
    tid = db.add_transaction(conn, amount_minor=100, category="Diger", date="2026-07-01", note="")
    with pytest.raises(ValueError):
        db.update_transaction(conn, tid, amount_minor=100, category="Diger", date="not-a-date", note="")
    # original row untouched
    rows = db.get_transactions(conn)
    assert rows[0].date == "2026-07-01"


@pytest.mark.parametrize("date_str", ["20260701", "2026-W27-3"])
def test_non_dashed_iso_date_variants_rejected_on_insert(conn, date_str):
    # fromisoformat alone is too lenient about these in Python 3.11+; they must
    # still be rejected since strftime('%Y-%m', date) can't parse them later.
    with pytest.raises(ValueError):
        db.add_transaction(conn, amount_minor=100, category="Diger", date=date_str, note="")
    assert db.get_transactions(conn) == []


@pytest.mark.parametrize("date_str", ["20260701", "2026-W27-3"])
def test_non_dashed_iso_date_variants_rejected_on_update(conn, date_str):
    tid = db.add_transaction(conn, amount_minor=100, category="Diger", date="2026-07-01", note="")
    with pytest.raises(ValueError):
        db.update_transaction(conn, tid, amount_minor=100, category="Diger", date=date_str, note="")
    rows = db.get_transactions(conn)
    assert rows[0].date == "2026-07-01"


def test_non_positive_amount_rejected(conn):
    with pytest.raises(ValueError):
        db.add_transaction(conn, amount_minor=0, category="Diger", date="2026-07-01", note="")
    with pytest.raises(ValueError):
        db.add_transaction(conn, amount_minor=-100, category="Diger", date="2026-07-01", note="")


def test_filter_by_category(conn):
    db.add_transaction(conn, amount_minor=100, category="Yemek", date="2026-07-01", note="")
    db.add_transaction(conn, amount_minor=200, category="Ulasim", date="2026-07-02", note="")
    rows = db.get_transactions(conn, category="Yemek")
    assert len(rows) == 1
    assert rows[0].category == "Yemek"


def test_filter_by_type(conn):
    db.add_transaction(conn, amount_minor=100, category="Yemek", date="2026-07-01", note="", type="gider")
    db.add_transaction(conn, amount_minor=250000, category="Maas", date="2026-07-01", note="", type="gelir")
    rows = db.get_transactions(conn, type="gelir")
    assert len(rows) == 1
    assert rows[0].category == "Maas"


def test_filter_by_date_range(conn):
    db.add_transaction(conn, amount_minor=100, category="Yemek", date="2026-07-01", note="")
    db.add_transaction(conn, amount_minor=200, category="Yemek", date="2026-07-15", note="")
    db.add_transaction(conn, amount_minor=300, category="Yemek", date="2026-08-01", note="")
    rows = db.get_transactions(conn, date_from="2026-07-01", date_to="2026-07-31")
    assert len(rows) == 2
    assert {r.amount_minor for r in rows} == {100, 200}


def test_filter_by_search_text(conn):
    db.add_transaction(conn, amount_minor=100, category="Yemek", date="2026-07-01", note="market alisverisi")
    db.add_transaction(conn, amount_minor=200, category="Yemek", date="2026-07-02", note="restoran")
    rows = db.get_transactions(conn, search_text="market")
    assert len(rows) == 1
    assert rows[0].note == "market alisverisi"


def test_budget_set_and_get(conn):
    assert db.get_budget(conn) is None
    db.set_budget(conn, 500000)
    assert db.get_budget(conn) == 500000
    db.set_budget(conn, 600000)
    assert db.get_budget(conn) == 600000


def test_is_over_budget_boundary():
    assert db.is_over_budget(spent_minor=1000, budget_minor=1000) is False
    assert db.is_over_budget(spent_minor=1001, budget_minor=1000) is True
    assert db.is_over_budget(spent_minor=500, budget_minor=1000) is False
    assert db.is_over_budget(spent_minor=500, budget_minor=None) is False
