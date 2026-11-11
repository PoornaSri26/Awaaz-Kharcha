"""Spending analytics and the multilingual voice Q&A engine."""

from __future__ import annotations

import calendar
import datetime as dt

import pandas as pd

from . import config
from .parser import CATEGORIES, word_in

MONTH_WORDS = ("is mahine", "is mahina", "this month", "इस महीने", "ఈ నెల", "e nel", "current month")
LAST_MONTH_WORDS = ("pichle mahine", "last month", "previous month", "पिछले महीने", "గత నెల")
TODAY_WORDS = ("aaj", "today", "आज", "ఈ రోజు", "eeroju", "నేడు")
WEEK_WORDS = ("is hafte", "this week", "hafte", "hafta", "week", "इस हफ्ते", "ఈ వారం")
BUDGET_WORDS = ("budget", "bacha", "bachega", "bachcha", "left", "remaining", "kitna bacha", "बजट", "బడ్జెట్")
UDHAR_WORDS = ("udhar", "khata", "baki", "baaki", "lent", "owe", "owes", "उधार", "అప్పు", "ఖాతా")
TOP_WORDS = ("top", "most", "sabse zyada", "sabse jyada", "highest", "बड़ा", "ఎక్కువ")
AVERAGE_WORDS = ("average", "per day", "roz", "daily", "औसत", "సగటు")
BIGGEST_WORDS = ("biggest", "largest", "sabse bada", "sabse mehnga", "highest single")
COUNT_WORDS = ("how many", "kitni", "kitne", "count", "number of")
PREV_WORDS = ("pichle hafte", "last week", "previous week")


def inr(amount: float) -> str:
    """Format a rupee amount, keeping paise only when they are actually there."""
    value = abs(float(amount or 0))
    sign = "-" if float(amount or 0) < 0 else ""
    if abs(value - round(value)) < 0.005:
        return f"{sign}₹{value:,.0f}"
    return f"{sign}₹{value:,.2f}"


def _prep(frame: pd.DataFrame | None) -> pd.DataFrame:
    """Return a copy with parsed dates and numeric amounts."""
    if frame is None or len(frame) == 0:
        return pd.DataFrame(columns=["id", "date", "item", "amount", "category"])
    out = frame.copy()
    out["date"] = pd.to_datetime(out["date"], errors="coerce")
    out = out.dropna(subset=["date"])
    if "amount" in out.columns:
        out["amount"] = pd.to_numeric(out["amount"], errors="coerce").fillna(0.0)
    else:
        out["amount"] = 0.0
    if "category" not in out.columns:
        out["category"] = "Other"
    if "item" not in out.columns:
        out["item"] = "General"
    return out


def month_frame(frame: pd.DataFrame, ref: dt.date) -> pd.DataFrame:
    if frame.empty:
        return frame
    return frame[(frame["date"].dt.month == ref.month) & (frame["date"].dt.year == ref.year)]


def shift_month(ref: dt.date, months: int = -1) -> dt.date:
    year = ref.year
    month = ref.month + months
    while month < 1:
        month += 12
        year -= 1
    while month > 12:
        month -= 12
        year += 1
    day = min(ref.day, calendar.monthrange(year, month)[1])
    return dt.date(year, month, day)


def summary(expenses: pd.DataFrame, today: dt.date | None = None) -> dict:
    """Headline numbers used by the dashboard."""
    today = today or dt.date.today()
    frame = _prep(expenses)
    stamp = pd.Timestamp(today)
    empty = {
        "today": 0.0,
        "month": 0.0,
        "week": 0.0,
        "prev_month": 0.0,
        "delta_pct": 0.0,
        "count": 0,
        "avg_per_day": 0.0,
        "top_category": None,
    }
    if frame.empty:
        return empty

    month = month_frame(frame, today)
    prev = month_frame(frame, shift_month(today))
    week = frame[frame["date"] >= stamp - dt.timedelta(days=6)]
    day_total = float(frame.loc[frame["date"] == stamp, "amount"].sum())
    month_total = float(month["amount"].sum())
    prev_total = float(prev["amount"].sum())

    top_category = month.groupby("category")["amount"].sum().idxmax() if not month.empty else None
    delta_pct = ((month_total - prev_total) / prev_total * 100) if prev_total > 0 else 0.0

    return {
        "today": day_total,
        "month": month_total,
        "week": float(week["amount"].sum()),
        "prev_month": prev_total,
        "delta_pct": delta_pct,
        "count": int(len(frame)),
        "avg_per_day": month_total / max(today.day, 1),
        "top_category": top_category,
    }


