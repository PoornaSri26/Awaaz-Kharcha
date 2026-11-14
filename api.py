"""Optional FastAPI service — ``pip install fastapi uvicorn python-multipart``.

Run::

    uvicorn api:app --port 8000

Endpoints
---------
``GET  /health``            liveness + which optional backends are available
``POST /expenses/parse``    {"text": "..."} -> parsed expense/udhar rows
``POST /expenses/voice``    multipart audio -> transcript (local whisper if
                            installed, else 501) -> parsed rows

Every response includes ``stages_ms`` latency per pipeline stage.
"""

from __future__ import annotations

import tempfile
import time
from pathlib import Path

from awaaz import audio as audio_dsp
from awaaz import stt_local
from awaaz.eval import StageTimer
from awaaz.parser import parse_expenses

try:
    from fastapi import FastAPI, File, Form, HTTPException, UploadFile
    from pydantic import BaseModel
except Exception:  # fastapi not installed — module still importable for tests
    FastAPI = None  # type: ignore


def create_app() -> "FastAPI":
    if FastAPI is None:
        raise RuntimeError("fastapi not installed: pip install fastapi uvicorn python-multipart")
    app = FastAPI(title="Awaaz Kharcha API", version="1.0")

    @app.get("/health")
    def health():
        return {
            "ok": True,
            "whisper_local": stt_local.available(),
            "diarization": False,  # pyannote needs HF_TOKEN; checked per-request
        }

    class ParseIn(BaseModel):
        text: str
        today: str | None = None

    @app.post("/expenses/parse")
    def parse_text(body: ParseIn):
        timer = StageTimer()
        with timer.stage("parse"):
            expenses, udhar = parse_expenses(body.text)
        return {
            "expenses": expenses,
            "udhar": udhar,
            "stages_ms": timer.summary_ms(),
        }

    @app.post("/expenses/voice")
    async def parse_voice(
        file: UploadFile = File(...),
        language: str | None = Form(None),
        num_speakers: int | None = Form(None),
    ):
        timer = StageTimer()
        suffix = Path(file.filename or "clip.wav").suffix or ".wav"
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
            tmp.write(await file.read())
            tmp_path = tmp.name
        try:
            with timer.stage("preprocess"):
                audio_arr, sr = audio_dsp.preprocess(tmp_path)
                clean = audio_dsp.highpass(audio_dsp.denoise(audio_arr, sr))
            with timer.stage("vad"):
                segs = audio_dsp.voice_activity(clean, sr)
            with timer.stage("stt"):
                if not stt_local.available():
                    raise HTTPException(
                        501,
                        "local whisper not installed — POST /expenses/parse "
                        "with text, or install faster-whisper",
                    )
                transcript = stt_local.transcribe_text(tmp_path, language=language)
            with timer.stage("diarize"):
                speakers = audio_dsp.diarize(tmp_path, num_speakers=num_speakers)
            with timer.stage("parse"):
                expenses, udhar = parse_expenses(transcript)
            return {
                "transcript": transcript,
                "language": language,
                "speech_segments": [
                    {"start": s.start, "end": s.end, "rms": s.rms} for s in segs
                ],
                "speakers": speakers,
                "expenses": expenses,
                "udhar": udhar,
                "stages_ms": timer.summary_ms(),
            }
        finally:
            Path(tmp_path).unlink(missing_ok=True)

    return app


app = create_app() if FastAPI is not None else None  # type: ignore
