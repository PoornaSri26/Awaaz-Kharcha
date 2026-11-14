"""Batch data pipeline helpers.

Turns the app's local SQLite store into labelled datasets that can be
re-ingested by offline training jobs (``train_model.py``) or shipped to a
Spark cluster unchanged — every record is a self-describing JSON line:

    {"text": "swiggy biryani 350", "label": "Food", "source": "user", "ts": "..."}

Schema is intentionally flat and Spark-friendly (string text, string label,
string source, ISO timestamp) so the same JSONL can be read by
``spark.read.json`` for large-scale retraining or analytics.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable

from . import config
from .nlp import CLF_LABELS


def iter_labeled_expenses(store) -> Iterable[dict]:
    """Yield ``{text, label}`` records from a :class:`awaaz.store.Store`.

    Only rows whose category is one of the classifier labels are emitted —
    user edits in the History tab are the highest-quality labels we have.
    """
    df = store.expenses()
    if df is None or df.empty:
        return
    for _, row in df.iterrows():
        text = str(row.get("item") or "").strip()
        label = str(row.get("category") or "").strip()
        if text and label in CLF_LABELS:
            yield {
                "text": text,
                "label": label,
                "source": "user",
                "merchant": row.get("merchant") or "",
                "amount": row.get("amount"),
                "ts": str(row.get("date") or ""),
            }


def export_training_jsonl(
    store=None, out_path: str | Path | None = None
) -> tuple[int, Path]:
    """Write labelled expense rows to JSONL for offline/Spark retraining.

    Returns ``(n_records, path)``.
    """
    if store is None:
        from .store import Store

        store = Store(config.DEFAULT_DB_PATH, migrate_legacy=False)
    out = Path(out_path or config.DATA_DIR / "training_data.jsonl")
    out.parent.mkdir(parents=True, exist_ok=True)
    n = 0
    with out.open("w", encoding="utf-8") as fh:
        for rec in iter_labeled_expenses(store):
            fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
            n += 1
    return n, out
