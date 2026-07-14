import pathlib
import sys
import tempfile

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

import csv_io
import db


@pytest.fixture
def conn():
    connection = db.connect(":memory:")
    yield connection
    connection.close()


def test_export_import_round_trip(conn, tmp_path):
    db.add_transaction(conn, amount_minor=1234, category="Yemek", date="2026-07-01", note="ogle yemegi")
    db.add_transaction(conn, amount_minor=5000, category="Ulasim", date="2026-07-02", note="")
    db.add_transaction(conn, amount_minor=999, category="Eglence", date="2026-07-03", note="sinema, bilet")
    db.add_transaction(conn, amount_minor=250000, category="Maas", date="2026-07-04", note="", type="gelir")

    csv_path = tmp_path / "export.csv"
    csv_io.export_csv(conn, str(csv_path))

    conn2 = db.connect(":memory:")
    imported_count = csv_io.import_csv(conn2, str(csv_path))
    assert imported_count == 4

    original = sorted(
        (t.amount_minor, t.category, t.date, t.note, t.type) for t in db.get_transactions(conn)
    )
    reimported = sorted(
        (t.amount_minor, t.category, t.date, t.note, t.type) for t in db.get_transactions(conn2)
    )
    assert original == reimported


def test_export_empty(conn, tmp_path):
    csv_path = tmp_path / "empty.csv"
    csv_io.export_csv(conn, str(csv_path))
    conn2 = db.connect(":memory:")
    count = csv_io.import_csv(conn2, str(csv_path))
    assert count == 0
    assert db.get_transactions(conn2) == []


def test_import_missing_or_invalid_type_defaults_to_gider(conn, tmp_path):
    csv_path = tmp_path / "no_type.csv"
    csv_path.write_text(
        "amount_minor,category,date,note\n"
        "1000,Yemek,2026-07-01,\n",
        encoding="utf-8",
    )
    count = csv_io.import_csv(conn, str(csv_path))
    assert count == 1
    assert db.get_transactions(conn)[0].type == "gider"

    csv_path2 = tmp_path / "bad_type.csv"
    csv_path2.write_text(
        "amount_minor,category,date,note,type\n"
        "1000,Yemek,2026-07-01,,not-a-type\n",
        encoding="utf-8",
    )
    conn2 = db.connect(":memory:")
    count2 = csv_io.import_csv(conn2, str(csv_path2))
    assert count2 == 1
    assert db.get_transactions(conn2)[0].type == "gider"


def test_import_csv_rolls_back_all_rows_on_bad_row(conn, tmp_path):
    csv_path = tmp_path / "bad_row.csv"
    csv_path.write_text(
        "amount_minor,category,date,note,type\n"
        "1000,Yemek,2026-07-01,,gider\n"
        "2000,Ulasim,not-a-date,,gider\n"
        "3000,Eglence,2026-07-03,,gider\n",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="row 2"):
        csv_io.import_csv(conn, str(csv_path))
    # all-or-nothing: no rows from the failed import were persisted
    assert db.get_transactions(conn) == []
