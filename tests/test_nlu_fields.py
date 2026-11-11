"""Structured fields from one sentence: merchant, payment mode, income vs expense."""

from __future__ import annotations

import datetime as dt
import json

import pandas as pd

from awaaz import insights
from awaaz.parser import (
    detect_kind,
    detect_merchant,
    detect_payment_mode,
    parse_expenses,
)
from awaaz.store import Store

TODAY = dt.date(2026, 11, 11)


def one(text: str) -> dict:
    rows, _ = parse_expenses(text, today=TODAY)
    assert len(rows) == 1, rows
    return rows[0]


# ---------------- parser ----------------

def test_merchant_is_read_from_at_and_from():
    assert detect_merchant("spent 250 on lunch at Paradise by UPI") == "Paradise"
    assert detect_merchant("bought shoes from Amazon") == "Amazon"
    assert detect_merchant("chai 20") is None


def test_merchant_ignores_payment_and_date_words():
    assert detect_merchant("snacks 60 at DMart cash") == "DMart"
    assert detect_merchant("600 at 8 pm for cab") is None


def test_payment_modes_are_recognised_longest_first():
    assert detect_payment_mode("paid by UPI") == "UPI"
    assert detect_payment_mode("chai 20 cash") == "Cash"
    assert detect_payment_mode("paid by credit card") == "Card"
    assert detect_payment_mode("paid by debit card") == "Card"
    assert detect_payment_mode("netbanking transfer") == "Netbanking"
    assert detect_payment_mode("chai 20") is None


def test_income_is_separated_from_spending():
    assert detect_kind("received 5000 salary") == "Income"
    assert detect_kind("refund credited 200") == "Income"
    assert detect_kind("spent 200 on petrol") == "Expense"


def test_one_sentence_fills_every_field():
    row = one("spent 250 on lunch at Paradise by UPI")

    assert row["amount"] == 250.0
    assert row["category"] == "Food"
    assert row["merchant"] == "Paradise"
    assert row["payment_mode"] == "UPI"
    assert row["kind"] == "Expense"
    assert row["item"] == "Lunch"


def test_item_name_drops_verbs_and_income_markers():
    assert one("bought shoes from Amazon 2999")["item"] == "Shoes"
    assert one("received 5000 salary")["item"] == "Salary"


def test_a_mode_said_once_applies_to_every_item():
    rows, _ = parse_expenses("tea 20, auto 150 by upi", today=TODAY)
    assert [row["payment_mode"] for row in rows] == ["UPI", "UPI"]


def test_payment_words_do_not_pollute_the_item_name():
    row = one("auto 80 by cash")
    assert row["item"] == "Auto"
    assert row["payment_mode"] == "Cash"


def test_each_item_in_a_list_keeps_its_own_mode():
    rows, _ = parse_expenses("chai 20 cash, auto 80 by upi", today=TODAY)
    assert [(row["item"], row["payment_mode"]) for row in rows] == [
        ("Chai", "Cash"),
        ("Auto", "UPI"),
    ]


# ---------------- storage ----------------

def test_new_fields_persist_and_can_be_edited(tmp_path):
    store = Store(tmp_path / "nlu.db", migrate_legacy=False)
    rows, _ = parse_expenses("spent 250 on lunch at Paradise by UPI", today=TODAY)
    expense_id = store.add_expenses(rows)[0]

    row = store.expenses().iloc[0]
    assert (row["merchant"], row["payment_mode"], row["kind"]) == ("Paradise", "UPI", "Expense")

    store.update_expense(expense_id, payment_mode="Cash", merchant="", kind="Income")
    row = store.expenses().iloc[0]
    assert row["payment_mode"] == "Cash"
    assert row["merchant"] is None  # blank clears it
    assert row["kind"] == "Income"


def test_old_database_gains_the_new_expense_columns(tmp_path):
    import sqlite3

    db = tmp_path / "old.db"
    conn = sqlite3.connect(db)
    conn.executescript(
        """
        CREATE TABLE expenses (
            id INTEGER PRIMARY KEY AUTOINCREMENT, date TEXT NOT NULL,
            item TEXT NOT NULL, amount REAL NOT NULL, category TEXT NOT NULL,
            source TEXT NOT NULL DEFAULT 'voice', created_at TEXT NOT NULL
        );
        """
    )
    conn.execute(
        "INSERT INTO expenses (date, item, amount, category, source, created_at)"
        " VALUES ('2026-11-01','Chai',20,'Food','voice','2026-11-01T10:00:00')"
    )
    conn.commit()
    conn.close()

    frame = Store(db, migrate_legacy=False).expenses()

    assert set(["merchant", "payment_mode", "kind"]).issubset(frame.columns)
    assert frame.iloc[0]["kind"] == "Expense"  # default for existing rows
    assert pd.isna(frame.iloc[0]["merchant"])


def test_export_keeps_the_new_fields(tmp_path):
    store = Store(tmp_path / "export.db", migrate_legacy=False)
    rows, _ = parse_expenses("lunch 250 at Paradise upi", today=TODAY)
    store.add_expenses(rows)

    payload = json.loads(store.export_json())

    assert payload["expenses"][0]["merchant"] == "Paradise"
    assert payload["expenses"][0]["payment_mode"] == "UPI"
    assert payload["expenses"][0]["kind"] == "Expense"


# ---------------- analytics and duplicates ----------------

def test_income_is_excluded_from_spend_analytics():
    frame = pd.DataFrame(
        [
            {"id": 1, "date": "2026-11-11", "item": "Chai", "amount": 20.0, "category": "Food", "kind": "Expense"},
            {"id": 2, "date": "2026-11-11", "item": "Salary", "amount": 50000.0, "category": "Other", "kind": "Income"},
        ]
    )

    stats = insights.summary(frame, TODAY)

    assert stats["today"] == 20.0
    assert stats["month"] == 20.0
    assert "₹20" in insights.answer_query("is mahine kitna kharch hua?", frame, today=TODAY)


def test_duplicates_are_flagged_and_different_amounts_are_not(tmp_path):
    store = Store(tmp_path / "dupe.db", migrate_legacy=False)
    store.add_expense("Chai", 20, category="Food")

    assert [match["item"] for match in store.recent_duplicates([{"item": "Chai", "amount": 20}])] == ["Chai"]
    assert store.recent_duplicates([{"item": "Chai", "amount": 25}]) == []
    assert store.recent_duplicates([{"item": "Auto", "amount": 20}]) == []
    assert store.recent_duplicates([]) == []
