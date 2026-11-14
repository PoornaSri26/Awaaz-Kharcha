"""Tests for the ML semantic layer (awaaz.nlp) and data pipeline."""

from __future__ import annotations

import json

import pytest

from awaaz import nlp
from awaaz.parser import CATEGORIES, EXPENSE_CATEGORIES, categorize_smart


def _toy_dataset():
    """Small labelled set covering every class."""
    texts, labels = [], []
    for cat in EXPENSE_CATEGORIES:
        for kw in CATEGORIES.get(cat, [])[:6]:
            texts.append(f"aaj {kw} 50")
            labels.append(cat)
    return texts, labels


class TestClassifierTraining:
    def test_train_and_predict_roundtrip(self, tmp_path):
        pytest.importorskip("sklearn")
        texts, labels = _toy_dataset()
        pipe, report = nlp.train(texts, labels, seed=1)
        assert report["n_train"] > 0
        clf = nlp.CategoryClassifier(path=tmp_path / "m.joblib")
        nlp.save_model(pipe, tmp_path / "m.joblib")
        assert clf.available
        label, conf = clf.predict("aaj chai 50")
        assert label == "Food"
        assert conf > 0.0

    def test_suggest_respects_threshold_and_fallback(self, tmp_path):
        pytest.importorskip("sklearn")
        texts, labels = _toy_dataset()
        pipe, _ = nlp.train(texts, labels, seed=1)
        nlp.save_model(pipe, tmp_path / "m.joblib")
        clf = nlp.CategoryClassifier(path=tmp_path / "m.joblib", threshold=0.99)
        # impossible threshold -> fallback always wins
        assert clf.suggest_category("chai", "Travel") == "Travel"
        clf2 = nlp.CategoryClassifier(path=tmp_path / "m.joblib", threshold=0.1)
        assert clf2.suggest_category("chai", "Travel") == "Food"

    def test_missing_model_falls_back(self, tmp_path):
        clf = nlp.CategoryClassifier(path=tmp_path / "nope.joblib")
        assert not clf.available
        assert clf.predict("anything") == (None, 0.0)
        assert clf.suggest_category("x", "Other") == "Other"


class TestParserIntegration:
    def test_smart_category_uses_rules_first(self):
        # lexicon hit -> rule answer, model never consulted
        assert categorize_smart("chai 20") == "Food"

    def test_smart_category_falls_back_without_model(self):
        # unknown phrase -> 'Other' (no model file in test env is fine either way)
        assert categorize_smart("zzzqqq 10") in {"Other"}


class TestPipelineExport:
    def test_export_training_jsonl(self, tmp_path):
        from awaaz.pipeline import export_training_jsonl
        from awaaz.store import Store

        store = Store(tmp_path / "t.db", migrate_legacy=False)
        store.add_expense("swiggy biryani", 350, "Food")
        store.add_expense("metro ticket", 40, "Travel")
        n, path = export_training_jsonl(store, tmp_path / "out.jsonl")
        assert n == 2
        rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
        assert {r["label"] for r in rows} == {"Food", "Travel"}
        assert all(r["source"] == "user" for r in rows)
