"""Multilingual parsing and Indian money formatting."""

from __future__ import annotations

import datetime as dt

from awaaz import insights
from awaaz.parser import parse_expenses

TODAY = dt.date(2026, 11, 11)


def test_native_script_date_words_leave_the_item_name():
    rows, _ = parse_expenses("నిన్న టీ 20", today=TODAY)
    assert rows[0]["item"] == "టీ"
    assert rows[0]["date"] == "2026-11-10"

    rows, _ = parse_expenses("कल चाय 20", today=TODAY)
    assert rows[0]["item"] == "चाय"
    assert rows[0]["date"] == "2026-11-10"


def test_romanised_telugu_dates_are_understood():
    rows, _ = parse_expenses("ninna tea 20", today=TODAY)
    assert rows[0]["item"] == "Tea"
    assert rows[0]["date"] == "2026-11-10"

    rows, _ = parse_expenses("monna auto 80", today=TODAY)
    assert rows[0]["date"] == "2026-11-09"


def test_devanagari_spelling_variants_of_dedh():
    for spelling in ("डेढ़ सौ", "ढेढ़ सौ", "देढ़ सौ"):
        rows, _ = parse_expenses(f"{spelling} खाना", today=TODAY)
        assert rows[0]["amount"] == 150.0, spelling


def test_telugu_script_sentence_end_to_end():
    rows, _ = parse_expenses("నిన్న టీ 20, ఆటో 80", today=TODAY)
    assert [(row["item"], row["amount"], row["category"]) for row in rows] == [
        ("టీ", 20.0, "Food"),
        ("ఆటో", 80.0, "Travel"),
    ]
    assert {row["date"] for row in rows} == {"2026-11-10"}


def test_mixed_language_sentence():
    rows, _ = parse_expenses("kal tea 20 and ఆటో 80", today=TODAY)
    assert [row["amount"] for row in rows] == [20.0, 80.0]
    assert [row["category"] for row in rows] == ["Food", "Travel"]


def test_indian_digit_grouping():
    assert insights.inr(1000) == "₹1,000"
    assert insights.inr(100000) == "₹1,00,000"
    assert insights.inr(1250000) == "₹12,50,000"
    assert insights.inr(10000000) == "₹1,00,00,000"
    assert insights.inr(20.5) == "₹20.50"
    assert insights.inr(-12.5) == "-₹12.50"
