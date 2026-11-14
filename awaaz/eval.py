"""Evaluation helpers — WER, SNR, latency — all optional-dependency safe.

Heavy metrics (jiwer WER, pyannote DER) degrade to ``None`` when the package
is missing so CI without those deps still runs.
"""

from __future__ import annotations

import time
from contextlib import contextmanager
from dataclasses import dataclass, field

import numpy as np

from .audio import add_noise, denoise, estimate_snr, preprocess


@dataclass
class StageTimer:
    """Per-stage latency accumulator — the 'latency per stage' evidence."""

    stages: dict[str, list[float]] = field(default_factory=dict)

    @contextmanager
    def stage(self, name: str):
        t0 = time.perf_counter()
        try:
            yield
        finally:
            self.stages.setdefault(name, []).append(time.perf_counter() - t0)

    def summary_ms(self) -> dict[str, float]:
        return {
            k: round(1000 * sum(v) / len(v), 1) for k, v in self.stages.items()
        }


def snr_benchmark(
    clips: list[str],
    snr_levels=(0, 5, 10, 20),
    seed: int = 0,
) -> list[dict]:
    """SNR before/after denoise for a set of audio files.

    Returns one row per (clip, snr): estimated SNR of the noisy mix and of the
    denoised output — quantifies the denoiser's noise-floor reduction.
    """
    rows = []
    for path in clips:
        try:
            audio, sr = preprocess(path)
        except Exception:
            continue
        for snr in snr_levels:
            noisy = add_noise(audio, snr, seed=seed)
            clean = denoise(noisy, sr)
            rows.append(
                {
                    "clip": str(path),
                    "target_snr_db": snr,
                    "snr_noisy_db": round(estimate_snr(noisy, sr), 1),
                    "snr_denoised_db": round(estimate_snr(clean, sr), 1),
                    "delta_db": round(
                        estimate_snr(clean, sr) - estimate_snr(noisy, sr), 1
                    ),
                }
            )
    return rows


def word_error_rate(reference: str, hypothesis: str) -> float | None:
    """WER via jiwer when installed, else ``None``."""
    try:
        import jiwer  # type: ignore
    except Exception:
        return None
    return float(jiwer.wer(reference, hypothesis))


def diarization_error_rate(reference, hypothesis) -> float | None:
    """DER via pyannote.metrics when installed, else ``None``.

    ``reference``/``hypothesis`` are pyannote Annotation objects.
    """
    try:
        from pyannote.metrics.diarization import DiarizationErrorRate  # type: ignore
    except Exception:
        return None
    metric = DiarizationErrorRate()
    return float(metric(reference, hypothesis))
