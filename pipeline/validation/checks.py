"""Dataset validation — schema + quality gates (swap for Great Expectations/TFDV at scale)."""
from __future__ import annotations
import json
from pathlib import Path

REQUIRED = {"text", "lang", "category"}
VALID_LANGS = {"en", "hi", "te", "ta", "hinglish"}

def validate_rows(rows: list[dict]) -> dict:
    errors = []
    for i, r in enumerate(rows):
        missing = REQUIRED - set(r)
        if missing:
            errors.append(f"row {i}: missing {missing}")
        elif r.get("lang") not in VALID_LANGS:
            errors.append(f"row {i}: bad lang {r.get('lang')}")
        if not str(r.get("text", "")).strip():
            errors.append(f"row {i}: empty text")
    return {"n": len(rows), "errors": len(errors), "error_rows": errors[:20], "ok": not errors}

def validate_jsonl(path: str) -> dict:
    rows = [json.loads(l) for l in Path(path).read_text(encoding="utf-8").splitlines() if l.strip()]
    return validate_rows(rows)
