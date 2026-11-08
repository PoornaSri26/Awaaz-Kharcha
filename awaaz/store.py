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

EXPENSE_COLUMNS = ["id", "date", "item", "amount", "category", "source", "created_at"]
UDHAR_COLUMNS = ["id", "date", "person", "amount", "type", "status", "created_at"]


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
                    source TEXT NOT NULL DEFAULT 'voice',
                    created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS udhar (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    date TEXT NOT NULL,
                    person TEXT NOT NULL,
                    amount REAL NOT NULL,
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
                    "INSERT INTO expenses (date, item, amount, category, source, created_at)"
                    " VALUES (?, ?, ?, ?, ?, ?)",
                    (
                        str(row.get("date") or dt.date.today().isoformat()),
                        (str(row.get("item") or "General")).strip() or "General",
                        round(amount, 2),
                        normalize_category(row.get("category", "Other")),
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
                "SELECT id, date, item, amount, category, source, created_at"
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
                cursor = conn.execute(
                    "INSERT INTO udhar (date, person, amount, type, status, created_at)"
                    " VALUES (?, ?, ?, ?, ?, ?)",
                    (
                        str(row.get("date") or dt.date.today().isoformat()),
                        (str(row.get("person") or "Someone")).strip() or "Someone",
                        round(amount, 2),
                        str(row.get("type") or "Lent (Diya)"),
                        str(row.get("status") or "Pending"),
                        now,
                    ),
                )
                ids.append(int(cursor.lastrowid))
        return ids

    def udhar(self) -> pd.DataFrame:
        with self._connect() as conn:
            frame = pd.read_sql_query(
                "SELECT id, date, person, amount, type, status, created_at"
                " FROM udhar ORDER BY date DESC, id DESC",
                conn,
            )
        if frame.empty:
            return pd.DataFrame(columns=UDHAR_COLUMNS)
        frame["amount"] = pd.to_numeric(frame["amount"], errors="coerce").fillna(0.0)
        return frame

    def set_udhar_status(self, ids: list[int], status: str) -> int:
        ids = [int(i) for i in ids]
        if not ids:
            return 0
        placeholders = ",".join("?" * len(ids))
        with self._connect() as conn:
            cursor = conn.execute(
                f"UPDATE udhar SET status = ? WHERE id IN ({placeholders})",
                [status, *ids],
            )
        return cursor.rowcount

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
            "udhar": self.udhar().drop(columns=["created_at"], errors="ignore").to_dict("records"),
            "budget": self.get_budget(),
        }
        return json.dumps(payload, indent=2, ensure_ascii=False)

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
