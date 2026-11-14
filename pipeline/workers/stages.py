"""Pipeline stage workers — each is a pure function stage for testability.

Stages: preprocess -> denoise -> vad -> langid -> stt -> nlp -> validate -> store
Each returns a dict result; the runner in workers/runner.py chains them and
records per-stage latency (feeds benchmarks/results.md).
"""
from __future__ import annotations
import time
from dataclasses import dataclass, field

import numpy as np

from awaaz import audio as dsp
from awaaz import stt_local


@dataclass
class JobResult:
    job_id: str
    transcript: str = ""
    language: str | None = None
    expenses: list = field(default_factory=list)
    speakers: list = field(default_factory=list)
    stages_ms: dict = field(default_factory=dict)
    errors: list = field(default_factory=list)
    confidence: float = 1.0
    needs_review: bool = False
    ok: bool = True


def run_job(audio_path: str, job_id: str = "job", language: str | None = None,
            num_speakers: int | None = None) -> JobResult:
    """Execute the full online pipeline for one audio file."""
    from awaaz.parser import parse_expenses

    res = JobResult(job_id=job_id)

    def stage(name, fn):
        t0 = time.perf_counter()
        try:
            return fn()
        except Exception as e:  # stage failure recorded, pipeline continues where safe
            res.errors.append(f"{name}: {e}")
            res.stages_ms[name] = round((time.perf_counter() - t0) * 1000, 1)
            return None
        finally:
            res.stages_ms[name] = round((time.perf_counter() - t0) * 1000, 1)

    audio_arr, sr = stage("preprocess", lambda: dsp.preprocess(audio_path)) or (None, None)
    if audio_arr is None:
        res.ok = False
        return res
    clean = stage("denoise", lambda: dsp.highpass(dsp.denoise(audio_arr, sr)))
    if clean is not None:
        stage("vad", lambda: dsp.voice_activity(clean, sr))
    res.language = stage("langid", lambda: stt_local.detect_language(audio_path)) or language
    segs = stage("stt", lambda: stt_local.transcribe(audio_path, language=res.language))
    res.transcript = " ".join(s["text"] for s in (segs or [])).strip()
    # confidence signal: whisper avg_logprob when available, else heuristic
    logprobs = [abs(s.get("avg_logprob", -1.0)) for s in (segs or []) if s.get("avg_logprob") is not None]
    if logprobs:
        res.confidence = round(sum(logprobs) / len(logprobs), 3)
    res.needs_review = res.confidence < 0.6 or bool(res.errors)
    if not res.transcript:
        res.ok = False
        res.errors.append("stt: empty transcript")
        _log_job(res)
        return res
    stage("diarize", lambda: dsp.diarize(audio_path, num_speakers=num_speakers))
    # attach speaker index to transcript segments when diarization is available
    parsed = stage("nlp", lambda: parse_expenses(res.transcript))
    if parsed:
        res.expenses = parsed[0]
    res.ok = True
    _log_job(res)
    return res


def _log_job(res: "JobResult", path: str = "pipeline/results/job_log.jsonl") -> None:
    """Append a structured record — the raw material for error-rate-over-time
    and low-confidence review dashboards."""
    import json
    from pathlib import Path
    p = Path(path); p.parent.mkdir(parents=True, exist_ok=True)
    rec = {"job_id": res.job_id, "ok": res.ok, "confidence": res.confidence,
           "needs_review": res.needs_review, "language": res.language,
           "total_ms": sum(res.stages_ms.values()),
           "stages_ms": res.stages_ms, "errors": res.errors}
    with p.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
