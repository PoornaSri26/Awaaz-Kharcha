"""Edge cases for partial khata payments, backup restore and money formatting."""

from __future__ import annotations

import json

import pandas as pd
import pytest

from awaaz import insights
from awaaz.parser import parse_expenses
from awaaz.store import Store


def make_store(tmp_path) -> Store:
    return Store(tmp_path / "edge.db", migrate_legacy=False)


def add_loan(store: Store, amount: float = 500.0) -> int:
    ids = store.add_udhar(
        [{"date": "2026-11-01", "person": "Ravi", "amount": amount, "type": "Lent (Diya)"}]
    )
    return ids[0]


# ---------------- khata payments ----------------

def test_partial_payment_keeps_the_balance_pending(tmp_path):
    store = make_store(tmp_path)
    loan_id = add_loan(store)

    result = store.record_payment(loan_id, 200)

    assert result == {"paid": 200.0, "remaining": 300.0, "status": "Pending"}
    row = store.udhar().iloc[0]
    assert row["remaining"] == 300.0
    assert len(store.pending_udhar()) == 1


def test_payment_cannot_exceed_the_loan_or_go_negative(tmp_path):
    store = make_store(tmp_path)
    loan_id = add_loan(store)

    assert store.record_payment(loan_id, 9999)["status"] == "Settled"
    assert store.udhar().iloc[0]["paid"] == 500.0

    store.set_udhar_status([loan_id], "Pending")
    assert store.record_payment(loan_id, -50)["paid"] == 0.0


def test_settling_and_reopening_resets_or_clears_paid(tmp_path):
    store = make_store(tmp_path)
    loan_id = add_loan(store)
    store.record_payment(loan_id, 200)

    store.set_udhar_status([loan_id], "Settled")
    assert store.udhar().iloc[0]["paid"] == 500.0

    store.set_udhar_status([loan_id], "Pending")
    assert store.udhar().iloc[0]["paid"] == 0.0
    assert store.udhar().iloc[0]["remaining"] == 500.0


def test_shrinking_an_entry_clamps_what_was_paid(tmp_path):
    store = make_store(tmp_path)
    loan_id = add_loan(store)
    store.set_udhar_status([loan_id], "Settled")

    store.update_udhar(loan_id, amount=100)

    row = store.udhar().iloc[0]
    assert row["amount"] == 100.0
    assert row["paid"] == 100.0  # never more paid than owed
    assert row["status"] == "Settled"


def test_editing_a_name_and_ignoring_blank_input(tmp_path):
    store = make_store(tmp_path)
    loan_id = add_loan(store)

    store.update_udhar(loan_id, person="  Ravi Kumar ", type="Borrowed (Liya)")
    store.update_udhar(loan_id, person="   ")

    row = store.udhar().iloc[0]
    assert row["person"] == "Ravi Kumar"
    assert row["type"] == "Borrowed (Liya)"


def test_partial_balance_drives_the_answer(tmp_path):
    store = make_store(tmp_path)
    loan_id = add_loan(store)
    store.record_payment(loan_id, 200)

    answer = insights.answer_query("how much udhar is pending?", store.expenses(), store.udhar())
    assert "₹300" in answer

    per_person = insights.answer_query("ravi ko kitna udhar dena hai?", store.expenses(), store.udhar())
    assert "₹300" in per_person


def test_answer_still_works_for_frames_without_the_new_columns(tmp_path):
    # Older callers pass a frame with only amount/status.
    khata = pd.DataFrame(
        [{"date": "2026-11-05", "person": "Ravi", "amount": 500.0, "type": "Lent (Diya)", "status": "Pending"}]
    )
    empty = pd.DataFrame(columns=["id", "date", "item", "amount", "category"])
    assert "₹500" in insights.answer_query("how much udhar pending?", empty, khata)


# ---------------- backup restore ----------------

def test_backup_round_trip_preserves_rows_and_payments(tmp_path):
    store = make_store(tmp_path)
    store.add_expense("Chai", 20.5, category="Food", date="2026-11-01")
    loan_id = add_loan(store)
    store.record_payment(loan_id, 200)
    store.set_budget(9000)
    backup = store.export_json()

    store.clear_all()
    assert store.counts() == (0, 0)

    restored = store.restore_json(backup)

    assert restored == (1, 1)
    assert store.counts() == (1, 1)
    assert store.get_budget() == 9000
    row = store.udhar().iloc[0]
    assert row["paid"] == 200.0 and row["remaining"] == 300.0


