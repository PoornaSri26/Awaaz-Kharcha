"""The Bengali, Tamil and Kannada interfaces must be as complete as the others."""

import re

import pytest

from awaaz import config, insights
from awaaz.parser import parse_expenses

NEW_LANGS = ("bn-IN", "ta-IN", "kn-IN")


def _ui():
    """Import app.py lazily.

    Importing the Streamlit script leaves form/popover state behind in the
    runtime, which upsets the AppTest smoke test when the whole suite runs in
    one process, so only pull it in when these tests actually need it.
    """
    import app

    return app


def test_languages_are_selectable():
    codes = set(config.LANGUAGES.values())
    for lang in NEW_LANGS:
        assert lang in codes


def test_core_ui_keys_match_hindi():
    base = set(_ui().UI["hi-IN"])
    for lang in NEW_LANGS:
        assert set(_ui().UI[lang]) == base, f"{lang} core keys differ"


def test_extra_ui_keys_match_hindi():
    base = set(_ui().EXTRA["hi-IN"])
    for lang in NEW_LANGS:
        assert set(_ui().EXTRA[lang]) == base, f"{lang} extra keys differ"


def test_every_category_is_named():
    base = set(_ui().CAT_LABELS["hi-IN"])
    for lang in NEW_LANGS:
        assert set(_ui().CAT_LABELS[lang]) == base, f"{lang} is missing categories"


def test_insight_prose_is_translated():
    base = set(insights._I18N["en-IN"])
    english = insights._I18N["en-IN"]
    for lang in NEW_LANGS:
        assert set(insights._I18N[lang]) == base, f"{lang} insight keys differ"
        assert insights._tr(lang)["no_history"] != english["no_history"]


def test_insight_sentences_format():
    for lang in NEW_LANGS:
        prose = insights._tr(lang)
        assert prose["weekly"].format(
            total="₹100", top="খাবার", amount="₹100", item="", streak=""
        )
        assert prose["budget_left"].format(
            left="₹10", budget="₹20", per_day="₹1", days=3
        )


@pytest.mark.parametrize("lang", NEW_LANGS)
def test_example_phrases_actually_parse(lang):
    phrase = re.search(r'"([^"]+)"', _ui().UI[lang]["example"]).group(1)
    rows, _ = parse_expenses(phrase)
    assert rows, f"{lang} example does not parse: {phrase}"
    assert all(row["amount"] > 0 for row in rows)


def test_weekday_names_exist():
    for lang in NEW_LANGS:
        names = insights.WEEKDAY_NAMES[lang]
        assert set(names) == set(insights.WEEKDAY_NAMES["en-IN"])
