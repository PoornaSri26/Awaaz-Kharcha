"""Optional local ASR via faster-whisper.

faster-whisper is *not* a hard dependency — everything here returns empty
results when it or a model is unavailable, so the app keeps working with the
hosted Gnani Prisma path. Install with::

    pip install faster-whisper        # pulls ctranslate2 (~200 MB first model)

Usage::

    from awaaz import stt_local
    segs = stt_local.transcribe("clip.ogg")   # [] when unavailable
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Iterable

from .audio import preprocess

_MODEL = None
_MODEL_TRIED = False


def _model():
    """Lazy-load the whisper model once per process."""
    global _MODEL, _MODEL_TRIED
    if _MODEL_TRIED:
        return _MODEL
    _MODEL_TRIED = True
    try:
        from faster_whisper import WhisperModel  # type: ignore

        size = os.getenv("AWAAZ_WHISPER_MODEL", "base")
        _MODEL = WhisperModel(size, device="cpu", compute_type="int8")
    except Exception:
        _MODEL = None
    return _MODEL


def available() -> bool:
    return _model() is not None


def detect_language(audio_path: str | Path) -> str | None:
    """Whisper's language detection on the first ~30 s — cheap langid."""
    model = _model()
    if model is None:
        return None
    try:
        audio, _ = preprocess(audio_path)
        segs, info = model.transcribe(audio, beam_size=1, vad_filter=False)
        # consume generator -> info.language is populated after first segment
        next(iter(segs), None)
        return getattr(info, "language", None)
    except Exception:
        return None


def transcribe(
    audio_path: str | Path,
    language: str | None = None,
    beam_size: int = 5,
) -> list[dict]:
    """Transcribe to ``[{start, end, text, language, speaker?}]`` segments.

    ``language`` is a whisper code hint (``"hi"``, ``"te"``, ``"ta"``,
    ``"en"`` …); ``None`` lets whisper detect per-file.
    """
    model = _model()
    if model is None:
        return []
    try:
        audio, sr = preprocess(audio_path)
        segments, info = model.transcribe(
            audio,
            language=language,
            beam_size=beam_size,
            vad_filter=True,  # whisper's built-in Silero VAD
            condition_on_previous_text=False,
        )
        out = []
        for seg in segments:
            out.append(
                {
                    "start": round(seg.start, 3),
                    "end": round(seg.end, 3),
                    "text": seg.text.strip(),
                    "language": getattr(info, "language", language),
                    "avg_logprob": round(seg.avg_logprob, 3),
                    "no_speech_prob": round(seg.no_speech_prob, 3),
                }
            )
        return out
    except Exception:
        return []


def transcribe_text(audio_path: str | Path, language: str | None = None) -> str:
    """Convenience: joined transcript text only."""
    segs = transcribe(audio_path, language=language, beam_size=1)
    return " ".join(s["text"] for s in segs).strip()
