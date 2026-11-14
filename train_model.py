"""Train (or retrain) the expense-category classifier.

    python train_model.py            # lexicon + user-labelled rows from data/awaaz.db
    python train_model.py --lexicon-only
    python train_model.py --db path/to/awaaz.db --out models/category_clf.joblib

Training data comes from two sources:

1. **Lexicon templates** — every keyword in ``awaaz.parser.CATEGORIES`` is
   wrapped in a few Hinglish/English sentence frames, giving broad coverage of
   the ten UI languages at zero annotation cost.
2. **User corrections** — rows in the SQLite store carry the category the
   user confirmed or edited in the History tab. These are the highest-value
   labels; as the app is used, retraining improves automatically.

The fitted pipeline is saved to ``models/category_clf.joblib`` (git-ignored).
"""

from __future__ import annotations

import argparse
import json
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from awaaz import config, nlp
from awaaz.parser import CATEGORIES, EXPENSE_CATEGORIES

#: Sentence frames that make bare keywords look like real user utterances.
FRAMES = [
    "aaj {kw} 50",
    "kal {kw} 120",
    "{kw} kharch 200",
    "paid for {kw}",
    "{kw} expense today",
    "{kw} bill 300",
    "bought {kw} 150",
    "{kw} 80 by cash",
]


def lexicon_samples() -> tuple[list[str], list[str]]:
    texts, labels = [], []
    rng = random.Random(7)
    for cat in EXPENSE_CATEGORIES:
        words = CATEGORIES.get(cat, [])
        for kw in words:
            kw = str(kw).strip()
            if not kw:
                continue
            # the bare keyword plus a couple of frames per keyword
            texts.append(kw)
            labels.append(cat)
            for frame in rng.sample(FRAMES, 2):
                texts.append(frame.format(kw=kw))
                labels.append(cat)
    return texts, labels


def store_samples(db_path: str | None) -> tuple[list[str], list[str]]:
    if not db_path:
        return [], []
    from awaaz.pipeline import iter_labeled_expenses
    from awaaz.store import Store

    store = Store(db_path, migrate_legacy=False)
    texts, labels = [], []
    for rec in iter_labeled_expenses(store):
        texts.append(rec["text"])
        labels.append(rec["label"])
    return texts, labels


def main() -> int:
    ap = argparse.ArgumentParser(description="Train the Awaaz Kharcha category classifier")
    ap.add_argument("--lexicon-only", action="store_true", help="skip the SQLite store")
    ap.add_argument("--db", default=None, help="path to awaaz.db (default: data/awaaz.db if present)")
    ap.add_argument("--out", default=None, help="output model path")
    ap.add_argument("--seed", type=int, default=42)
    args = ap.parse_args()

    db = args.db or (str(config.DEFAULT_DB_PATH) if config.DEFAULT_DB_PATH.exists() else None)
    if args.lexicon_only:
        db = None

    texts, labels = lexicon_samples()
    n_lex = len(texts)
    u_texts, u_labels = store_samples(db)
    texts += u_texts
    labels += u_labels

    print(f"training examples: {len(texts)} total "
          f"({n_lex} lexicon + {len(u_texts)} user-labelled, db={db or 'none'})")
    if not texts:
        print("no training data — nothing to do", file=sys.stderr)
        return 1

    pipe, report = nlp.train(texts, labels, seed=args.seed)
    out = nlp.save_model(pipe, args.out)

    print(json.dumps({k: v for k, v in report.items() if k != "per_class"}, indent=2))
    if report.get("per_class"):
        print("\nper-class F1 (held-out):")
        for cls, m in sorted(report["per_class"].items()):
            if cls in ("accuracy", "macro avg", "weighted avg"):
                continue
            print(f"  {cls:12s}  P={m['precision']:.2f}  R={m['recall']:.2f}  F1={m['f1-score']:.2f}  n={int(m['support'])}")
    print(f"\nmodel saved -> {out}")
    print("classes:", ", ".join(map(str, pipe.classes_)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
