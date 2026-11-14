"""Generate the starter multilingual expense dataset (SYNTHETIC).

Every record is template-generated — NOT human-recorded speech. Fields:

    {"id", "text", "lang", "category", "entities": [{start,end,label,text}]}

Entity labels: AMOUNT, ITEM, PAYEE, DATE. Char spans let train_ner.py build
BIO tags deterministically. Real user data should be added via
nlp/data/annotated/*.jsonl (see ANNOTATION_GUIDE.md).

    python nlp/data/gen_synthetic.py --out nlp/data/synthetic.jsonl --per-lang 60
"""

from __future__ import annotations

import argparse
import json
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from awaaz.parser import CATEGORIES, EXPENSE_CATEGORIES

LANGS = ["en", "hi", "te", "ta", "hinglish"]  # hinglish = romanised code-mixed

#: amount surface forms per lang (digits + a few number words)
AMOUNTS = {
    "en": ["50", "120", "250", "380", "450", "99", "fifty", "two hundred"],
    "hi": ["50", "120", "250", "पचास", "दो सौ", "साढ़े तीन सौ"],
    "te": ["50", "120", "250", "యాభై", "రెండు వందలు"],
    "ta": ["50", "120", "250", "ஐம்பது", "இருநூறு"],
    "hinglish": ["50", "120", "250", "dedh sau", "pachaas", "do sau"],
}
DATES = {
    "en": ["today", "yesterday"],
    "hi": ["aaj", "kal"],
    "te": ["eeroju", "ninna"],
    "ta": ["inru", "netru"],
    "hinglish": ["aaj", "kal", "parso"],
}
PAYEES = ["Ravi", "Priya", "Auto wala", "Cafe owner", " Ravi ko ", "అన్నయ్య"]

#: templates per lang — {item} {amount} {payee} {date} slots
TEMPLATES = {
    "en": [
        "spent {amount} on {item}",
        "{item} cost {amount} {date}",
        "bought {item} for {amount}",
        "{payee} charged me {amount} for {item}",
        "{date} {item} {amount}",
    ],
    "hi": [
        "{item} पर {amount} खर्च किए",
        "{amount} का {item} {date} खरीदा",
        "{payee} ने {item} के {amount} लिए",
        "{date} {item} में {amount} गए",
    ],
    "te": [
        "{item} ki {amount} dabbu {date} vesanu",
        "{amount} anukuntuna {item} {payee} iccinadu",
        "{date} {item} kosam {amount} kharchu chesanu",
    ],
    "ta": [
        "{item} ku {amount} solvom {date}",
        "{payee} {item} ku {amount} kekararu",
        "{date} {item} ku {amount} selavu",
    ],
    "hinglish": [
        "aaj {item} {amount} kharch hua",
        "{item} ka {amount} {date} diya",
        "{payee} ko {amount} {item} ke liye diye",
        "kal {item} {amount} spent kiya",
        "{item} par {amount} lagaye {date}",
    ],
}


def _items_for(cat: str, lang: str, n: int, rng) -> list[str]:
    """Pick item keywords; for non-en/hi prefer native-script lexicon words."""
    words = [str(w) for w in CATEGORIES.get(cat, [])]
    return rng.sample(words, min(n, len(words)))


def _fill(template: str, slots: dict[str, str]) -> tuple[str, list[dict]]:
    """Substitute {slots}, returning text + entity char spans."""
    text, ents, cursor = "", [], 0
    # find {slot} placeholders in order of appearance
    import re

    for m in re.finditer(r"\{(item|amount|payee|date)\}", template):
        label = m.group(1).upper()
        val = slots[label.lower()]
        # rebuild: text up to placeholder + value
        prefix = template[cursor:m.start()]
        text += prefix + val
        start = len(text) - len(val)
        ents.append({"start": start, "end": start + len(val),
                     "label": label, "text": val})
        cursor = m.end()
    text += template[cursor:]
    return text, ents


def generate(per_lang: int = 60, seed: int = 7) -> list[dict]:
    rng = random.Random(seed)
    rows = []
    rid = 0
    for lang in LANGS:
        made = 0
        tries = 0
        while made < per_lang and tries < per_lang * 30:
            tries += 1
            cat = rng.choice(EXPENSE_CATEGORIES)
            items = _items_for(cat, lang, 1, rng)
            if not items:
                continue
            tmpl = rng.choice(TEMPLATES[lang])
            slots = {
                "item": items[0],
                "amount": rng.choice(AMOUNTS[lang]),
                "payee": rng.choice(PAYEES).strip(),
                "date": rng.choice(DATES[lang]),
            }
            # keep templates that only use slots present in the dict
            try:
                text, ents = _fill(tmpl, slots)
            except Exception:
                continue
            rows.append({
                "id": f"syn-{rid:05d}", "text": text, "lang": lang,
                "category": cat, "entities": ents,
                "source": "synthetic-template",
            })
            rid += 1
            made += 1
    return rows


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="nlp/data/synthetic.jsonl")
    ap.add_argument("--per-lang", type=int, default=60)
    args = ap.parse_args()
    rows = generate(args.per_lang)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", encoding="utf-8") as fh:
        for r in rows:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")
    langs = sorted({r["lang"] for r in rows})
    print(f"wrote {len(rows)} rows -> {out}  langs={langs}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
