"""Language-ID / code-mix detection fine-tune (sequence classification).

    python nlp/train_langid.py --model ai4bharat/IndicBERT_v2 --data nlp/data/synthetic.jsonl

Labels: en, hi, te, ta, hinglish (romanised code-mixed).
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

LANGS = ["en", "hi", "te", "ta", "hinglish"]
LANG2ID = {l: i for i, l in enumerate(LANGS)}


def load_jsonl(path):
    return [json.loads(l) for l in Path(path).read_text(encoding="utf-8").splitlines() if l.strip()]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="distilbert-base-multilingual-cased")
    ap.add_argument("--data", default="nlp/data/synthetic.jsonl")
    ap.add_argument("--out", default="nlp/models/langid")
    ap.add_argument("--epochs", type=float, default=3.0)
    ap.add_argument("--batch", type=int, default=16)
    ap.add_argument("--lr", type=float, default=2e-5)
    ap.add_argument("--lora", action="store_true")
    args = ap.parse_args()

    from datasets import Dataset
    from sklearn.metrics import accuracy_score, f1_score
    from transformers import (AutoModelForSequenceClassification, AutoTokenizer,
                              Trainer, TrainingArguments)

    from nlp.augment import split_rows
    rows = load_jsonl(args.data)
    splits = split_rows(rows)
    ds = {k: Dataset.from_list(v) for k, v in splits.items()}
    print({k: len(v) for k, v in ds.items()})

    tok = AutoTokenizer.from_pretrained(args.model)
    for k in ds:
        ds[k] = ds[k].map(lambda b: tok(b["text"], truncation=True, max_length=64))
        ds[k] = ds[k].map(lambda b: {"labels": LANG2ID.get(b["lang"], 0)})
    keep = {"input_ids", "attention_mask", "token_type_ids", "labels"}
    ds = {k: v.remove_columns([c for c in v.column_names if c not in keep])
          for k, v in ds.items()}

    model = AutoModelForSequenceClassification.from_pretrained(
        args.model, num_labels=len(LANGS), id2label={i: l for l, i in LANG2ID.items()},
        label2id=LANG2ID)
    if args.lora:
        from peft import LoraConfig, get_peft_model
        model = get_peft_model(model, LoraConfig(r=8, lora_alpha=16,
            lora_dropout=0.05, target_modules=["query", "value"], task_type="SEQ_CLS"))

    def metrics(p):
        pred = p.predictions.argmax(-1)
        return {"accuracy": accuracy_score(p.label_ids, pred),
                "macro_f1": f1_score(p.label_ids, pred, average="macro")}

    targs = TrainingArguments(output_dir=args.out, num_train_epochs=args.epochs,
        per_device_train_batch_size=args.batch, per_device_eval_batch_size=32,
        learning_rate=args.lr, eval_strategy="epoch", save_strategy="epoch",
        load_best_model_at_end=True, metric_for_best_model="macro_f1",
        report_to=[], seed=42)
    trainer = Trainer(model=model, args=targs, train_dataset=ds["train"],
                      eval_dataset=ds["val"], compute_metrics=metrics)
    trainer.train()
    pred = trainer.predict(ds["test"])
    report = {"model": args.model, "lora": args.lora,
              "accuracy": accuracy_score(pred.label_ids, pred.predictions.argmax(-1)),
              "macro_f1": f1_score(pred.label_ids, pred.predictions.argmax(-1), average="macro")}
    out = Path(args.out); out.mkdir(parents=True, exist_ok=True)
    (out / "test_report.json").write_text(json.dumps(report, indent=2))
    print(json.dumps(report, indent=2))
    trainer.save_model(str(out / "final")); tok.save_pretrained(str(out / "final"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
