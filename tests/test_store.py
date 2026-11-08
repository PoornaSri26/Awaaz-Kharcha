"""Storage tests: CRUD, khata settlement, settings, legacy CSV import."""

from __future__ import annotations

from awaaz import config
from awaaz.store import Store


def make_store(tmp_path, **kwargs) -> Store:
    return Store(tmp_path / "test.db", migrate_legacy=kwargs.get("migrate_legacy", False))


def test_add_and_list_expenses(tmp_path):
    store = make_store(tmp_path)
    ids = store.add_expenses(
        [
            {"date": "2026-11-08", "item": "Chai", "amount": 20, "category": "Food"},
            {"date": "2026-11-07", "item": "Auto", "amount": 80, "category": "Travel"},
        ]
    )

    assert len(ids) == 2
    frame = store.expenses()
    assert len(frame) == 2
    assert list(frame.columns) == ["id", "date", "item", "amount", "category", "source", "created_at"]
    assert frame["item"].tolist() == ["Auto", "Chai"]  # ordered by date
    assert set(frame["source"]) == {"voice"}


def test_zero_amounts_are_rejected(tmp_path):
    store = make_store(tmp_path)
    assert store.add_expenses([{"date": "2026-11-08", "item": "Free", "amount": 0}]) == []
    assert store.expenses().empty


def test_update_and_delete_expenses(tmp_path):
    store = make_store(tmp_path)
    expense_id = store.add_expense("Chai", 20, category="Food", date="2026-11-08")

    store.update_expense(expense_id, item="Chai + Samosa", amount=40, category="Food")
    row = store.expenses().iloc[0]
    assert row["item"] == "Chai + Samosa"
    assert row["amount"] == 40.0

    assert store.delete_expenses([expense_id]) == 1
    assert store.expenses().empty


def test_update_expense_ignores_empty_change_set(tmp_path):
    store = make_store(tmp_path)
    expense_id = store.add_expense("Chai", 20, category="Food")
    store.update_expense(expense_id)
    assert store.expenses().iloc[0]["item"] == "Chai"


def test_udhar_lifecycle(tmp_path):
    store = make_store(tmp_path)
    ids = store.add_udhar(
        [{"date": "2026-11-08", "person": "Ravi", "amount": 500, "type": "Lent (Diya)"}]
    )

    assert len(store.pending_udhar()) == 1
    assert store.set_udhar_status(ids, "Settled") == 1
    assert store.pending_udhar().empty
    assert store.udhar().iloc[0]["status"] == "Settled"
    assert store.delete_udhar(ids) == 1
    assert store.udhar().empty


def test_budget_setting_round_trip(tmp_path):
    store = make_store(tmp_path)
    assert store.get_budget(default=9000) == 9000
    store.set_budget(15000)
    assert store.get_budget() == 15000
    assert store.get_setting("missing", "fallback") == "fallback"


def test_exports(tmp_path):
    import json

    store = make_store(tmp_path)
    store.add_expense("Chai", 20, category="Food", date="2026-11-08")

    csv_text = store.export_csv()
    assert csv_text.splitlines()[0].startswith("id,date,item,amount,category")

    payload = json.loads(store.export_json())
    assert payload["expenses"][0]["item"] == "Chai"
    assert payload["budget"] >= 0


def test_counts_and_clear(tmp_path):
    store = make_store(tmp_path)
    store.add_expense("Chai", 20, category="Food")
    store.add_udhar([{"person": "Ravi", "amount": 100, "type": "Lent (Diya)"}])

    assert store.counts() == (1, 1)
    store.clear_all()
    assert store.counts() == (0, 0)


def test_legacy_csv_is_imported_once(tmp_path, monkeypatch):
    legacy_expenses = tmp_path / "expenses.csv"
    legacy_expenses.write_text(
        "date,item,amount,category\n"
        "2026-11-01,Chai,20,Food & Chai\n"
        "2026-11-02,Auto,80,Travel & Commute\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(config, "LEGACY_EXPENSE_CSV", legacy_expenses)
    monkeypatch.setattr(config, "LEGACY_UDHAR_CSV", tmp_path / "missing.csv")

    store = Store(tmp_path / "legacy.db")

    frame = store.expenses()
    assert len(frame) == 2
    assert set(frame["category"]) == {"Food", "Travel"}
    assert not legacy_expenses.exists()
    assert (tmp_path / "expenses.csv.imported").exists()

    # A second store on the same file must not duplicate the import.
    again = Store(tmp_path / "legacy.db")
    assert len(again.expenses()) == 2
