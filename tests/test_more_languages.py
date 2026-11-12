"""Bengali, Tamil and Kannada speech lands in the right categories."""

from __future__ import annotations

import datetime as dt

from awaaz.parser import parse_expenses

TODAY = dt.date(2026, 11, 11)


def _rows(text: str, today: dt.date = TODAY) -> list[tuple[str, float, str, str]]:
    rows, _ = parse_expenses(text, today=today)
    return [(row["item"], row["amount"], row["category"], row["date"]) for row in rows]


def test_bengali_sentence_with_native_digits():
    assert _rows("আজ চা ২০, অটো ৮০") == [
        ("চা", 20.0, "Food", "2026-11-11"),
        ("অটো", 80.0, "Travel", "2026-11-11"),
    ]


def test_bengali_number_words_and_categories():
    assert _rows("খাবার পাঁচশো") == [("খাবার", 500.0, "Food", "2026-11-11")]
    assert _rows("গতকাল ওষুধ ১০০") == [("ওষুধ", 100.0, "Health", "2026-11-10")]


def test_tamil_sentence_and_relative_date():
    assert _rows("நேற்று டீ 20, ஆட்டோ 80") == [
        ("டீ", 20.0, "Food", "2026-11-10"),
        ("ஆட்டோ", 80.0, "Travel", "2026-11-10"),
    ]


def test_tamil_number_words():
    assert _rows("ஆயிரம் வாடகை") == [("வாடகை", 1000.0, "Bills", "2026-11-11")]
    assert _rows("மருந்து இருநூறு") == [("மருந்து", 200.0, "Health", "2026-11-11")]


def test_kannada_sentence_with_native_digits():
    assert _rows("ಇಂದು ಟೀ ೨೦, ಆಟೋ ೮೦") == [
        ("ಟೀ", 20.0, "Food", "2026-11-11"),
        ("ಆಟೋ", 80.0, "Travel", "2026-11-11"),
    ]


def test_kannada_number_words_and_categories():
    assert _rows("ಮೂವತ್ತು ಪುಸ್ತಕ") == [("ಪುಸ್ತಕ", 30.0, "Education", "2026-11-11")]
    assert _rows("ನಿನ್ನೆ ತರಕಾರಿ 60") == [("ತರಕಾರಿ", 60.0, "Groceries", "2026-11-10")]


def test_khata_words_in_the_new_scripts():
    _expenses, udhar = parse_expenses("Ravi ಗೆ 500 ಸಾಲ ಕೊಟ್ಟೆ", today=TODAY)
    assert len(udhar) == 1
    assert udhar[0]["amount"] == 500.0
    assert udhar[0]["type"].startswith("Lent")
