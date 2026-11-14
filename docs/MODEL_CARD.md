# Model card — expense category classifier

## Overview

Multinomial text classifier that maps a free-form, code-mixed expense
description (Hinglish, Telugu, Tamil, Bengali, Kannada, Malayalam, Indian
English) to one of nine expense categories. It is a *fallback* layer: the
deterministic rule parser in `awaaz/parser.py` handles amounts, dates, udhar
rows and every lexicon-known keyword; the model only votes when rules return
`Other`, and only above a 0.50 confidence threshold.

## Model

| | |
|---|---|
| Pipeline | `TfidfVectorizer(char_wb, ngram_range=(2,5), sublinear_tf)` → `LogisticRegression(lbfgs, class_weight=balanced)` |
| Labels | Food, Travel, Groceries, Bills, Health, Shopping, Fun, Education |
| Artefact | `models/category_clf.joblib` (git-ignored; rebuilt by `train_model.py`) |
| Why char n-grams | code-mixed text has no clean tokeniser; char n-grams capture sub-word morphology across romanised and native scripts |

## Training data

1. **Lexicon templates** — every keyword in `CATEGORIES` wrapped in Hinglish/English sentence frames (~1.3k examples, 9 classes).
2. **User corrections** — SQLite rows whose category the user confirmed/edited in History (`awaaz/pipeline.iter_labeled_expenses`). These grow with usage and are the intended path to production quality.

`train_model.py` reports stratified held-out accuracy and per-class P/R/F1.
Baseline (lexicon only): **accuracy ≈ 0.95** on held-out templates.

## Intended use / limits

- **Intended:** suggest a category for items the lexicon misses; batch
  re-labelling via `awaaz/pipeline.export_training_jsonl` (Spark-readable JSONL).
- **Not intended:** parsing amounts/dates (rule engine owns that), udhar/khata
  classification, or languages outside the ten UI locales.
- Confidence below threshold → caller's fallback is kept; the model never
  overrides a confident rule match.
- Rule-based lexicon remains authoritative — a wrong model guess cannot corrupt
  amounts, only relabel a category, and only on `Other` items.

## Offline behaviour

Everything runs locally; no network calls. Missing model or missing
scikit-learn degrades silently to rule-only categorisation.
