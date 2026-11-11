"""Innovation features: spend forecast, anomaly detection, bank SMS capture."""

from __future__ import annotations

import datetime as dt

import pandas as pd

from awaaz import insights
from awaaz.parser import parse_bank_sms

TODAY = dt.date(2026, 11, 10)  # day 10 of a 30-day month


def frame(rows: list[dict]) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "id": index + 1,
                "date": row.get("date", "2026-11-10"),
                "item": row.get("item", "Item"),
                "amount": float(row["amount"]),
                "category": row.get("category", "Food"),
            }
            for index, row in enumerate(rows)
        ]
    )


# ---------------- forecast ----------------

def test_forecast_extrapolates_the_current_pace():
    pace = insights.forecast(frame([{"amount": 300}]), budget=0, today=TODAY)

    assert pace["spent"] == 300.0
    assert pace["pace"] == 30.0  # 300 over 10 elapsed days
    assert pace["projected"] == 900.0  # 30 days in November
    assert pace["cross_on"] is None


def test_forecast_names_the_day_the_budget_is_crossed():
    pace = insights.forecast(frame([{"amount": 300}]), budget=500, today=TODAY)

    assert pace["cross_on"] == dt.date(2026, 11, 16)  # 500 / 30 = day 16
    assert pace["over_by"] == 400.0


def test_forecast_stays_quiet_when_ahead_of_budget():
    pace = insights.forecast(frame([{"amount": 100}]), budget=5000, today=TODAY)
    assert pace["cross_on"] is None
    assert pace["over_by"] == 0.0


def test_forecast_handles_no_data_and_month_start():
    empty = frame([])
    assert insights.forecast(empty, budget=500, today=TODAY)["projected"] == 0.0

    first_day = insights.forecast(frame([{"amount": 100}]), budget=0, today=dt.date(2026, 11, 1))
    assert first_day["pace"] == 100.0
    assert first_day["projected"] == 3000.0


def test_forecast_question_is_answered_in_words():
    data = frame([{"amount": 300}])
    answer = insights.answer_query("what is the forecast for this month?", data, budget=500, today=TODAY)

    assert "₹900" in answer
    assert "16 Nov" in answer


# ---------------- anomalies ----------------

def test_outlier_against_the_category_median_is_flagged():
    data = frame(
        [
            {"amount": 100},
            {"amount": 100, "date": "2026-11-05"},
            {"amount": 100, "date": "2026-11-03"},
            {"amount": 500, "item": "Party", "date": "2026-11-08"},
        ]
    )

    flagged = insights.anomalies(data, today=TODAY)

    assert len(flagged) == 1
    assert flagged.iloc[0]["item"] == "Party"
    assert flagged.iloc[0]["times"] == 5.0
    assert flagged.iloc[0]["usual"] == 100.0


def test_small_categories_and_normal_amounts_are_not_flagged():
    two_entries = frame([{"amount": 100}, {"amount": 900, "date": "2026-11-02"}])
    assert insights.anomalies(two_entries, today=TODAY).empty

    steady = frame([{"amount": 100}, {"amount": 110}, {"amount": 105}])
    assert insights.anomalies(steady, today=TODAY).empty

    assert insights.anomalies(frame([]), today=TODAY).empty


# ---------------- bank SMS ----------------

def test_a_debit_sms_becomes_a_confirmable_entry():
    row = parse_bank_sms("Rs 450 debited at Swiggy", today=TODAY)

    assert row["amount"] == 450.0
    assert row["merchant"] == "Swiggy"
    assert row["item"] == "Swiggy"
    assert row["category"] == "Food"
    assert row["kind"] == "Expense"
    assert row["date"] == TODAY.isoformat()


def test_a_credit_sms_is_income_not_spending():
    row = parse_bank_sms("Rs 1,500 credited to your account", today=TODAY)

    assert row["amount"] == 1500.0
    assert row["kind"] == "Income"
    assert row["payment_mode"] == "Netbanking"


def test_sms_with_rupee_symbol_and_mode():
    row = parse_bank_sms("₹2,999 spent at DMart via UPI", today=TODAY)

    assert row["amount"] == 2999.0
    assert row["merchant"] == "DMart"
    assert row["category"] == "Groceries"
    assert row["payment_mode"] == "UPI"


def test_sms_without_an_amount_is_rejected():
    assert parse_bank_sms("Your OTP is 4821, do not share it", today=TODAY) is None
    assert parse_bank_sms("", today=TODAY) is None
    assert parse_bank_sms("Rs 0 debited", today=TODAY) is None
