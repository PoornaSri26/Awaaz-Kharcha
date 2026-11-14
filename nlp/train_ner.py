"""Token-classification (NER) fine-tune: AMOUNT, ITEM, PAYEE, DATE.

    python nlp/train_ner.py --model ai4bharat/IndicBERT_v2 --data nlp/data/synthetic.jsonl

Converts entity char-spans to BIO tags with the HF tokenizer, fine-tunes with
HF Trainer, evaluates entity-level P/R/F1 via seqeval on the held-out test
split (split is template-stratified — test sentences use unseen item words
where possible).
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

TAGS = ["O", "B-AMOUNT", "I-AMOUNT", "B-ITEM", "I-ITEM",
        "B-PAYEE", "I-PAYEE", "B-DATE", "I-DATE"]
TAG2ID = {t: i for i, t in enumerate(TAGS)}
ID2TAG = {i: t for t, i in TAG2ID.items()}


def spans_to_bio(text: str, entities: list[dict]) -> list[str]:
    """Word-level BIO from char spans (whitespace tokenisation)."""
    words = text.split(" ")
    # map char offset -> word index
    offsets, pos = [], 0
    for w in words:
        offsets.append((pos, pos + len(w)))
        pos += len(w) + 1
    tags = ["O"] * len(words)
    for e in entities:
        lab = e["label"]
        for i, (a, b) in enumerate(offsets):
            if a < e["end"] and b > e["start"]:
                tags[i] = ("B-" if a >= e["start"] else "I-") + lab if tags[i] == "O" else tags[i]
                if a >= e["start"]:
                    tags[i] = "B-" + lab
                elif tags[i] == "O":
                    tags[i] = "I-" + lab
    return tags


def load_jsonl(path: str) -> list[dict]:
    return [json.loads(l) for l in Path(path).read_text(encoding="utf-8").splitlines() if l.strip()]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="distilbert-base-multilingual-cased")
    ap.add_argument("--data", default="nlp/data/synthetic.jsonl")
    ap.add_argument("--out", default="nlp/models/ner")
    ap.add_argument("--epochs", type=float, default=3.0)
    ap.add_argument("--batch", type=int, default=16)
    ap.add_argument("--lr", type=float, default=2e-5)
    ap.add_argument("--max-steps", type=int, default=-1)
    args = ap.parse_args()

    from datasets import Dataset
    from seqeval.metrics import accuracy_score, f1_score, precision_score, recall_score
    from transformers import (AutoModelForTokenClassification, AutoTokenizer,
                              Trainer, TrainingArguments)

    rows = [r for r in load_jsonl(args.data) if r.get("entities")]
    from nlp.augment import split_rows
    splits = split_rows(rows)
    ds = {k: Dataset.from_list(v) for k, v in splits.items()}
    print({k: len(v) for k, v in ds.items()})

    tok = AutoTokenizer.from_pretrained(args.model)

    def prep2(ex):
        enc = tok(ex["text"], truncation=True, max_length=96,
                  return_offsets_mapping=True)
        offsets = enc.pop("offset_mapping")
        bio = spans_to_bio(ex["text"], ex["entities"])
        # whitespace word spans
        words, pos = [], 0
        for w in ex["text"].split(" "):
            words.append((pos, pos + len(w)))
            pos += len(w) + 1
        word_tags = []
        for (a, b) in offsets:
            if a == b:
                word_tags.append(-100)
                continue
            mid = (a + b) // 2
            wi = next((i for i, (wa, wb) in enumerate(words)
                       if wa <= mid < wb), -1)
            word_tags.append(TAG2ID[bio[wi]] if wi >= 0 else -100)
        enc["labels"] = word_tags
        return enc

    for k in ds:
        ds[k] = ds[k].map(prep2)

    model = AutoModelForTokenClassification.from_pretrained(
        args.model, num_labels=len(TAGS), id2label=ID2TAG, label2id=TAG2ID)

    def to_seqeval(p):
        preds = p.predictions.argmax(-1)
        y_true, y_pred = [], []
        for label_ids, pred_ids in zip(p.label_ids, preds):
            yt = [ID2TAG[i] for i in label_ids if i != -100]
            yp = [ID2TAG[i] for i in pred_ids if i != -100]
            # lengths may differ after label masking; trim to min
            m = min(len(yt), len(yp))
            y_true.append(yt[:m]); y_pred.append(yp[:m])
        return y_true, y_pred

    def metrics(p):
        yt, yp = to_seqeval(p)
        return {"entity_f1": f1_score(yt, yp),
                "entity_precision": precision_score(yt, yp),
                "entity_recall": recall_score(yt, yp)}

    targs = TrainingArguments(
        output_dir=args.out, num_train_epochs=args.epochs,
        per_device_train_batch_size=args.batch, per_device_eval_batch_size=32,
        learning_rate=args.lr, eval_strategy="epoch", save_strategy="epoch",
        load_best_model_at_end=True, metric_for_best_model="entity_f1",
        report_to=[], seed=42, max_steps=args.max_steps)

    trainer = Trainer(model=model, args=targs, train_dataset=ds["train"],
                      eval_dataset=ds["val"], compute_metrics=metrics)
    trainer.train()
    yt, yp = to_seqeval(trainer.predict(ds["test"]))
    report = {"model": args.model,
              "entity_f1": f1_score(yt, yp),
              "entity_precision": precision_score(yt, yp),
              "entity_recall": recall_score(yt, yp),
              "token_accuracy": accuracy_score(yt, yp)}
    out = Path(args.out); out.mkdir(parents=True, exist_ok=True)
    (out / "test_report.json").write_text(json.dumps(report, indent=2))
    print(json.dumps(report, indent=2))
    trainer.save_model(str(out / "final")); tok.save_pretrained(str(out / "final"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