def budget_status(month_total: float, budget: float, today: dt.date | None = None) -> dict:
    """How much of the monthly budget is left, and how loud the nudge is."""
    today = today or dt.date.today()
    days_left = calendar.monthrange(today.year, today.month)[1] - today.day + 1
    if budget <= 0:
        return {
            "pct": 0.0,
            "remaining": 0.0,
            "days_left": days_left,
            "per_day": 0.0,
            "level": "off",
        }
    pct = month_total / budget * 100
    remaining = budget - month_total
    if remaining < 0:
        level = "over"
    elif pct >= config.ALERT_PCT:
        level = "alert"
    elif pct >= config.NUDGE_PCT:
        level = "nudge"
    else:
        level = "ok"
    return {
        "pct": pct,
        "remaining": remaining,
        "days_left": days_left,
        "per_day": max(remaining, 0.0) / days_left,
        "level": level,
    }


def category_totals(expenses: pd.DataFrame, today: dt.date | None = None) -> pd.Series:
    today = today or dt.date.today()
    month = month_frame(_prep(expenses), today)
    if month.empty:
        return pd.Series(dtype="float64")
    return month.groupby("category")["amount"].sum().sort_values(ascending=False)


def daily_totals(expenses: pd.DataFrame, days: int = 14, today: dt.date | None = None) -> pd.DataFrame:
    """One row per day (zero-filled) for the trend chart."""
    today = today or dt.date.today()
    frame = _prep(expenses)
    start = pd.Timestamp(today) - dt.timedelta(days=days - 1)
    index = pd.date_range(start=start, end=pd.Timestamp(today), freq="D")
    index.name = "date"
    if frame.empty:
        return pd.DataFrame({"amount": 0.0}, index=index)
    window = frame[frame["date"] >= start]
    series = window.groupby(window["date"].dt.normalize())["amount"].sum()
    series = series.reindex(index, fill_value=0.0)
    return pd.DataFrame({"amount": series.astype(float)}, index=index)


def top_items(expenses: pd.DataFrame, n: int = 5, today: dt.date | None = None) -> pd.DataFrame:
    today = today or dt.date.today()
    month = month_frame(_prep(expenses), today)
    if month.empty:
        return pd.DataFrame(columns=["item", "amount", "count"])
    grouped = (
        month.groupby("item")
        .agg(amount=("amount", "sum"), count=("amount", "size"))
        .sort_values("amount", ascending=False)
        .head(n)
        .reset_index()
    )
    return grouped


def weekday_insight(expenses: pd.DataFrame, today: dt.date | None = None) -> str | None:
    """Spot the weekly pattern, e.g. "Saturdays are your heaviest days"."""
    today = today or dt.date.today()
    frame = _prep(expenses)
    start = pd.Timestamp(today) - dt.timedelta(days=27)
    recent = frame[frame["date"] >= start]
    if len(recent) < 6:
        return None
    totals = recent.groupby(recent["date"].dt.day_name())["amount"].mean().sort_values(ascending=False)
    if len(totals) < 3 or totals.iloc[0] <= 0:
        return None
    top_day = totals.index[0]
    return f"{top_day}s are your heaviest days, averaging {inr(totals.iloc[0])}."


def weekly_insight(expenses: pd.DataFrame, today: dt.date | None = None) -> str:
    """A single human sentence about the last seven days."""
    today = today or dt.date.today()
    frame = _prep(expenses)
    if frame.empty:
        return "Log your first expense to unlock weekly insights."

    start = pd.Timestamp(today) - dt.timedelta(days=6)
    week = frame[frame["date"] >= start]
    if week.empty:
        week = frame  # fall back to whatever history exists

    total = float(week["amount"].sum())
    by_category = week.groupby("category")["amount"].sum().sort_values(ascending=False)
    top_category = by_category.index[0]
    top_amount = float(by_category.iloc[0])
    top_item_frame = week[week["category"] == top_category]
    item_note = ""
    if not top_item_frame.empty:
        item = top_item_frame.groupby("item")["amount"].sum().idxmax()
        if item and item != "General":
            item_note = f" (mostly {item})"

    streak = _logging_streak(frame, today)
    streak_note = f" {streak}-day logging streak — keep it going!" if streak >= 2 else ""
    return (
        f"You spent {inr(total)} in the last 7 days; {top_category} was your "
        f"biggest bucket at {inr(top_amount)}{item_note}.{streak_note}"
    )


