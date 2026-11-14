"""Evaluation utilities for the fine-tuning experiments.

    python nlp/evaluate.py --report nlp/models/category_indicbert/test_report.json

Aggregates per-class F1, per-language breakdown and zero-shot-vs-finetuned
deltas from the JSON reports written by the train_* scripts into
nlp/results/results.csv.
"""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

RESULTS_CSV = Path("nlp/results/results.csv")


def collect(reports: list[Path]) -> list[dict]:
    rows = []
    for p in reports:
        if not p.exists():
            continue
        r = json.loads(p.read_text())
        r["report"] = str(p)
        rows.append(r)
    return rows


def write_csv(rows: list[dict], path: Path = RESULTS_CSV) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = sorted({k for r in rows for k in r if k != "per_class_f1"})
    with path.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=fields)
        w.writeheader()
        for r in rows:
            w.writerow({k: (json.dumps(v) if isinstance(v, (list, dict)) else v)
                        for k, v in r.items() if k in fields})


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("reports", nargs="*",
                    default=["nlp/models/category_indicbert/test_report.json",
                             "nlp/models/category_muril_lora/test_report.json",
                             "nlp/models/ner/test_report.json",
                             "nlp/models/langid_xlmr/test_report.json"])
    args = ap.parse_args()
    rows = collect([Path(p) for p in args.reports])
    write_csv(rows)
    for r in rows:
        print(json.dumps({k: v for k, v in r.items()
                          if k not in ("per_class_f1", "report")}, indent=None))
    print(f"\nwrote {RESULTS_CSV}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
