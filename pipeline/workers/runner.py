"""Queue worker entrypoint — processes jobs from a Redis/RQ queue if available,
else runs a local directory of audio files (benchmark mode)."""
from __future__ import annotations
import json, sys, time
from pathlib import Path

from .stages import run_job


def process_file(path: str, **kw):
    t0 = time.perf_counter()
    res = run_job(path, job_id=Path(path).stem, **kw)
    total_ms = round((time.perf_counter() - t0) * 1000, 1)
    audio_s = kw.get("_audio_s", 0.0)
    rtf = round((total_ms / 1000) / audio_s, 3) if audio_s else None
    return {"job_id": res.job_id, "ok": res.ok, "transcript": res.transcript,
            "language": res.language, "expenses": res.expenses,
            "stages_ms": res.stages_ms, "total_ms": total_ms, "rtf": rtf,
            "errors": res.errors, "confidence": res.confidence, "needs_review": res.needs_review}


def benchmark_dir(clips_dir: str, out_json: str = "pipeline/benchmarks/results.json") -> dict:
    """Run every audio file in a dir; returns aggregate stats."""
    rows = []
    for p in sorted(Path(clips_dir).rglob("*")):
        if p.suffix.lower() not in {".wav", ".mp3", ".ogg", ".m4a", ".flac"}:
            continue
        try:
            from awaaz.audio import load_audio
            _, sr = load_audio(p)
            dur = len(load_audio(p)[0]) / sr
        except Exception:
            dur = 0.0
        r = process_file(str(p), _audio_s=dur)
        rows.append(r)
        print(f"{p.name}: ok={r['ok']} total={r['total_ms']}ms rtf={r['rtf']}")
    ok = [r for r in rows if r["ok"]]
    totals = [r["total_ms"] for r in ok] or [0]
    summary = {
        "n_clips": len(rows), "n_ok": len(ok),
        "p50_ms": sorted(totals)[len(totals) // 2],
        "mean_ms": round(sum(totals) / len(totals), 1),
        "clips_per_hour": round(3600000 / (sum(totals) / max(len(totals), 1)), 1),
        "rows": rows,
    }
    out = Path(out_json); out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(summary, indent=2))
    print(json.dumps({k: v for k, v in summary.items() if k != "rows"}, indent=2))
    return summary


if __name__ == "__main__":
    if len(sys.argv) >= 3 and sys.argv[1] == "bench":
        benchmark_dir(sys.argv[2])
    else:
        print("usage: python -m pipeline.workers.runner bench <clips_dir>")
