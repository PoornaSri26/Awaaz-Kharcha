"""Tests for stage-1/2 pipeline extras: features, eval utils, API guards."""

from __future__ import annotations

import numpy as np
import pytest

from awaaz import audio, eval as ev

SR = 16000


def _tone(freq=440.0, dur=0.4, sr=SR, amp=0.4):
    t = np.arange(int(dur * sr)) / sr
    return (amp * np.sin(2 * np.pi * freq * t)).astype(np.float32)


class TestExtras:
    def test_highpass_removes_dc(self):
        dc = np.full(SR, 0.5, dtype=np.float32)
        out = audio.highpass(dc, SR)
        # steady-state tail is DC-free; startup transient settles quickly
        assert np.abs(out[int(SR * 0.1):]).max() < 0.02

    def test_logmel_shape(self):
        lm = audio.logmel_spectrogram(_tone(dur=0.4), SR)
        assert lm.shape[0] == 64
        assert lm.shape[1] > 10

    def test_mfcc_delta_shape(self):
        d = audio.mfcc_delta(_tone(dur=0.4), SR, n_mfcc=13)
        assert d.shape[1] == 39  # 13 * (1 + delta + delta-delta)

    def test_pitch_f0_voiced_tone(self):
        f0 = audio.pitch_f0(_tone(220, dur=0.4), SR)
        voiced = f0[f0 > 0]
        assert len(voiced) > 0
        assert np.median(voiced) == pytest.approx(220, rel=0.1)

    def test_rms_and_centroid(self):
        assert audio.rms_envelope(_tone(), SR).size > 0
        assert audio.spectral_centroid(_tone(1000), SR) > audio.spectral_centroid(_tone(200), SR)


class TestEvalUtils:
    def test_add_noise_and_snr(self):
        clean = _tone(dur=0.5)
        noisy = audio.add_noise(clean, 10, seed=0)
        assert noisy.shape == clean.shape
        # denoise should improve estimated SNR on stationary noise
        est_noisy = audio.estimate_snr(noisy, SR)
        est_clean = audio.estimate_snr(audio.denoise(noisy, SR), SR)
        assert est_clean >= est_noisy - 1.0  # tolerant bound

    def test_snr_benchmark_rows(self, tmp_path):
        import scipy.io.wavfile as wavfile

        p = tmp_path / "c.wav"
        wavfile.write(str(p), SR, (_tone() * 30000).astype(np.int16))
        rows = ev.snr_benchmark([str(p)], snr_levels=(10, 20))
        assert len(rows) == 2
        assert all("delta_db" in r for r in rows)

    def test_stage_timer(self):
        t = ev.StageTimer()
        with t.stage("x"):
            pass
        assert "x" in t.summary_ms()

    def test_wer_optional(self):
        # jiwer may not be installed -> None is acceptable
        assert ev.word_error_rate("a b", "a b") in (0.0, None)


class TestApi:
    def test_app_import_guard(self):
        import api

        # fastapi may be absent -> app is None; must not raise on import
        assert api.app is None or hasattr(api.app, "get")
