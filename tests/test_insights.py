"""Insights and Q&A tests, including the empty-data crash the old build had."""

from __future__ import annotations

import datetime as dt

import pandas as pd

from awaaz import insights

TODAY = dt.date(2026, 11, 8)


def expenses() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {"id": 1, "date": "2026-11-08", "item": "Chai", "amount": 20.0, "category": "Food"},
            {"id": 2, "date": "2026-11-07", "item": "Auto", "amount": 80.0, "category": "Travel"},
            {"id": 3, "date": "2026-11-01", "item": "Lunch", "amount": 150.0, "category": "Food"},
            {"id": 4, "date": "2026-10-20", "item": "Movie", "amount": 200.0, "category": "Fun"},
        ]
    )


def empty_expenses() -> pd.DataFrame:
    return pd.DataFrame(columns=["id", "date", "item", "amount", "category"])


def khata() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {"date": "2026-11-05", "person": "Ravi", "amount": 500.0, "type": "Lent (Diya)", "status": "Pending"},
            {"date": "2026-11-06", "person": "Sneha", "amount": 250.0, "type": "Borrowed (Liya)", "status": "Pending"},
            {"date": "2026-10-30", "person": "Arjun", "amount": 300.0, "type": "Lent (Diya)", "status": "Settled"},
        ]
    )


def test_summary_numbers():
    stats = insights.summary(expenses(), TODAY)

    assert stats["today"] == 20.0
    assert stats["month"] == 250.0
    assert stats["week"] == 100.0
    assert stats["prev_month"] == 200.0
    assert stats["count"] == 4
    assert stats["top_category"] == "Food"


def test_summary_of_empty_dataframe():
    stats = insights.summary(empty_expenses(), TODAY)
    assert stats["month"] == 0.0
    assert stats["count"] == 0


def test_budget_status_levels():
    ok = insights.budget_status(250, 1000, TODAY)
    assert ok["level"] == "ok"
    assert ok["remaining"] == 750
    assert ok["days_left"] == 23

    assert insights.budget_status(950, 1000, TODAY)["level"] == "alert"
    assert insights.budget_status(820, 1000, TODAY)["level"] == "nudge"
    over = insights.budget_status(1100, 1000, TODAY)
    assert over["level"] == "over"
    assert over["remaining"] == -100
    assert insights.budget_status(500, 0, TODAY)["level"] == "off"


def test_daily_totals_are_zero_filled():
    daily = insights.daily_totals(expenses(), days=14, today=TODAY)
    assert len(daily) == 14
    # 14-day window starts 2026-10-26, so it also covers the Nov 1 lunch.
    assert daily["amount"].sum() == 250.0
    assert daily.loc[pd.Timestamp("2026-11-03"), "amount"] == 0.0
    assert daily.loc[pd.Timestamp("2026-11-08"), "amount"] == 20.0


def test_category_and_top_items():
    totals = insights.category_totals(expenses(), TODAY)
    assert totals.index[0] == "Food"
    assert totals.loc["Food"] == 170.0

    best = insights.top_items(expenses(), 2, TODAY)
    assert best.iloc[0]["item"] == "Lunch"
    assert len(best) == 2


def test_weekly_insight_mentions_the_top_category():
    # Last 7 days: Chai 20 (Food) + Auto 80 (Travel) -> Travel is the top bucket.
    text = insights.weekly_insight(expenses(), TODAY)
    assert "₹100" in text
    assert "Travel" in text
    assert "2-day logging streak" in text

    assert "Log your first expense" in insights.weekly_insight(empty_expenses(), TODAY)


def test_logging_streak():
    assert insights.logging_streak(expenses(), TODAY) == 2
    assert insights.logging_streak(empty_expenses(), TODAY) == 0


def test_answer_month_question():
    answer = insights.answer_query("is mahine kitna kharch hua?", expenses(), khata(), today=TODAY)
    assert "₹250" in answer
    assert "Food" in answer


def test_answer_category_question():
    answer = insights.answer_query("chai pe kitna gaya?", expenses(), khata(), today=TODAY)
    assert "Food" in answer
    assert "₹170" in answer


def test_answer_budget_question():
    answer = insights.answer_query("budget kitna bacha?", expenses(), khata(), budget=1000, today=TODAY)
    assert "750" in answer
    assert "budget" in answer.lower()


def test_answer_budget_without_a_budget_set():
    answer = insights.answer_query("budget kitna bacha?", expenses(), khata(), budget=0, today=TODAY)
    assert "Set a monthly budget" in answer


def test_answer_udhar_questions():
    answer = insights.answer_query("ravi ko kitna udhar dena hai?", expenses(), khata(), today=TODAY)
    assert "Ravi" in answer
    assert "₹500" in answer

    total = insights.answer_query("how much udhar is pending?", expenses(), khata(), today=TODAY)
    assert "₹500" in total and "₹250" in total


def test_answer_biggest_and_average():
    biggest = insights.answer_query("sabse mehnga kharch?", expenses(), khata(), today=TODAY)
    assert "Movie" in biggest

    average = insights.answer_query("per day average?", expenses(), khata(), today=TODAY)
    assert "per day" in average


def test_answer_with_no_data_does_not_crash():
    empty = empty_expenses()
    assert "not recorded anything yet" in insights.answer_query("is mahine kitna kharch hua?", empty, empty)

    # The v1 crash: khata data exists but the expense frame is empty.
    answer = insights.answer_query("this month", empty, khata(), today=TODAY)
    assert isinstance(answer, str) and answer


def test_answer_blank_query():
    assert "Ask me something" in insights.answer_query("   ", expenses(), khata(), today=TODAY)


def test_inr_formatting():
    assert insights.inr(1500) == "₹1,500"
    assert insights.inr(0) == "₹0"
