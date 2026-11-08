"""Runtime configuration for Awaaz Kharcha.

Everything that depends on the environment (API key, database path, language
codes) lives here so the rest of the code stays importable in tests.
"""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
DEFAULT_DB_PATH = DATA_DIR / "awaaz.db"

# Legacy CSV files from v1 of the app. They are imported once, then renamed.
LEGACY_EXPENSE_CSV = PROJECT_ROOT / "expenses.csv"
LEGACY_UDHAR_CSV = PROJECT_ROOT / "udhar_khata.csv"

GNANI_API_URL = os.getenv("GNANI_API_URL", "https://api.vachana.ai/stt/v3")

#: UI language picker -> Gnani language code
LANGUAGES = {
    "Hinglish": "hi-IN",
    "తెలుగు": "te-IN",
    "English": "en-IN",
}

DEFAULT_LANGUAGE = "Hinglish"

#: Budget nudge thresholds (percent of the monthly budget already spent)
NUDGE_PCT = 80
ALERT_PCT = 90


def api_key() -> str:
    """Return the Gnani API key from the environment or Streamlit secrets."""
    key = os.getenv("GNANI_API_KEY", "").strip()
    if key:
        return key
    try:  # pragma: no cover - only available inside a Streamlit runtime
        import streamlit as st

        return str(st.secrets.get("GNANI_API_KEY", "")).strip()
    except Exception:
        return ""


def api_key_configured() -> bool:
    return bool(api_key())


def db_path() -> Path:
    """Path of the SQLite database, overridable for tests and deployments."""
    override = os.getenv("AWAAZ_DB_PATH", "").strip()
    return Path(override) if override else DEFAULT_DB_PATH
