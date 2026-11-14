"""Tests for awaaz.audio — pure numpy/scipy DSP, no downloads."""

from __future__ import annotations

import numpy as np
import pytest
from scipy.io import wavfile

from awaaz import audio

SR = 16000


def _tone(freq=440.0, dur=0.5, sr=SR, amp=0.5):
    t = np.arange(int(dur * sr)) / sr
    return (amp * np.sin(2 * np.pi * freq * t)).astype(np.float32)


def _noise(dur=0.5, sr=SR, amp=0.05, seed=0):
    rng = np.random.default_rng(seed)
    return (amp * rng.standard_normal(int(dur * sr))).astype(np.float32)


class TestResample:
    def test_to_mono_16k_resamples_and_normalises(self):
        audio_in = _tone(sr=8000) * 5.0  # clipped amplitude
        out, sr = audio.to_mono_16k(audio_in, 8000)
        assert sr == 16000
        assert len(out) == pytest.approx(len(audio_in) * 2, rel=0.01)
        assert np.max(np.abs(out)) <= 1.0


class TestDenoise:
    def test_denoise_reduces_stationary_noise(self):
        rng = np.random.default_rng(1)
        speech = _tone(300, 0.6) * (np.hanning(int(0.6 * SR)) ** 2)
        noisy = speech + 0.08 * rng.standard_normal(len(speech)).astype(np.float32)
        clean = audio.denoise(noisy, SR)
        assert clean.shape == noisy.shape
        # residual noise floor should drop
        tail_clean = np.abs(clean[int(0.5 * SR):]).mean()
        tail_noisy = np.abs(noisy[int(0.5 * SR):]).mean()
        assert tail_clean < tail_noisy

    def test_denoise_handles_short_input(self):
        short = np.zeros(100, dtype=np.float32)
        assert audio.denoise(short, SR).shape == short.shape


class TestMFCC:
    def test_mfcc_shape(self):
        f = audio.mfcc(_tone(dur=0.5), SR)
        assert f.ndim == 2
        assert f.shape[0] > 10
        assert f.shape[1] == 13

    def test_mfcc_empty(self):
        assert audio.mfcc(np.zeros(0, dtype=np.float32), SR).shape == (0, 13)

    def test_spectral_features(self):
        feats = audio.spectral_features(_tone(dur=0.3), SR)
        assert feats["duration_s"] == pytest.approx(0.3, abs=0.01)
        assert len(feats["mfcc_mean"]) == 13


class TestVAD:
    def test_vad_finds_speech_burst(self):
        silence = np.zeros(int(0.3 * SR), dtype=np.float32)
        burst = _tone(500, 0.4, amp=0.6)
        gap = np.zeros(int(0.3 * SR), dtype=np.float32)
        clip = np.concatenate([silence, burst, gap]).astype(np.float32)
        segs = audio.voice_activity(clip, SR, threshold_db=-45)
        assert len(segs) >= 1
        assert segs[0].start < 0.5
        assert segs[0].end > 0.5

    def test_vad_empty_and_silence(self):
        assert audio.voice_activity(np.zeros(0, dtype=np.float32), SR) == []
        assert audio.voice_activity(np.zeros(SR, dtype=np.float32), SR) == []


class TestWavIO:
    def test_wav_roundtrip(self, tmp_path):
        x = (_tone() + 0.01 * np.random.default_rng(2).standard_normal(SR // 2)).astype(np.float32)
        p = tmp_path / "clip.wav"
        wavfile.write(str(p), SR, (x * 32767).astype(np.int16))
        y, sr = audio.load_audio(p)
        assert sr == SR
        assert y.shape == x.shape
        assert np.allclose(y, x, atol=1e-3)

    def test_preprocess_pipeline(self, tmp_path):
        p = tmp_path / "clip.wav"
        wavfile.write(str(p), 8000, (_tone(sr=8000) * 30000).astype(np.int16))
        y, sr = audio.preprocess(p)
        assert sr == 16000
        assert 0.4 < len(y) / sr < 0.7


class TestDiarize:
    def test_diarize_returns_empty_without_pyannote(self):
        # pyannote not installed / no HF token -> graceful []
        assert audio.diarize(_tone(dur=0.2)) == []
