"""Malayalam speech is understood like the other Indic languages."""

from __future__ import annotations

import datetime as dt

import pytest

from awaaz.parser import detect_kind, parse_expenses

TODAY = dt.date(2026, 11, 11)


def _rows(text: str, today: dt.date = TODAY) -> list[tuple[str, float, str, str]]:
    rows, _ = parse_expenses(text, today=today)
    return [(row["item"], row["amount"], row["category"], row["date"]) for row in rows]


def test_malayalam_sentence_with_ascii_digits():
    assert _rows("ഇന്ന് ചായ 20, ഓട്ടോ 80") == [
        ("ചായ", 20.0, "Food", "2026-11-11"),
        ("ഓട്ടോ", 80.0, "Travel", "2026-11-11"),
    ]


def test_malayalam_digits_and_yesterday():
    assert _rows("ഇന്നലെ ടീ ൨൦") == [("ടീ", 20.0, "Food", "2026-11-10")]


def test_malayalam_number_words():
    assert _rows("അഞ്ഞൂറ് മരുന്ന്") == [("മരുന്ന്", 500.0, "Health", "2026-11-11")]
    assert _rows("രണ്ടായിരം വാടക") == [("വാടക", 2000.0, "Bills", "2026-11-11")]


@pytest.mark.parametrize(
    "word, category",
    [
        ("പച്ചക്കറി", "Groceries"),
        ("ബിൽ", "Bills"),
        ("പുസ്തകം", "Education"),
        ("സിനിമ", "Fun"),
        ("മൊബൈൽ", "Shopping"),
    ],
)
def test_malayalam_category_words(word: str, category: str):
    rows, _ = parse_expenses(f"{word} 50", today=TODAY)
    assert rows[0]["category"] == category


def test_malayalam_conjunction_splits_entries():
    assert _rows("ചായ 20 ഒപ്പം ഓട്ടോ 80") == [
        ("ചായ", 20.0, "Food", "2026-11-11"),
        ("ഓട്ടോ", 80.0, "Travel", "2026-11-11"),
    ]


def test_malayalam_khata_keeps_the_name_clean():
    _expenses, udhar = parse_expenses("Ravi ന് 500 കടം കൊടുത്തു", today=TODAY)
    assert len(udhar) == 1
    assert udhar[0]["person"] == "Ravi"
    assert udhar[0]["amount"] == 500.0
    assert udhar[0]["type"].startswith("Lent")


def test_malayalam_income_word():
    rows, _ = parse_expenses("ശമ്പളം 30000 കിട്ടി", today=TODAY)
    assert rows[0]["kind"] == "Income"
    assert rows[0]["item"] == "ശമ്പളം"
    assert detect_kind("ശമ്പളം കിട്ടി") == "Income"
