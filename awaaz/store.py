"""SQLite persistence for expenses, udhar/khata entries and settings.

CSV worked for a demo but could not edit or delete a single row, could not
settle a khata entry, and lost the file if two reruns wrote at once. SQLite
gives us ids, durable updates and atomic writes, and the legacy CSV files are
imported automatically on first run.
"""

from __future__ import annotations

import datetime as dt
import json
import sqlite3
from pathlib import Path

import pandas as pd

from . import config
from .parser import normalize_category

EXPENSE_COLUMNS = [
    "id",
    "date",
    "item",
    "amount",
    "category",
    "merchant",
    "payment_mode",
    "kind",
    "source",
    "created_at",
]
UDHAR_COLUMNS = ["id", "date", "person", "amount", "paid", "remaining", "type", "status", "created_at"]


class Store:
    """Thin, dependency-free data layer over a single SQLite file."""

    def __init__(self, path: str | Path | None = None, *, migrate_legacy: bool = True):
        self.path = Path(path) if path is not None else config.db_path()
        if str(self.path) != ":memory:":
            self.path.parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()
        if migrate_legacy:
            self.import_legacy_csv()

    # ---------------- internals ----------------

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.path))
        conn.row_factory = sqlite3.Row
        return conn

    def _init_schema(self) -> None:
        with self._connect() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS expenses (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    date TEXT NOT NULL,
                    item TEXT NOT NULL,
                    amount REAL NOT NULL,
                    category TEXT NOT NULL,
                    merchant TEXT,
                    payment_mode TEXT,
                    kind TEXT NOT NULL DEFAULT 'Expense',
                    source TEXT NOT NULL DEFAULT 'voice',
                    created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS udhar (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    date TEXT NOT NULL,
                    person TEXT NOT NULL,
                    amount REAL NOT NULL,
                    paid REAL NOT NULL DEFAULT 0,
                    type TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'Pending',
                    created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS settings (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_expenses_date ON expenses(date);
                CREATE INDEX IF NOT EXISTS idx_udhar_status ON udhar(status);
                """
            )
            columns = {row["name"] for row in conn.execute("PRAGMA table_info(udhar)")}
            if "paid" not in columns:  # databases created before partial payments
                conn.execute("ALTER TABLE udhar ADD COLUMN paid REAL NOT NULL DEFAULT 0")
            # A settled entry is, by definition, fully paid — including rows that
            # existed before the paid column did.
            conn.execute(
                "UPDATE udhar SET paid = amount WHERE status = 'Settled' AND paid < amount"
            )
            expense_columns = {
                row["name"] for row in conn.execute("PRAGMA table_info(expenses)")
            }
            for column, ddl in (
                ("merchant", "ALTER TABLE expenses ADD COLUMN merchant TEXT"),
                ("payment_mode", "ALTER TABLE expenses ADD COLUMN payment_mode TEXT"),
                (
                    "kind",
                    "ALTER TABLE expenses ADD COLUMN kind TEXT NOT NULL DEFAULT 'Expense'",
                ),
            ):
                if column not in expense_columns:
                    conn.execute(ddl)

    # ---------------- expenses ----------------

    def add_expenses(self, rows: list[dict], source: str = "voice") -> list[int]:
        """Insert parsed expense rows and return the new ids."""
        if not rows:
            return []
        now = dt.datetime.now().isoformat(timespec="seconds")
        ids: list[int] = []
        with self._connect() as conn:
            for row in rows:
                amount = float(row.get("amount") or 0)
                if amount <= 0:
                    continue
                cursor = conn.execute(
                    "INSERT INTO expenses"
                    " (date, item, amount, category, merchant, payment_mode, kind, source, created_at)"
                    " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (
                        str(row.get("date") or dt.date.today().isoformat()),
                        (str(row.get("item") or "General")).strip() or "General",
                        round(amount, 2),
                        normalize_category(row.get("category", "Other")),
                        (str(row["merchant"]).strip() if row.get("merchant") else None),
                        row.get("payment_mode"),
                        "Income" if str(row.get("kind", "")).lower() == "income" else "Expense",
                        source,
                        now,
                    ),
                )
                ids.append(int(cursor.lastrowid))
        return ids

    def add_expense(
        self,
        item: str,
        amount: float,
        category: str = "Other",
        date: str | dt.date | None = None,
        source: str = "manual",
    ) -> int:
        row = {
            "date": date.isoformat() if isinstance(date, dt.date) else (date or dt.date.today().isoformat()),
            "item": item,
            "amount": amount,
            "category": category,
        }
        ids = self.add_expenses([row], source=source)
        return ids[0] if ids else 0

    def expenses(self) -> pd.DataFrame:
        with self._connect() as conn:
            frame = pd.read_sql_query(
                "SELECT id, date, item, amount, category, merchant, payment_mode, kind,"
                " source, created_at"
                " FROM expenses ORDER BY date ASC, id ASC",
                conn,
            )
        if frame.empty:
            return pd.DataFrame(columns=EXPENSE_COLUMNS)
        frame["amount"] = pd.to_numeric(frame["amount"], errors="coerce").fillna(0.0)
        return frame

    def update_expense(
        self,
        expense_id: int,
        *,
        date: str | None = None,
        item: str | None = None,
        amount: float | None = None,
        category: str | None = None,
        merchant: str | None = None,
        payment_mode: str | None = None,
        kind: str | None = None,
    ) -> None:
        fields, values = [], []
        if date is not None:
            fields.append("date = ?")
            values.append(date)
        if item is not None:
            fields.append("item = ?")
            values.append(item)
        if amount is not None:
            fields.append("amount = ?")
            values.append(round(float(amount), 2))
        if category is not None:
            fields.append("category = ?")
            values.append(normalize_category(category))
        if merchant is not None:
            fields.append("merchant = ?")
            values.append(merchant.strip() or None)
        if payment_mode is not None:
            fields.append("payment_mode = ?")
            values.append(payment_mode)
        if kind is not None:
            fields.append("kind = ?")
            values.append("Income" if kind.lower() == "income" else "Expense")
        if not fields:
            return
        values.append(int(expense_id))
        with self._connect() as conn:
            conn.execute(f"UPDATE expenses SET {', '.join(fields)} WHERE id = ?", values)

    def delete_expenses(self, ids: list[int]) -> int:
        ids = [int(i) for i in ids]
        if not ids:
            return 0
        placeholders = ",".join("?" * len(ids))
        with self._connect() as conn:
            cursor = conn.execute(f"DELETE FROM expenses WHERE id IN ({placeholders})", ids)
        return cursor.rowcount

    def recent_duplicates(self, rows: list[dict], minutes: int = 2) -> list[dict]:
        """Entries saved moments ago with the same amount and item."""
        if not rows:
            return []
        cutoff = (dt.datetime.now() - dt.timedelta(minutes=minutes)).isoformat(
            timespec="seconds"
        )
        matches: list[dict] = []
        with self._connect() as conn:
            for row in rows:
                amount = round(float(row.get("amount") or 0), 2)
                item = str(row.get("item") or "").strip().lower()
                if amount <= 0:
                    continue
                found = conn.execute(
                    "SELECT id, item, amount, created_at FROM expenses"
                    " WHERE created_at >= ? AND ROUND(amount, 2) = ? AND LOWER(item) = ?",
                    (cutoff, amount, item),
                ).fetchone()
                if found:
                    matches.append(dict(found))
        return matches

    # ---------------- udhar / khata ----------------

    def add_udhar(self, rows: list[dict]) -> list[int]:
        if not rows:
            return []
        now = dt.datetime.now().isoformat(timespec="seconds")
        ids: list[int] = []
        with self._connect() as conn:
            for row in rows:
                amount = float(row.get("amount") or 0)
                if amount <= 0:
                    continue
                money = round(amount, 2)
                paid = min(max(float(row.get("paid") or 0), 0.0), money)
                if str(row.get("status") or "") == "Settled" and paid == 0:
                    paid = money  # backups written before partial payments existed
                status = "Settled" if paid >= money else str(row.get("status") or "Pending")
                cursor = conn.execute(
                    "INSERT INTO udhar (date, person, amount, paid, type, status, created_at)"
                    " VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (
                        str(row.get("date") or dt.date.today().isoformat()),
                        (str(row.get("person") or "Someone")).strip() or "Someone",
                        money,
                        round(paid, 2),
                        str(row.get("type") or "Lent (Diya)"),
                        status,
                        now,
                    ),
                )
                ids.append(int(cursor.lastrowid))
        return ids

    def udhar(self) -> pd.DataFrame:
        with self._connect() as conn:
            frame = pd.read_sql_query(
                "SELECT id, date, person, amount, paid, type, status, created_at"
                " FROM udhar ORDER BY date DESC, id DESC",
                conn,
            )
        if frame.empty:
            return pd.DataFrame(columns=UDHAR_COLUMNS)
        for column in ("amount", "paid"):
            frame[column] = pd.to_numeric(frame[column], errors="coerce").fillna(0.0)
        frame["remaining"] = (frame["amount"] - frame["paid"]).clip(lower=0).round(2)
        return frame

    def set_udhar_status(self, ids: list[int], status: str) -> int:
        """Mark entries settled (fully paid) or reopen them (nothing paid)."""
        ids = [int(i) for i in ids]
        if not ids:
            return 0
        placeholders = ",".join("?" * len(ids))
        with self._connect() as conn:
            if status == "Settled":
                cursor = conn.execute(
                    f"UPDATE udhar SET status = 'Settled', paid = amount"
                    f" WHERE id IN ({placeholders})",
                    ids,
                )
            else:
                cursor = conn.execute(
                    f"UPDATE udhar SET status = 'Pending', paid = 0"
                    f" WHERE id IN ({placeholders})",
                    ids,
                )
        return cursor.rowcount

    def record_payment(self, udhar_id: int, payment: float | None = None) -> dict:
        """Add a full or partial repayment and return the entry's new balance."""
        with self._connect() as conn:
            row = conn.execute(
                "SELECT amount, paid FROM udhar WHERE id = ?", (int(udhar_id),)
            ).fetchone()
            if row is None:
                raise ValueError(f"No khata entry with id {udhar_id}.")
            amount = float(row["amount"])
            paid = float(row["paid"])
            delta = amount - paid if payment is None else float(payment)
            paid = round(min(max(paid + max(delta, 0.0), 0.0), amount), 2)
            status = "Settled" if paid >= amount else "Pending"
            conn.execute(
                "UPDATE udhar SET paid = ?, status = ? WHERE id = ?",
                (paid, status, int(udhar_id)),
            )
        return {"paid": paid, "remaining": round(amount - paid, 2), "status": status}

    def update_udhar(
        self,
        udhar_id: int,
        *,
        date: str | None = None,
        person: str | None = None,
        amount: float | None = None,
        type: str | None = None,
    ) -> None:
        """Fix a typo or a wrong amount without deleting and re-adding the row."""
        fields, values = [], []
        if date is not None:
            fields.append("date = ?")
            values.append(date)
        if person is not None and person.strip():
            fields.append("person = ?")
            values.append(person.strip())
        if amount is not None:
            fields.append("amount = ?")
            values.append(round(float(amount), 2))
        if type is not None:
            fields.append("type = ?")
            values.append(type)
        if not fields:
            return
        values.append(int(udhar_id))
        with self._connect() as conn:
            conn.execute(f"UPDATE udhar SET {', '.join(fields)} WHERE id = ?", values)
            row = conn.execute(
                "SELECT amount, paid FROM udhar WHERE id = ?", (int(udhar_id),)
            ).fetchone()
            if row is not None:
                # A reduced amount must never leave more paid than was ever owed.
                amount_now = float(row["amount"])
                paid_now = min(float(row["paid"]), amount_now)
                status = "Settled" if paid_now >= amount_now else "Pending"
                conn.execute(
                    "UPDATE udhar SET paid = ?, status = ? WHERE id = ?",
                    (round(paid_now, 2), status, int(udhar_id)),
                )

    def delete_udhar(self, ids: list[int]) -> int:
        ids = [int(i) for i in ids]
        if not ids:
            return 0
        placeholders = ",".join("?" * len(ids))
        with self._connect() as conn:
            cursor = conn.execute(f"DELETE FROM udhar WHERE id IN ({placeholders})", ids)
        return cursor.rowcount

    def pending_udhar(self) -> pd.DataFrame:
        frame = self.udhar()
        return frame[frame["status"] == "Pending"] if not frame.empty else frame

    # ---------------- settings ----------------

    def get_setting(self, key: str, default: str | None = None) -> str | None:
        with self._connect() as conn:
            row = conn.execute("SELECT value FROM settings WHERE key = ?", (key,)).fetchone()
        return row["value"] if row else default

    def set_setting(self, key: str, value: str | float | int) -> None:
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO settings (key, value) VALUES (?, ?)"
                " ON CONFLICT(key) DO UPDATE SET value = excluded.value",
                (key, str(value)),
            )

    def get_budget(self, default: float = 12000.0) -> float:
        try:
            return float(self.get_setting("budget", str(default)) or default)
        except (TypeError, ValueError):
            return default

    def set_budget(self, amount: float) -> None:
        self.set_setting("budget", max(0.0, float(amount)))

    # ---------------- export / reset ----------------

    def export_csv(self) -> str:
        return self.expenses().drop(columns=["created_at"], errors="ignore").to_csv(index=False)

    def export_json(self) -> str:
        payload = {
            "exported_at": dt.datetime.now().isoformat(timespec="seconds"),
            "expenses": self.expenses().drop(columns=["created_at"], errors="ignore").to_dict("records"),
            "udhar": self.udhar()
            .drop(columns=["created_at", "remaining"], errors="ignore")
            .to_dict("records"),
            "budget": self.get_budget(),
        }
        return json.dumps(payload, indent=2, ensure_ascii=False)

    @staticmethod
    def _parse_backup(payload: str) -> dict:
        """Validate a backup file before anything is written."""
        try:
            data = json.loads(payload)
        except ValueError as exc:
            raise ValueError("That file is not valid JSON.") from exc
        if not isinstance(data, dict):
            raise ValueError("That backup is not in the Awaaz Kharcha format.")
        expenses = data.get("expenses") or []
        udhar = data.get("udhar") or []
        if not isinstance(expenses, list) or not isinstance(udhar, list):
            raise ValueError("That backup is not in the Awaaz Kharcha format.")
        if not expenses and not udhar:
            raise ValueError("That backup has no expenses or khata entries.")
        return {"expenses": expenses, "udhar": udhar, "budget": data.get("budget")}

    def backup_preview(self, payload: str) -> dict:
        """Describe a backup file without touching the current data."""
        data = self._parse_backup(payload)
        dates = sorted(str(row.get("date")) for row in data["expenses"] if row.get("date"))
        return {
            "expenses": len(data["expenses"]),
            "udhar": len(data["udhar"]),
            "first": dates[0] if dates else None,
            "last": dates[-1] if dates else None,
            "budget": float(data.get("budget") or 0),
        }

    def restore_json(self, payload: str) -> tuple[int, int]:
        """Replace all local data with a backup and report what was restored."""
        data = self._parse_backup(payload)
        self.clear_all()
        expense_ids = self.add_expenses(
            [
                {
                    "date": row.get("date"),
                    "item": row.get("item"),
                    "amount": row.get("amount"),
                    "category": row.get("category"),
                }
                for row in data["expenses"]
            ],
            source="restored",
        )
        udhar_ids = self.add_udhar(
            [
                {
                    "date": row.get("date"),
                    "person": row.get("person"),
                    "amount": row.get("amount"),
                    "paid": row.get("paid") or 0,
                    "type": row.get("type"),
                    "status": row.get("status"),
                }
                for row in data["udhar"]
            ]
        )
        budget = data.get("budget")
        if budget:
            self.set_budget(float(budget))
        return len(expense_ids), len(udhar_ids)

    def clear_all(self) -> None:
        with self._connect() as conn:
            conn.execute("DELETE FROM expenses")
            conn.execute("DELETE FROM udhar")

    def counts(self) -> tuple[int, int]:
        with self._connect() as conn:
            expenses = conn.execute("SELECT COUNT(*) FROM expenses").fetchone()[0]
            udhar = conn.execute("SELECT COUNT(*) FROM udhar").fetchone()[0]
        return int(expenses), int(udhar)

    # ---------------- legacy v1 CSV import ----------------

    def import_legacy_csv(self) -> None:
        """Import v1's expenses.csv / udhar_khata.csv exactly once."""
        if self.get_setting("legacy_import_v1") == "done":
            return
        imported_any = False

        if config.LEGACY_EXPENSE_CSV.exists():
            try:
                frame = pd.read_csv(config.LEGACY_EXPENSE_CSV)
                rows = []
                for record in frame.to_dict("records"):
                    rows.append(
                        {
                            "date": str(record.get("date") or dt.date.today().isoformat()),
                            "item": str(record.get("item") or "General"),
                            "amount": float(record.get("amount") or 0),
                            "category": normalize_category(record.get("category", "Other")),
                        }
                    )
                if self.add_expenses(rows, source="legacy"):
                    imported_any = True
                config.LEGACY_EXPENSE_CSV.rename(
                    config.LEGACY_EXPENSE_CSV.with_suffix(".csv.imported")
                )
            except Exception:
                pass  # a malformed legacy file must never block the app

        if config.LEGACY_UDHAR_CSV.exists():
            try:
                frame = pd.read_csv(config.LEGACY_UDHAR_CSV)
                rows = []
                for record in frame.to_dict("records"):
                    rows.append(
                        {
                            "date": str(record.get("date") or dt.date.today().isoformat()),
                            "person": str(record.get("person") or "Someone"),
                            "amount": float(record.get("amount") or 0),
                            "type": str(record.get("type") or "Lent (Diya)"),
                            "status": str(record.get("status") or "Pending"),
                        }
                    )
                if self.add_udhar(rows):
                    imported_any = True
                config.LEGACY_UDHAR_CSV.rename(
                    config.LEGACY_UDHAR_CSV.with_suffix(".csv.imported")
                )
            except Exception:
                pass

        if imported_any:
            self.set_setting("legacy_import_v1", "done")
