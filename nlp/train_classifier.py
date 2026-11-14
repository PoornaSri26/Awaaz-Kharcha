"""Fine-tune a multilingual transformer for expense-category classification.

    python nlp/train_classifier.py --model xlmo/mt0-small --data nlp/data/synthetic.jsonl
    python nlp/train_classifier.py --model ai4bharat/IndicBERT_v2 --lora --epochs 3

Works on Colab free GPU; on CPU keep --model small (distilbert-base-multilingual-cased).
Requires: transformers, datasets, scikit-learn (metrics).
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

LABELS = ["Food", "Travel", "Groceries", "Bills", "Health",
          "Shopping", "Fun", "Education", "Other"]
LABEL2ID = {l: i for i, l in enumerate(LABELS)}


def load_jsonl(path: str) -> list[dict]:
    return [json.loads(l) for l in Path(path).read_text(encoding="utf-8").splitlines() if l.strip()]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="distilbert-base-multilingual-cased")
    ap.add_argument("--data", default="nlp/data/synthetic.jsonl")
    ap.add_argument("--out", default="nlp/models/category_clf")
    ap.add_argument("--epochs", type=float, default=3.0)
    ap.add_argument("--batch", type=int, default=16)
    ap.add_argument("--lr", type=float, default=2e-5)
    ap.add_argument("--lora", action="store_true", help="PEFT LoRA instead of full FT")
    ap.add_argument("--max-steps", type=int, default=-1)
    args = ap.parse_args()

    from datasets import Dataset
    from sklearn.metrics import accuracy_score, f1_score
    from transformers import (AutoModelForSequenceClassification, AutoTokenizer,
                              DataCollatorWithPadding, Trainer, TrainingArguments)

    rows = load_jsonl(args.data)
    from nlp.augment import split_rows
    splits = split_rows(rows)
    ds = {k: Dataset.from_list(v) for k, v in splits.items()}
    print({k: len(v) for k, v in ds.items()})

    tok = AutoTokenizer.from_pretrained(args.model)

    def enc(batch):
        return tok(batch["text"], truncation=True, max_length=64)

    ds = {k: v.map(enc, batched=True) for k, v in ds.items()}
    ds["train"] = ds["train"].map(lambda b: {"labels": LABEL2ID.get(b["category"], 8)})
    ds["val"] = ds["val"].map(lambda b: {"labels": LABEL2ID.get(b["category"], 8)})
    ds["test"] = ds["test"].map(lambda b: {"labels": LABEL2ID.get(b["category"], 8)})
    keep = {"input_ids", "attention_mask", "token_type_ids", "labels"}
    ds = {k: v.remove_columns([c for c in v.column_names if c not in keep])
          for k, v in ds.items()}

    model = AutoModelForSequenceClassification.from_pretrained(
        args.model, num_labels=len(LABELS), id2label={i: l for l, i in LABEL2ID.items()},
        label2id=LABEL2ID)

    if args.lora:
        from peft import LoraConfig, get_peft_model
        model = get_peft_model(model, LoraConfig(
            r=8, lora_alpha=16, lora_dropout=0.05,
            target_modules=["query", "value"], task_type="SEQ_CLS"))
        model.print_trainable_parameters()

    def metrics(p):
        pred = p.predictions.argmax(-1)
        return {"accuracy": accuracy_score(p.label_ids, pred),
                "macro_f1": f1_score(p.label_ids, pred, average="macro")}

    targs = TrainingArguments(
        output_dir=args.out, num_train_epochs=args.epochs,
        per_device_train_batch_size=args.batch, per_device_eval_batch_size=32,
        learning_rate=args.lr, eval_strategy="epoch", save_strategy="epoch",
        load_best_model_at_end=True, metric_for_best_model="macro_f1",
        report_to=[], seed=42, max_steps=args.max_steps)

    trainer = Trainer(model=model, args=targs, train_dataset=ds["train"],
                      eval_dataset=ds["val"], compute_metrics=metrics,
                      data_collator=DataCollatorWithPadding(tokenizer=tok))
    trainer.train()

    # held-out test report
    pred = trainer.predict(ds["test"])
    y = pred.label_ids
    p = pred.predictions.argmax(-1)
    report = {
        "model": args.model, "lora": args.lora,
        "accuracy": accuracy_score(y, p),
        "macro_f1": f1_score(y, p, average="macro"),
        "per_class_f1": f1_score(y, p, average=None, labels=list(range(len(LABELS)))),
    }
    out = Path(args.out); out.mkdir(parents=True, exist_ok=True)
    (out / "test_report.json").write_text(json.dumps(report, indent=2))
    print(json.dumps(report, indent=2))
    trainer.save_model(str(out / "final"))
    tok.save_pretrained(str(out / "final"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
