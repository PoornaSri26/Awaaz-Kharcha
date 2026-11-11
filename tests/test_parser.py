"""Parser tests: number words, multi-item speech, udhar, relative dates."""

from __future__ import annotations

import datetime as dt

from awaaz import parser

TODAY = dt.date(2026, 11, 8)


def test_number_words_become_digits():
    assert parser.normalize_hinglish_numbers("dedh sau") == "150"
    assert parser.normalize_hinglish_numbers("dhai hazar") == "2500"
    assert parser.normalize_hinglish_numbers("paanch sau") == "500"
    assert parser.normalize_hinglish_numbers("2k") == "2000"
    assert parser.normalize_hinglish_numbers("डेढ़ सौ रुपये") == "150 रुपये"


def test_parses_multiple_expenses_in_one_breath():
    rows, udhar = parser.parse_expenses(
        "aaj chai 20, auto 80, lunch dedh sau", today=TODAY
    )

    assert udhar == []
    assert [row["amount"] for row in rows] == [20.0, 80.0, 150.0]
    assert [row["item"] for row in rows] == ["Chai", "Auto", "Lunch"]
    assert [row["category"] for row in rows] == ["Food", "Travel", "Food"]
    assert {row["date"] for row in rows} == {TODAY.isoformat()}


def test_comma_less_gnani_transcript_keeps_every_item():
    # Gnani Prisma really returns "चाय ₹20 ऑटो ₹80 लंच ₹150" for
    # "chai twenty rupees, auto eighty rupees, lunch one hundred fifty".
    rows, _ = parser.parse_expenses("चाय ₹20 ऑटो ₹80 लंच ₹150", today=TODAY)

    assert [row["amount"] for row in rows] == [20.0, 80.0, 150.0]
    assert [row["item"] for row in rows] == ["चाय", "ऑटो", "लंच"]
    assert [row["category"] for row in rows] == ["Food", "Travel", "Food"]

    rows, _ = parser.parse_expenses("chai 20 auto 80 lunch 150", today=TODAY)
    assert [row["amount"] for row in rows] == [20.0, 80.0, 150.0]

    rows, udhar = parser.parse_expenses(
        "chai 20 auto 80 lunch 150 aur Ravi ko 500 udhar diya", today=TODAY
    )
    assert [row["amount"] for row in rows] == [20.0, 80.0, 150.0]
    assert [row["amount"] for row in udhar] == [500.0]  # udhar stays out of expenses


def test_quantity_is_not_mistaken_for_the_amount():
    rows, _ = parser.parse_expenses("2 chai 20", today=TODAY)

    assert len(rows) == 1
    assert rows[0]["amount"] == 20.0


def test_relative_dates():
    rows, _ = parser.parse_expenses("kal metro 40", today=TODAY)
    assert rows[0]["date"] == "2026-11-07"

    rows, _ = parser.parse_expenses("parso auto 60", today=TODAY)
    assert rows[0]["date"] == "2026-11-06"


def test_telugu_and_english_sentences():
    rows, _ = parser.parse_expenses(
        "eeroju tiffin dosa 60, rapido bike 75, medicines 180", today=TODAY
    )
    assert len(rows) == 3
    assert [row["category"] for row in rows] == ["Food", "Travel", "Health"]

    rows, _ = parser.parse_expenses(
        "metro ticket 40, coffee 60, stationary 120, groceries 350", today=TODAY
    )
    assert len(rows) == 4
    assert rows[2]["category"] == "Education"
    assert rows[3]["category"] == "Groceries"


def test_udhar_entries_capture_the_person_and_direction():
    rows, udhar = parser.parse_expenses("Ravi ko 500 udhar diya", today=TODAY)

    assert rows == []
    assert len(udhar) == 1
    assert udhar[0]["person"] == "Ravi"
    assert udhar[0]["amount"] == 500.0
    assert udhar[0]["type"] == "Lent (Diya)"
    assert udhar[0]["status"] == "Pending"

    _, borrowed = parser.parse_expenses("Sneha se 250 liya", today=TODAY)
    assert borrowed[0]["person"] == "Sneha"
    assert borrowed[0]["type"] == "Borrowed (Liya)"


def test_expense_and_udhar_in_one_sentence():
    rows, udhar = parser.parse_expenses(
        "chai 20 aur Ravi ko 500 udhar diya", today=TODAY
    )
    assert len(rows) == 1
    assert len(udhar) == 1


def test_text_without_amounts_is_ignored():
    rows, udhar = parser.parse_expenses("how much did I spend today?", today=TODAY)
    assert rows == []
    assert udhar == []


def test_empty_input_is_safe():
    assert parser.parse_expenses("") == ([], [])
    assert parser.parse_expenses(None) == ([], [])


def test_category_normalization_handles_v1_names():
    assert parser.normalize_category("Food & Chai") == "Food"
    assert parser.normalize_category("Travel & Commute") == "Travel"
    assert parser.normalize_category("Bills") == "Bills"
    assert parser.normalize_category("something odd") == "Other"
    assert parser.normalize_category("") == "Other"
