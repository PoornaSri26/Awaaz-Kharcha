"""Generate synthetic speech-like test clips for pipeline evaluation.

These are NOT real voice recordings — harmonic bursts with vibrato-ish
modulation through a synthetic vocal tract-ish envelope, mixed with
stationary noise at controlled SNRs. They exercise the DSP chain
(denoise/VAD/MFCC) deterministically; they cannot measure WER, which needs
real speech + transcripts.

    python eval/make_clips.py --out eval/clips --n 10
"""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
from scipy.io import wavfile

SR = 16000


def speech_like(dur: float, seed: int) -> np.ndarray:
    """Harmonic stack + syllabic amplitude envelope — speech-ish, not speech."""
    rng = np.random.default_rng(seed)
    t = np.arange(int(dur * SR)) / SR
    f0 = rng.uniform(120, 260)
    sig = np.zeros_like(t)
    for h in range(1, 6):
        sig += (0.6 / h) * np.sin(2 * np.pi * f0 * h * t + rng.uniform(0, 6.28))
    # syllabic envelope: 3-5 bursts per clip
    env = np.zeros_like(t)
    for _ in range(rng.integers(3, 6)):
        c = rng.uniform(0.1, 0.9) * dur
        w = rng.uniform(0.05, 0.15)
        env += np.exp(-0.5 * ((t - c) / w) ** 2)
    env = env / max(env.max(), 1e-9)
    return (0.4 * sig * env).astype(np.float32)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="eval/clips")
    ap.add_argument("--n", type=int, default=10)
    ap.add_argument("--dur", type=float, default=2.0)
    args = ap.parse_args()

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(0)
    for i in range(args.n):
        clean = speech_like(args.dur, seed=i)
        wavfile.write(str(out / f"clip_{i:02d}_clean.wav"), SR,
                      (clean * 30000).astype(np.int16))
        for snr in (0, 5, 10, 20):
            noise = rng.standard_normal(len(clean)).astype(np.float32)
            p_sig = np.mean(clean**2) + 1e-12
            gain = np.sqrt(p_sig / (np.mean(noise**2) * 10 ** (snr / 10)))
            mix = (clean + gain * noise)
            wavfile.write(str(out / f"clip_{i:02d}_snr{snr}.wav"), SR,
                          (np.clip(mix, -1, 1) * 30000).astype(np.int16))
    print(f"wrote {args.n} clean + {args.n * 4} noisy clips -> {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
