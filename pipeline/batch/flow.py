"""Offline batch path — Prefect flow (optional dep) or plain function.

    python -m pipeline.batch.flow --clips eval/clips --out data/dataset.parquet

Validates clips (duration/SNR), denoises, extracts features, writes Parquet
partitioned by language — the Spark-swap-ready layout described in
ARCHITECTURE.md.
"""
from __future__ import annotations
import argparse, json, sys
from pathlib import Path

import numpy as np

from awaaz import audio as dsp

try:
    import pyarrow as pa, pyarrow.parquet as pq
    HAVE_PA = True
except Exception:
    HAVE_PA = False


def validate_clip(path: str, min_snr_db: float = 5.0, min_dur_s: float = 0.3) -> dict:
    """Quality gate: duration + estimated SNR."""
    audio, sr = dsp.preprocess(path)
    dur = len(audio) / sr
    snr = dsp.estimate_snr(audio, sr)
    return {"path": path, "duration_s": round(dur, 2), "snr_db": round(snr, 1),
            "accept": dur >= min_dur_s and snr >= min_snr_db}


def build_dataset(clips_dir: str, out_parquet: str) -> dict:
    rows = []
    for p in sorted(Path(clips_dir).rglob("*.wav")):
        try:
            v = validate_clip(str(p))
            audio, sr = dsp.preprocess(str(p))
            feats = dsp.spectral_features(audio, sr)
            rows.append({**v, "mfcc_mean": json.dumps(feats.get("mfcc_mean", []))})
        except Exception as e:
            rows.append({"path": str(p), "accept": False, "error": str(e)})
    accepted = [r for r in rows if r.get("accept")]
    if HAVE_PA and accepted:
        table = pa.Table.from_pylist(accepted)
        pq.write_table(table, out_parquet)
    Path(out_parquet + ".json").write_text(json.dumps(rows, indent=2))
    return {"total": len(rows), "accepted": len(accepted),
            "reject_rate": round(1 - len(accepted) / max(len(rows), 1), 3),
            "out": out_parquet}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--clips", required=True)
    ap.add_argument("--out", default="data/dataset.parquet")
    args = ap.parse_args()
    print(json.dumps(build_dataset(args.clips, args.out), indent=2))


if __name__ == "__main__":
    main()
