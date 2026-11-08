"""Gnani Prisma speech-to-text client."""

from __future__ import annotations

from . import config


class SttError(RuntimeError):
    """Raised when transcription fails or is not configured."""


def transcribe(audio_bytes: bytes, filename: str, language_code: str) -> str:
    """Transcribe an audio clip with Gnani Prisma (ITN keeps numerals as digits)."""
    key = config.api_key()
    if not key:
        raise SttError("GNANI_API_KEY is not configured.")
    if not audio_bytes:
        raise SttError("The audio clip was empty.")

    try:
        import requests
    except ImportError as exc:  # pragma: no cover - requests is a hard dependency
        raise SttError("The 'requests' package is required for voice input.") from exc

    try:
        response = requests.post(
            config.GNANI_API_URL,
            headers={"X-API-Key-ID": key},
            files={"audio_file": (filename, audio_bytes)},
            data={
                "language_code": language_code,
                "format": "transcribe",
                "itn_native_numerals": "false",
            },
            timeout=60,
        )
    except Exception as exc:  # network problems should not crash the page
        raise SttError(f"Could not reach Gnani Prisma: {exc}") from exc

    if response.status_code != 200:
        raise SttError(f"Gnani returned {response.status_code}: {response.text[:300]}")

    try:
        payload = response.json()
    except ValueError as exc:
        raise SttError("Gnani returned a response that was not JSON.") from exc

    transcript = (payload.get("transcript") or "").strip()
    if not transcript:
        raise SttError("Gnani could not find speech in that clip.")
    return transcript
