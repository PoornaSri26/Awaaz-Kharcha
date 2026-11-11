"""Speech-to-text helpers: format detection and configuration errors."""

from __future__ import annotations

import struct

import pytest

from awaaz import config, stt

WAV = b"RIFF" + struct.pack("<I", 36) + b"WAVEfmt " + b"\x00" * 32
OGG = b"OggS" + b"\x00" * 40
MP3 = b"ID3\x03\x00\x00\x00" + b"\x00" * 40
M4A = b"\x00\x00\x00\x20ftypM4A " + b"\x00" * 32
FLAC = b"fLaC" + b"\x00" * 40
WEBM = b"\x1aE\xdf\xa3" + b"\x00" * 40


def test_bytes_win_over_a_misleading_name():
    # WhatsApp names Opus voice notes .opus, and some downloads have no extension.
    assert stt.audio_filename("PTT-20261111-WA0003.opus", OGG) == "clip.ogg"
    assert stt.audio_filename("audio", WAV) == "clip.wav"
    assert stt.audio_filename("voice.bin", MP3) == "clip.mp3"


def test_mime_labels_are_understood():
    # The 400 from Gnani came from sending a mime string as the filename.
    assert stt.audio_filename("audio/wav", WAV) == "clip.wav"
    assert stt.audio_filename("audio/ogg", OGG) == "clip.ogg"
    assert stt.audio_filename("audio/mp4", M4A) == "clip.m4a"
    assert stt.audio_filename("audio/flac", FLAC) == "clip.flac"


def test_known_containers_are_detected():
    assert stt.audio_filename("", M4A) == "clip.m4a"
    assert stt.audio_filename("", FLAC) == "clip.flac"


def test_webm_is_rejected_with_a_usable_message():
    with pytest.raises(stt.SttError, match="WebM"):
        stt.audio_filename("sample.webm", WEBM)


def test_missing_key_and_empty_clip_are_config_errors(monkeypatch):
    monkeypatch.setattr(config, "api_key", lambda: "")
    with pytest.raises(stt.SttError, match="GNANI_API_KEY"):
        stt.transcribe(WAV, "voice.wav", "hi-IN")

    monkeypatch.setattr(config, "api_key", lambda: "dummy")
    with pytest.raises(stt.SttError, match="empty"):
        stt.transcribe(b"", "voice.wav", "hi-IN")
