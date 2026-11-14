"""Pipeline API — upload audio, get structured expense JSON.

    uvicorn pipeline.api.app:app --port 8100
"""
from __future__ import annotations
import tempfile, time
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from ..workers.stages import run_job

app = FastAPI(title="Awaaz Kharcha Pipeline API", version="1.0")


@app.get("/health")
def health():
    return {"ok": True}


@app.post("/v1/jobs")
async def create_job(file: UploadFile = File(...),
                     language: str | None = Form(None),
                     num_speakers: int | None = Form(None)):
    """Synchronous processing (queue workers swap in later without API change)."""
    suffix = Path(file.filename or "clip.wav").suffix or ".wav"
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        tmp.write(await file.read())
        tmp_path = tmp.name
    try:
        t0 = time.perf_counter()
        res = run_job(tmp_path, job_id=file.filename or "upload",
                      language=language, num_speakers=num_speakers)
        total_ms = round((time.perf_counter() - t0) * 1000, 1)
        return {"job_id": res.job_id, "ok": res.ok, "transcript": res.transcript,
                "language": res.language, "expenses": res.expenses,
                "stages_ms": res.stages_ms, "total_ms": total_ms,
                "errors": res.errors, "confidence": res.confidence, "needs_review": res.needs_review}
    finally:
        Path(tmp_path).unlink(missing_ok=True)
