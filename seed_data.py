"""Seed the local database with realistic demo data.

Usage:  python seed_data.py [--force]

Only seeds when the database is empty (unless --force is passed), so running it
twice never duplicates rows.
"""

from __future__ import annotations

import argparse
import datetime as dt

from awaaz.store import Store


def demo_expenses(today: dt.date) -> list[dict]:
    return [
        {"date": (today - dt.timedelta(days=9)).isoformat(), "item": "Chai & Samosa", "amount": 40.0, "category": "Food"},
        {"date": (today - dt.timedelta(days=9)).isoformat(), "item": "Metro Recharge", "amount": 200.0, "category": "Bills"},
        {"date": (today - dt.timedelta(days=8)).isoformat(), "item": "Auto Rickshaw", "amount": 80.0, "category": "Travel"},
        {"date": (today - dt.timedelta(days=8)).isoformat(), "item": "Canteen Biryani", "amount": 160.0, "category": "Food"},
        {"date": (today - dt.timedelta(days=6)).isoformat(), "item": "Rapido Bike", "amount": 65.0, "category": "Travel"},
        {"date": (today - dt.timedelta(days=6)).isoformat(), "item": "Chai with Friends", "amount": 30.0, "category": "Food"},
        {"date": (today - dt.timedelta(days=5)).isoformat(), "item": "Xerox Notes", "amount": 45.0, "category": "Education"},
        {"date": (today - dt.timedelta(days=4)).isoformat(), "item": "Sabzi & Milk", "amount": 120.0, "category": "Groceries"},
        {"date": (today - dt.timedelta(days=3)).isoformat(), "item": "Movie Ticket", "amount": 180.0, "category": "Fun"},
        {"date": (today - dt.timedelta(days=2)).isoformat(), "item": "Dinner Thali", "amount": 150.0, "category": "Food"},
        {"date": (today - dt.timedelta(days=1)).isoformat(), "item": "Pharmacy", "amount": 90.0, "category": "Health"},
        {"date": today.isoformat(), "item": "Chai", "amount": 20.0, "category": "Food"},
        {"date": today.isoformat(), "item": "Auto", "amount": 80.0, "category": "Travel"},
    ]


def demo_udhar(today: dt.date) -> list[dict]:
    return [
        {"date": (today - dt.timedelta(days=3)).isoformat(), "person": "Ravi", "amount": 500.0, "type": "Lent (Diya)", "status": "Pending"},
        {"date": (today - dt.timedelta(days=2)).isoformat(), "person": "Sneha", "amount": 250.0, "type": "Borrowed (Liya)", "status": "Pending"},
        {"date": (today - dt.timedelta(days=7)).isoformat(), "person": "Arjun", "amount": 300.0, "type": "Lent (Diya)", "status": "Settled"},
    ]


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed Awaaz Kharcha with demo data")
    parser.add_argument("--force", action="store_true", help="seed even if data already exists")
    args = parser.parse_args()

    today = dt.date.today()
    store = Store()
    expense_count, udhar_count = store.counts()

    if (expense_count or udhar_count) and not args.force:
        print(f"Database already has {expense_count} expenses and {udhar_count} khata entries; nothing seeded.")
        print("Run 'python seed_data.py --force' to add the demo data anyway.")
        return

    store.add_expenses(demo_expenses(today), source="seed")
    store.add_udhar(demo_udhar(today))
    print(f"Seeded {len(demo_expenses(today))} expenses and {len(demo_udhar(today))} khata entries into {store.path}")


if __name__ == "__main__":
    main()