def logging_streak(expenses: pd.DataFrame, today: dt.date | None = None) -> int:
    """Consecutive days (ending today) with at least one logged expense."""
    today = today or dt.date.today()
    return _logging_streak(_prep(expenses), today)


def _logging_streak(frame: pd.DataFrame, today: dt.date) -> int:
    if frame.empty:
        return 0
    days = set(frame["date"].dt.date)
    streak = 0
    cursor = today
    while cursor in days:
        streak += 1
        cursor -= dt.timedelta(days=1)
    return streak


# ---------------- VOICE Q&A ----------------

def _has(query: str, words: tuple[str, ...]) -> bool:
    return any(word_in(query, w) for w in words)


def _scope(expenses: pd.DataFrame, query: str, today: dt.date) -> tuple[pd.DataFrame, str]:
    """Narrow the data to whatever period the question talks about."""
    if not expenses.empty:
        if _has(query, LAST_MONTH_WORDS):
            prev = shift_month(today)
            return month_frame(expenses, prev), f"in {prev.strftime('%B %Y')}"
        if _has(query, MONTH_WORDS):
            return month_frame(expenses, today), "this month"
        if _has(query, TODAY_WORDS):
            return expenses[expenses["date"] == pd.Timestamp(today)], "today"
        if _has(query, PREV_WORDS):
            start = pd.Timestamp(today) - dt.timedelta(days=13)
            end = pd.Timestamp(today) - dt.timedelta(days=7)
            return expenses[(expenses["date"] >= start) & (expenses["date"] <= end)], "last week"
        if _has(query, WEEK_WORDS):
            start = pd.Timestamp(today) - dt.timedelta(days=6)
            return expenses[expenses["date"] >= start], "in the last 7 days"
    return expenses, "overall"


def _topic(query: str) -> str | None:
    for category, words in CATEGORIES.items():
        if category == "Udhar/Khata":
            continue
        if any(word_in(query, word) for word in words):
            return category
    return None


def _person_from_query(query: str, udhar: pd.DataFrame) -> str | None:
    if udhar.empty or "person" not in udhar.columns:
        return None
    for person in udhar["person"].dropna().unique():
        first = str(person).split()[0].lower()
        if len(first) >= 3 and word_in(query, first):
            return str(person)
    return None


def _item_match(scope: pd.DataFrame, query: str) -> pd.DataFrame:
    """Free-text item lookup: "chai pe kitna gaya" -> rows mentioning chai."""
    if scope.empty:
        return scope
    stop = {
        "how", "much", "did", "the", "and", "for", "kitna", "kitne", "kitni", "gaya",
        "gayi", "hua", "hui", "spent", "spend", "pe", "par", "ka", "ke", "ki", "ko",
        "is", "this", "month", "mahine", "today", "aaj", "week", "hafte", "on", "my",
        "total", "show", "what", "which", "was", "were", "i", "didi", "batao",
    }
    tokens = [t for t in str(query).lower().replace("?", " ").split() if t not in stop and len(t) >= 3]
    if not tokens:
        return scope.iloc[0:0]
    mask = scope["item"].astype(str).str.lower()
    combined = pd.Series(False, index=scope.index)
    for token in tokens:
        combined = combined | mask.str.contains(token, regex=False)
    return scope[combined]


