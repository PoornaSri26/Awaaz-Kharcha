"""ML semantic layer for Awaaz Kharcha.

A trainable text classifier that predicts the expense *category* from a
free-form, code-mixed item description. It complements the deterministic rule
parser in :mod:`awaaz.parser`:

* the parser stays the source of truth for amounts, dates and udhar rows;
* this module is consulted when the lexicon cannot place an item (``Other``)
  or when a caller explicitly wants a model suggestion.

Model
-----
``TfidfVectorizer(analyzer="char_wb", ngram_range=(2, 5))`` feeding a
``LogisticRegression``. Character n-grams work well for code-mixed Indian
text: they capture sub-word morphology in Telugu/Tamil script, romanised
Hinglish, and English without language-specific tokenisation.

The fitted pipeline is persisted with joblib under ``models/`` (git-ignored;
retrain with ``python train_model.py``). Everything degrades gracefully: if
scikit-learn or the model file is missing, :func:`suggest_category` simply
returns the caller's fallback.
"""

from __future__ import annotations

import os
from pathlib import Path

import joblib
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_MODEL_PATH = PROJECT_ROOT / "models" / "category_clf.joblib"

#: Minimum predicted probability before the model overrides the fallback.
DEFAULT_THRESHOLD = 0.50

#: Labels the classifier is allowed to emit (udhar is handled by the parser).
CLF_LABELS = [
    "Food", "Travel", "Groceries", "Bills", "Health",
    "Shopping", "Fun", "Education", "Other",
]


def build_pipeline() -> Pipeline:
    """Fresh, unfitted classifier pipeline."""
    return Pipeline(
        [
            (
                "tfidf",
                TfidfVectorizer(
                    analyzer="char_wb",
                    ngram_range=(2, 5),
                    min_df=1,
                    sublinear_tf=True,
                    lowercase=True,
                ),
            ),
            (
                "clf",
                LogisticRegression(
                    max_iter=1000,
                    class_weight="balanced",
                    solver="lbfgs",
                ),
            ),
        ]
    )


def train(
    texts: list[str], labels: list[str], *, seed: int = 42
) -> tuple[Pipeline, dict]:
    """Fit the pipeline and return it plus a small evaluation report.

    Splits stratified 80/20 internally so callers always get held-out metrics.
    """
    from sklearn.metrics import accuracy_score, classification_report
    from sklearn.model_selection import train_test_split

    pairs = [(t, l) for t, l in zip(texts, labels) if t and l in CLF_LABELS]
    if len(pairs) < 20:
        raise ValueError(
            f"Need at least ~20 labelled examples, got {len(pairs)}. "
            "Run with lexicon-generated data or collect user corrections first."
        )
    t, l = zip(*pairs)
    pipe = build_pipeline()
    if len(set(l)) >= 2 and len(pairs) >= 40:
        tr_txt, te_txt, tr_y, te_y = train_test_split(
            list(t), list(l), test_size=0.2, random_state=seed, stratify=list(l)
        )
        pipe.fit(tr_txt, tr_y)
        pred = pipe.predict(te_txt)
        report = {
            "n_train": len(tr_txt),
            "n_test": len(te_txt),
            "accuracy": round(float(accuracy_score(te_y, pred)), 4),
            "per_class": classification_report(
                te_y, pred, output_dict=True, zero_division=0
            ),
        }
        # Refit on all data for the shipped model.
        pipe.fit(list(t), list(l))
    else:
        pipe.fit(list(t), list(l))
        report = {"n_train": len(pairs), "n_test": 0, "accuracy": None, "per_class": {}}
    return pipe, report


def save_model(pipe: Pipeline, path: str | Path | None = None) -> Path:
    path = Path(path or os.getenv("AWAAZ_MODEL_PATH", DEFAULT_MODEL_PATH))
    path.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(pipe, path)
    return path


class CategoryClassifier:
    """Lazy-loading wrapper around the persisted pipeline."""

    def __init__(self, path: str | Path | None = None, threshold: float = DEFAULT_THRESHOLD):
        self.path = Path(path or os.getenv("AWAAZ_MODEL_PATH", DEFAULT_MODEL_PATH))
        self.threshold = threshold
        self._pipe: Pipeline | None = None
        self._tried = False

    @property
    def available(self) -> bool:
        return self._load() is not None

    def _load(self) -> Pipeline | None:
        if self._tried:
            return self._pipe
        self._tried = True
        try:
            if self.path.exists():
                self._pipe = joblib.load(self.path)
        except Exception:
            self._pipe = None
        return self._pipe

    def predict_proba(self, text: str) -> dict[str, float]:
        """Return ``{label: probability}`` for a description, or ``{}``."""
        pipe = self._load()
        if pipe is None or not (text or "").strip():
            return {}
        try:
            proba = pipe.predict_proba([text])[0]
            labels = pipe.classes_
            return {str(l): float(p) for l, p in zip(labels, proba)}
        except Exception:
            return {}

    def predict(self, text: str) -> tuple[str | None, float]:
        """Return ``(label, confidence)`` or ``(None, 0.0)``."""
        proba = self.predict_proba(text)
        if not proba:
            return None, 0.0
        label = max(proba, key=proba.get)
        return label, proba[label]

    def suggest_category(self, text: str, fallback: str) -> str:
        """ML suggestion if confident enough, else *fallback* unchanged."""
        label, conf = self.predict(text)
        if label and conf >= self.threshold and label != "Other":
            return label
        return fallback


_default = CategoryClassifier()


def suggest_category(text: str, fallback: str) -> str:
    """Module-level convenience wrapper using the default model path."""
    return _default.suggest_category(text, fallback)


def model_info() -> dict:
    """Small introspection helper for the UI / diagnostics."""
    pipe = _default._load()
    if pipe is None:
        return {"available": False, "path": str(_default.path)}
    try:
        n_features = pipe.named_steps["tfidf"].vocabulary_.__len__()
    except Exception:
        n_features = None
    return {
        "available": True,
        "path": str(_default.path),
        "classes": list(map(str, pipe.classes_)),
        "n_features": n_features,
        "threshold": _default.threshold,
    }