def test_preview_describes_a_backup_without_writing(tmp_path):
    store = make_store(tmp_path)
    store.add_expense("Chai", 20, category="Food", date="2026-11-01")
    backup = store.export_json()

    preview = store.backup_preview(backup)

    assert preview["expenses"] == 1
    assert preview["first"] == "2026-11-01"
    assert store.counts() == (1, 0)  # unchanged


@pytest.mark.parametrize("payload", ["not json", "{}", "[]", '{"expenses": []}', '{"expenses": "x"}'])
def test_bad_backups_are_rejected_without_touching_data(tmp_path, payload):
    store = make_store(tmp_path)
    store.add_expense("Chai", 20, category="Food")

    with pytest.raises(ValueError):
        store.restore_json(payload)

    assert store.counts() == (1, 0)


def test_backup_from_before_partial_payments_restores_as_settled(tmp_path):
    store = make_store(tmp_path)
    old = json.dumps(
        {
            "expenses": [{"date": "2026-11-01", "item": "Chai", "amount": 20, "category": "Food"}],
            "udhar": [
                {
                    "date": "2026-11-01",
                    "person": "Arjun",
                    "amount": 300,
                    "type": "Lent (Diya)",
                    "status": "Settled",
                }
            ],
            "budget": 9000,
        }
    )

    store.restore_json(old)

    row = store.udhar().iloc[0]
    assert row["paid"] == 300.0  # a settled row is fully paid
    assert row["remaining"] == 0.0


def test_restore_skips_zero_and_negative_amounts(tmp_path):
    store = make_store(tmp_path)
    payload = json.dumps(
        {
            "expenses": [
                {"date": "2026-11-01", "item": "Real", "amount": 20, "category": "Food"},
                {"date": "2026-11-01", "item": "Zero", "amount": 0, "category": "Food"},
                {"date": "2026-11-01", "item": "Negative", "amount": -5, "category": "Food"},
            ]
        }
    )

    assert store.restore_json(payload) == (1, 0)
    assert store.expenses()["item"].tolist() == ["Real"]


# ---------------- money and parsing ----------------

def test_thousands_separators_are_one_amount():
    rows, _ = parse_expenses("chai 1,500")
    assert [(row["item"], row["amount"]) for row in rows] == [("Chai", 1500.0)]

    rows, _ = parse_expenses("rent 1,00,000")
    assert [(row["item"], row["amount"]) for row in rows] == [("Rent", 100000.0)]

    # A real list still splits: the comma is followed by a space and a word.
    rows, _ = parse_expenses("chai 20, auto 80")
    assert [row["amount"] for row in rows] == [20.0, 80.0]


def test_legacy_database_gains_paid_and_backfills_settled_rows(tmp_path):
    import sqlite3

    db = tmp_path / "legacy.db"
    conn = sqlite3.connect(db)
    conn.executescript(
        """
        CREATE TABLE udhar (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL, person TEXT NOT NULL, amount REAL NOT NULL,
            type TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'Pending',
            created_at TEXT NOT NULL
        );
        """
    )
    conn.execute(
        "INSERT INTO udhar (date, person, amount, type, status, created_at)"
        " VALUES ('2026-11-01','Arjun',300,'Lent (Diya)','Settled','2026-11-01T10:00:00')"
    )
    conn.execute(
        "INSERT INTO udhar (date, person, amount, type, status, created_at)"
        " VALUES ('2026-11-01','Ravi',500,'Lent (Diya)','Pending','2026-11-01T10:00:00')"
    )
    conn.commit()
    conn.close()

    store = Store(db, migrate_legacy=False)

    frame = store.udhar().set_index("person")
    assert frame.loc["Arjun", "paid"] == 300.0  # settled rows are fully paid
    assert frame.loc["Arjun", "remaining"] == 0.0
    assert frame.loc["Ravi", "paid"] == 0.0


def test_inr_keeps_paise_and_places_the_sign():
    assert insights.inr(1500) == "₹1,500"
    assert insights.inr(20.5) == "₹20.50"
    assert insights.inr(1499.99) == "₹1,499.99"
    assert insights.inr(-12.5) == "-₹12.50"
    assert insights.inr(0) == "₹0"