def answer_query(
    query: str,
    expenses: pd.DataFrame,
    udhar: pd.DataFrame | None = None,
    budget: float = 0.0,
    today: dt.date | None = None,
) -> str:
    """Answer a spoken/spoken-style question about spending, offline."""
    today = today or dt.date.today()
    q = (query or "").lower().strip()
    frame = _prep(expenses)
    khata = udhar if udhar is not None else pd.DataFrame()

    if not q:
        return "Ask me something like 'is mahine kitna kharch hua?' or 'chai pe kitna gaya?'."
    if frame.empty and (khata is None or len(khata) == 0):
        return "You have not recorded anything yet. Log an expense and ask me again."

    # 1. Budget question
    if _has(q, BUDGET_WORDS):
        if budget <= 0:
            return "Set a monthly budget in the sidebar and I will track what is left."
        month_total = float(month_frame(frame, today)["amount"].sum())
        status = budget_status(month_total, budget, today)
        if status["level"] == "over":
            return (
                f"You are over budget by {inr(abs(status['remaining']))}. "
                f"{inr(month_total)} spent of {inr(budget)} this month."
            )
        return (
            f"{inr(status['remaining'])} left of your {inr(budget)} budget, "
            f"about {inr(status['per_day'])} a day for the remaining {status['days_left']} days."
        )

    # 2. Udhar / khata question
    if _has(q, UDHAR_WORDS) and khata is not None and len(khata) > 0:
        pending = khata[khata["status"] == "Pending"] if "status" in khata else khata
        # Partial payments mean the amount owed is the unpaid remainder.
        money = "remaining" if "remaining" in pending.columns else "amount"
        person = _person_from_query(q, khata)
        if person:
            person_rows = pending[pending["person"] == person]
            if person_rows.empty:
                settled = khata[(khata["person"] == person) & (khata["status"] == "Settled")]
                amount = float(settled["amount"].sum()) if not settled.empty else 0.0
                return f"Nothing pending with {person}. {inr(amount)} is already settled."
            owed = float(person_rows.loc[person_rows["type"].str.contains("Lent", na=False), money].sum())
            taken = float(person_rows[money].sum()) - owed
            parts = []
            if owed:
                parts.append(f"owes you {inr(owed)}")
            if taken:
                parts.append(f"you owe {inr(taken)}")
            return f"{person} {' and '.join(parts)}.".capitalize()
        if pending.empty:
            return "Every khata entry is settled. Nothing pending."
        owed_total = float(
            pending.loc[pending["type"].astype(str).str.contains("Lent", na=False), money].sum()
        )
        taken_total = float(pending[money].sum()) - owed_total
        return (
            f"{inr(owed_total)} is pending to come back to you from "
            f"{pending['person'].nunique()} people, and you owe {inr(taken_total)}."
        )

    scope, label = _scope(frame, q, today)
    scope_total = float(scope["amount"].sum())

    # 3. Averages / biggest / counts
    if _has(q, AVERAGE_WORDS):
        if scope.empty:
            return f"No expenses {label}."
        days = max((scope["date"].max() - scope["date"].min()).days + 1, 1)
        return f"Your average is {inr(scope_total / days)} per day {label} ({inr(scope_total)} over {days} days)."

    if _has(q, BIGGEST_WORDS):
        if scope.empty:
            return f"No expenses {label}."
        row = scope.loc[scope["amount"].idxmax()]
        return f"Your biggest expense {label} was {row['item']} at {inr(row['amount'])} on {row['date'].date()}."

    if _has(q, COUNT_WORDS):
        return f"You logged {len(scope)} expenses {label}, totalling {inr(scope_total)}."

    # 4. Category or item question inside the period
    topic = _topic(q)
    if topic:
        matched = scope[scope["category"] == topic]
        if matched.empty:
            return f"Nothing recorded in {topic} {label}."
        share = matched["amount"].sum() / scope_total * 100 if scope_total else 0
        return (
            f"{topic} cost you {inr(matched['amount'].sum())} {label} "
            f"across {len(matched)} entries ({share:.0f}% of your spending)."
        )

    if label == "overall" and _has(q, TOP_WORDS) and not frame.empty:
        by_category = frame.groupby("category")["amount"].sum().sort_values(ascending=False)
        top_three = ", ".join(f"{cat} {inr(amt)}" for cat, amt in by_category.head(3).items())
        return f"Your top categories overall are {top_three}."

    item_rows = _item_match(scope, q)
    if item_rows is not None and len(item_rows) > 0:
        names = ", ".join(item_rows["item"].astype(str).value_counts().head(3).index)
        return (
            f"You spent {inr(item_rows['amount'].sum())} on {names} {label} "
            f"across {len(item_rows)} entries."
        )

    # 5. Period total, or a friendly overall summary
    by_category = scope.groupby("category")["amount"].sum().sort_values(ascending=False)
    if scope.empty:
        return f"No expenses {label}."
    top_category = by_category.index[0]
    return (
        f"You spent {inr(scope_total)} {label} across {len(scope)} expenses. "
        f"{top_category} topped the list at {inr(by_category.iloc[0])}."
    )
