import pathlib
import sys

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

import db


@pytest.fixture
def conn():
    connection = db.connect(":memory:")
    db.add_transaction(connection, amount_minor=1000, category="Yemek", date="2026-06-01", note="")
    db.add_transaction(connection, amount_minor=2000, category="Yemek", date="2026-06-15", note="")
    db.add_transaction(connection, amount_minor=500, category="Ulasim", date="2026-06-20", note="")
    db.add_transaction(connection, amount_minor=3000, category="Yemek", date="2026-07-05", note="")
    db.add_transaction(connection, amount_minor=1500, category="Eglence", date="2026-07-10", note="")
    yield connection
    connection.close()


def test_category_totals_for_month(conn):
    june = db.category_totals_for_month(conn, "2026-06")
    assert june == {"Yemek": 3000, "Ulasim": 500}
    july = db.category_totals_for_month(conn, "2026-07")
    assert july == {"Yemek": 3000, "Eglence": 1500}
    empty = db.category_totals_for_month(conn, "2026-01")
    assert empty == {}


def test_monthly_totals(conn):
    totals = db.monthly_totals(conn)
    assert totals == {
        "2026-06": {"gelir": 0, "gider": 3500},
        "2026-07": {"gelir": 0, "gider": 4500},
    }


def test_get_month_spending(conn):
    assert db.get_month_spending(conn, "2026-06") == 3500
    assert db.get_month_spending(conn, "2026-07") == 4500
    assert db.get_month_spending(conn, "2026-01") == 0


def test_monthly_totals_mixed_income_expense(conn):
    db.add_transaction(conn, amount_minor=100000, category="Maas", date="2026-07-15", note="", type="gelir")
    totals = db.monthly_totals(conn)
    assert totals["2026-07"] == {"gelir": 100000, "gider": 4500}
    assert totals["2026-06"] == {"gelir": 0, "gider": 3500}


def test_monthly_net(conn):
    db.add_transaction(conn, amount_minor=100000, category="Maas", date="2026-07-15", note="", type="gelir")
    assert db.monthly_net(conn, "2026-07") == 100000 - 4500
    assert db.monthly_net(conn, "2026-06") == -3500
    assert db.monthly_net(conn, "2026-01") == 0


def test_get_month_spending_ignores_income(conn):
    db.add_transaction(conn, amount_minor=100000, category="Maas", date="2026-07-15", note="", type="gelir")
    assert db.get_month_spending(conn, "2026-07") == 4500


def test_is_over_budget_ignores_income_in_same_month(conn):
    db.add_transaction(conn, amount_minor=100000, category="Maas", date="2026-07-15", note="", type="gelir")
    spent = db.get_month_spending(conn, "2026-07")
    assert db.is_over_budget(spent, budget_minor=4500) is False
    assert db.is_over_budget(spent, budget_minor=4000) is True


def test_category_totals_for_month_type_filter(conn):
    db.add_transaction(conn, amount_minor=100000, category="Maas", date="2026-07-15", note="", type="gelir")
    gider_only = db.category_totals_for_month(conn, "2026-07", type="gider")
    assert gider_only == {"Yemek": 3000, "Eglence": 1500}
    gelir_only = db.category_totals_for_month(conn, "2026-07", type="gelir")
    assert gelir_only == {"Maas": 100000}
    all_types = db.category_totals_for_month(conn, "2026-07")
    assert all_types == {"Yemek": 3000, "Eglence": 1500, "Maas": 100000}
