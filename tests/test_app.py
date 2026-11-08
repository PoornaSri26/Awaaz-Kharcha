"""Smoke test that the Streamlit UI boots and the typed path saves rows.

Streamlit's AppTest runs app.py in a simulated runtime, so this catches broken
widget wiring (session-state keys, save handlers) that unit tests miss.
"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

import pytest

pytest.importorskip("streamlit.testing.v1")

from streamlit.testing.v1 import AppTest  # noqa: E402

from awaaz.store import Store  # noqa: E402

# The app reads AWAAZ_DB_PATH when it creates its cached store, so point it at a
# throwaway database before the script runs.
DB_PATH = Path(tempfile.mkdtemp(prefix="awaaz-ui-")) / "ui.db"
os.environ["AWAAZ_DB_PATH"] = str(DB_PATH)


def test_typed_sentence_saves_expenses():
    app = AppTest.from_file("app.py", default_timeout=60).run()
    assert not app.exception

    app.text_area(key="typed_text").set_value("chai 20, auto 80, lunch dedh sau").run()
    assert not app.exception

    app.button(key="typed_save").click().run()
    assert not app.exception

    frame = Store(DB_PATH, migrate_legacy=False).expenses()
    assert len(frame) == 3
    assert sorted(frame["amount"].tolist()) == [20.0, 80.0, 150.0]
    assert set(frame["source"]) == {"typed"}
