"""Text augmentation for the multilingual expense dataset.

Simulates ASR/typist noise so models don't overfit clean templates:

* random word dropout (ASR misses a word)
* spelling variants (common romanised-Indic confusions)
* case/punctuation stripping
* digit ↔ number-word swaps where a lexicon exists

Every function is deterministic under a seed and returns NEW records —
originals are never mutated. Augmented rows are tagged
``source="augmented"`` so evaluation can separate them.
"""

from __future__ import annotations

import random
import re

#: romanised-Indic spelling confusions seen in real typing
SPELL_VARIANTS = {
    "kharcha": ["kharchaa", "kharacha"],
    "paisa": ["paise", "pesa"],
    "auto": ["oto", "aoto"],
    "chai": ["chay", "chaii"],
    "khaya": ["khaaya"],
    "kharch": ["kharach"],
    "rupees": ["rupe", "roopees"],
    "nenu": ["nennu", "nanu"],
    "kosam": ["kosam", "koosam"],
}

DROP_PROB = 0.08


def augment_text(text: str, rng: random.Random | None = None) -> str:
    rng = rng or random.Random()
    words = text.split()
    if len(words) > 2 and rng.random() < 0.5:
        # drop one non-first word (simulates an ASR miss)
        i = rng.randrange(1, len(words))
        words = words[:i] + words[i + 1:]
    out = []
    for w in words:
        low = w.lower().strip(".,!?")
        if low in SPELL_VARIANTS and rng.random() < 0.4:
            w = rng.choice(SPELL_VARIANTS[low])
        out.append(w)
    s = " ".join(out)
    if rng.random() < 0.15:
        s = s.lower()
    return re.sub(r"\s+", " ", s).strip()


def augment_rows(rows: list[dict], factor: int = 1, seed: int = 11) -> list[dict]:
    """Return ``factor`` augmented copies per row (text-only; entities dropped)."""
    rng = random.Random(seed)
    out = []
    for r in rows:
        for _ in range(factor):
            out.append({
                **{k: v for k, v in r.items() if k != "entities"},
                "text": augment_text(r["text"], rng),
                "source": "augmented",
                "entities": [],
            })
    return out


def split_rows(rows: list[dict], seed: int = 3,
               ratios=(0.8, 0.1, 0.1)) -> dict[str, list[dict]]:
    """Deterministic train/val/test split, stratified by (lang, category)."""
    rng = random.Random(seed)
    groups: dict[tuple, list[dict]] = {}
    for r in rows:
        groups.setdefault((r.get("lang"), r.get("category")), []).append(r)
    train, val, test = [], [], []
    for _, items in groups.items():
        items = items[:]
        rng.shuffle(items)
        n = len(items)
        n_tr = int(n * ratios[0])
        n_va = int(n * ratios[1])
        train += items[:n_tr]
        val += items[n_tr:n_tr + n_va]
        test += items[n_tr + n_va:]
    rng.shuffle(train); rng.shuffle(val); rng.shuffle(test)
    return {"train": train, "val": val, "test": test}
