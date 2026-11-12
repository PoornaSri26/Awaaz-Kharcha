"""Automatic spoken-language detection through Prisma v3.0."""

from __future__ import annotations

import sys
import types

from awaaz import stt

WAV = b"RIFF" + b"\x00" * 4 + b"WAVE"


class _FakeResponse:
    status_code = 200

    def __init__(self, payload: dict) -> None:
        self._payload = payload
        self.text = str(payload)

    def json(self) -> dict:
        return self._payload


def _fake_requests(monkeypatch, payload: dict, captured: dict):
    def post(url, headers=None, files=None, data=None, timeout=None):
        captured["data"] = data
        captured["files"] = files
        return _FakeResponse(payload)

    module = types.SimpleNamespace(post=post)
    monkeypatch.setitem(sys.modules, "requests", module)


def test_auto_request_asks_prisma_v3_to_detect():
    fields = stt.request_fields("")
    assert fields["language_code"] == "indic-auto"
    assert fields["model"] == "prisma-v3.0"


def test_explicit_language_keeps_the_default_model():
    fields = stt.request_fields("te-IN")
    assert fields["language_code"] == "te-IN"
    assert "model" not in fields


def test_auto_hints_are_recognised():
    for value in ("", None, "auto", "indic-auto", "AUTO"):
        assert stt.is_auto(value), value
    assert not stt.is_auto("hi-IN")


def test_transcribe_detailed_returns_the_detected_language(monkeypatch):
    monkeypatch.setenv("GNANI_API_KEY", "test-key")
    captured: dict = {}
    _fake_requests(
        monkeypatch,
        {"transcript": "నిన్న టీ 20", "detected_language_code": "te-IN"},
        captured,
    )

    result = stt.transcribe_detailed(WAV, "clip.wav", "")

    assert result.text == "నిన్న టీ 20"
    assert result.language == "te-IN"
    assert captured["data"]["language_code"] == "indic-auto"
    assert captured["files"]["audio_file"][0] == "clip.wav"


def test_plain_transcribe_still_returns_text(monkeypatch):
    monkeypatch.setenv("GNANI_API_KEY", "test-key")
    _fake_requests(monkeypatch, {"transcript": "chai 20"}, {})

    assert stt.transcribe(WAV, "clip.wav", "hi-IN") == "chai 20"
