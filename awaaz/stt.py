"""Gnani Prisma speech-to-text client."""

from __future__ import annotations

from . import config

#: Container formats Gnani Prisma accepts (it rejects anything else with a 400).
SUPPORTED_EXTENSIONS = ("wav", "mp3", "m4a", "ogg", "flac", "aac")

#: Labels people/browsers use for the same container.
_LABEL_ALIASES = {
    "opus": "ogg",
    "oga": "ogg",
    "ogv": "ogg",
    "mp4": "m4a",
    "mpeg": "mp3",
    "mpga": "mp3",
    "wave": "wav",
    "x-m4a": "m4a",
    "x-wav": "wav",
    "x-flac": "flac",
    "webm": "webm",  # recognised, but not accepted by the API
}

_MIME_TYPES = {
    "audio/wav": "wav",
    "audio/wave": "wav",
    "audio/x-wav": "wav",
    "audio/mpeg": "mp3",
    "audio/mp3": "mp3",
    "audio/mp4": "m4a",
    "audio/m4a": "m4a",
    "audio/x-m4a": "m4a",
    "audio/ogg": "ogg",
    "audio/opus": "ogg",
    "audio/flac": "flac",
    "audio/x-flac": "flac",
    "audio/aac": "aac",
    "audio/webm": "webm",
    "video/webm": "webm",
}


class SttError(RuntimeError):
    """Raised when transcription fails or is not configured."""


def _sniff_extension(audio_bytes: bytes) -> str:
    """Guess the container from magic bytes, which never lie about the format."""
    head = audio_bytes[:12]
    if head[:4] == b"RIFF" and head[8:12] == b"WAVE":
        return "wav"
    if head[:4] == b"OggS":
        return "ogg"
    if head[:4] == b"fLaC":
        return "flac"
    if head[:3] == b"ID3":
        return "mp3"
    if len(head) > 1 and head[0] == 0xFF and head[1] in (0xFB, 0xFA, 0xF3, 0xF2, 0xF9):
        return "mp3"
    if head[0:1] == b"\xff" and len(head) > 1 and (head[1] & 0xF6) == 0xF0:
        return "aac"
    if head[4:8] == b"ftyp":
        return "m4a"
    if head[:4] == b"\x1aE\xdf\xa3":
        return "webm"
    return ""


def _label_extension(label: str) -> str:
    """Extension from a filename (``note.opus``) or a mime type (``audio/ogg``)."""
    label = (label or "").strip().lower()
    if not label:
        return ""
    if "/" in label:  # mime type, not a filename
        return _MIME_TYPES.get(label, "")
    tail = label.rsplit(".", 1)[-1] if "." in label else label
    tail = _LABEL_ALIASES.get(tail, tail)
    return tail if tail in SUPPORTED_EXTENSIONS or tail == "webm" else ""


def audio_filename(label: str, audio_bytes: bytes) -> str:
    """Return a filename Gnani accepts, trusting the bytes over the label.

    The API picks the decoder from the file extension, so a WhatsApp clip named
    ``PTT-2026.opus`` or ``audio`` (no extension) is rejected even when the
    audio is fine. Sniffing first keeps those working.
    """
    extension = (
        _sniff_extension(audio_bytes)
        or _label_extension(label)
        or "wav"  # the browser recorder always produces WAV
    )
    if extension == "webm":
        raise SttError(
            "This clip is WebM audio, which Gnani Prisma cannot decode. "
            "Record in the browser, or upload a WAV, MP3, M4A, OGG or FLAC file."
        )
    if extension not in SUPPORTED_EXTENSIONS:
        raise SttError(
            f"Unsupported audio format '{extension}'. "
            "Gnani Prisma accepts WAV, MP3, M4A, OGG, FLAC and AAC."
        )
    return f"clip.{extension}"


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
            files={"audio_file": (audio_filename(filename, audio_bytes), audio_bytes)},
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
