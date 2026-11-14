"""Audio preprocessing for Awaaz Kharcha.

Everything here runs locally on CPU with numpy/scipy only — no model downloads,
no GPU. The pipeline mirrors what a production multilingual-ASR front-end does:

    load → resample 16 kHz mono → denoise → VAD segments → (optional) MFCCs

Optional integrations degrade gracefully:

* ``soundfile`` enables .ogg/.flac/.opus decode (WhatsApp voice notes);
* ``pyannote.audio`` enables speaker diarization when installed *and* a
  HuggingFace token is configured — otherwise :func:`diarize` returns ``[]``.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import numpy as np
from scipy import signal

TARGET_SR = 16000


# ---------------------------------------------------------------- loading

def load_audio(path: str | Path) -> tuple[np.ndarray, int]:
    """Decode an audio file to ``(float32 mono array, sample_rate)``.

    Supports WAV natively; .ogg/.opus/.flac need ``soundfile``
    (``pip install soundfile``). Raises a clear error for formats that need
    ffmpeg (e.g. .m4a/.aac) when no decoder is available.
    """
    path = Path(path)
    try:
        import soundfile as sf  # type: ignore

        data, sr = sf.read(str(path), dtype="float32", always_2d=True)
        return data.mean(axis=1), int(sr)
    except ImportError:
        pass
    # WAV fallback via scipy
    if path.suffix.lower() in {".wav", ".wave"}:
        from scipy.io import wavfile

        sr, data = wavfile.read(str(path))
        if np.issubdtype(data.dtype, np.integer):
            scale = float(np.iinfo(data.dtype).max)
            data = data.astype(np.float32) / max(scale, 1.0)
        else:
            data = data.astype(np.float32)
        if data.ndim > 1:
            data = data.mean(axis=1)
        return data, int(sr)
    raise RuntimeError(
        f"Cannot decode {path.suffix}: install soundfile for .ogg/.flac "
        "or convert .m4a/.aac with ffmpeg first."
    )


def to_mono_16k(audio: np.ndarray, sr: int) -> tuple[np.ndarray, int]:
    """Resample to 16 kHz and normalise to [-1, 1]."""
    if sr != TARGET_SR:
        n_out = int(round(len(audio) * TARGET_SR / sr))
        audio = signal.resample(audio, n_out).astype(np.float32)
        sr = TARGET_SR
    peak = float(np.max(np.abs(audio))) if len(audio) else 0.0
    if peak > 1.0:
        audio = audio / peak
    return audio.astype(np.float32), sr


def preprocess(path: str | Path) -> tuple[np.ndarray, int]:
    """load → mono 16 kHz — the standard input for everything below."""
    audio, sr = load_audio(path)
    return to_mono_16k(audio, sr)


# ---------------------------------------------------------------- denoise

def denoise(
    audio: np.ndarray,
    sr: int = TARGET_SR,
    n_fft: int = 512,
    hop: int = 128,
    oversubtract: float = 1.5,
    noise_percentile: float = 20.0,
) -> np.ndarray:
    """Spectral-subtraction denoiser (a lightweight noisereduce equivalent).

    Estimates a stationary noise magnitude spectrum from the quietest frames
    (``noise_percentile`` of frame energies), subtracts ``oversubtract`` × that
    floor from every frame's magnitude spectrum with a spectral floor, then
    inverts the STFT. Good for fan/hiss/crowd stationary noise; not for
    non-stationary babble — that is what diarization/ASR robustness is for.
    """
    if len(audio) < n_fft:
        return audio
    freqs, times, Z = signal.stft(audio, fs=sr, nperseg=n_fft, noverlap=n_fft - hop)
    mag = np.abs(Z)
    power = mag ** 2

    frame_energy = power.sum(axis=0)
    cutoff = np.percentile(frame_energy, noise_percentile)
    noise_frames = frame_energy <= max(cutoff, 1e-12)
    if noise_frames.sum() < 1:
        noise_frames = np.argsort(frame_energy)[: max(1, len(frame_energy) // 5)]
        mask = np.zeros(len(frame_energy), bool)
        mask[noise_frames] = True
        noise_frames = mask

    noise_mag = np.median(mag[:, noise_frames], axis=1, keepdims=True)
    clean_mag = np.maximum(mag - oversubtract * noise_mag, 0.15 * mag)
    Z_clean = clean_mag * np.exp(1j * np.angle(Z))
    _, x = signal.istft(Z_clean, fs=sr, nperseg=n_fft, noverlap=n_fft - hop)
    n = min(len(audio), len(x))
    return x[:n].astype(np.float32)


# ---------------------------------------------------------------- features

def frame_signal(audio: np.ndarray, sr: int, win: float = 0.025, hop: float = 0.010):
    """Yield framed windows: ``(n_frames, n_samples)``."""
    n = int(win * sr)
    h = int(hop * sr)
    if len(audio) < n:
        return np.zeros((0, n), dtype=np.float32)
    count = 1 + (len(audio) - n) // h
    idx = np.arange(n)[None, :] + h * np.arange(count)[:, None]
    return audio[idx].astype(np.float32)


def _mel_filterbank(sr: int, n_fft: int, n_mels: int = 26) -> np.ndarray:
    """Triangular mel filterbank, ``(n_mels, n_freq_bins)``."""
    def hz_to_mel(f):
        return 2595.0 * np.log10(1.0 + f / 700.0)

    def mel_to_hz(m):
        return 700.0 * (10.0 ** (m / 2595.0) - 1.0)

    n_bins = n_fft // 2 + 1
    freqs = np.linspace(0, sr / 2, n_bins)
    mels = np.linspace(hz_to_mel(0), hz_to_mel(sr / 2), n_mels + 2)
    hz = mel_to_hz(mels)
    fb = np.zeros((n_mels, n_bins), dtype=np.float32)
    for i in range(n_mels):
        left, center, right = hz[i], hz[i + 1], hz[i + 2]
        up = (freqs - left) / max(center - left, 1e-9)
        down = (right - freqs) / max(right - center, 1e-9)
        fb[i] = np.maximum(0.0, np.minimum(up, down))
    return fb


def mfcc(
    audio: np.ndarray,
    sr: int = TARGET_SR,
    n_mfcc: int = 13,
    n_mels: int = 26,
    n_fft: int = 512,
) -> np.ndarray:
    """Mel-frequency cepstral coefficients, ``(n_frames, n_mfcc)``.

    Standard front-end: pre-emphasis → 25 ms frames → power spectrum →
    mel filterbank → log energies → DCT. Used for speaker/language
    verification features and for feeding small acoustic models.
    """
    if len(audio) == 0:
        return np.zeros((0, n_mfcc), dtype=np.float32)
    audio = np.append(audio[0], audio[1:] - 0.97 * audio[:-1])
    frames = frame_signal(audio, sr)
    if frames.shape[0] == 0:
        return np.zeros((0, n_mfcc), dtype=np.float32)
    frames *= np.hamming(frames.shape[1])
    spec = np.abs(np.fft.rfft(frames, n=n_fft, axis=1)) ** 2
    fb = _mel_filterbank(sr, n_fft, n_mels)
    mel_e = np.maximum(spec @ fb.T, 1e-10)
    logmel = np.log(mel_e)
    from scipy.fftpack import dct

    return dct(logmel, type=2, axis=1, norm="ortho")[:, :n_mfcc].astype(np.float32)


def spectral_features(audio: np.ndarray, sr: int = TARGET_SR) -> dict:
    """Compact summary vector for dashboards / similarity checks."""
    if len(audio) == 0:
        return {}
    f = mfcc(audio, sr)
    if f.shape[0] == 0:
        return {}
    return {
        "duration_s": round(len(audio) / sr, 2),
        "n_frames": int(f.shape[0]),
        "mfcc_mean": f.mean(axis=0).round(3).tolist(),
        "mfcc_std": f.std(axis=0).round(3).tolist(),
        "zcr_mean": float(
            np.mean(
                np.abs(np.diff(np.signbit(audio).astype(np.int8)))
            )
        ),
    }


# ---------------------------------------------------------------- VAD

@dataclass
class Segment:
    start: float  # seconds
    end: float
    rms: float


def voice_activity(
    audio: np.ndarray,
    sr: int = TARGET_SR,
    frame_ms: float = 30.0,
    hop_ms: float = 10.0,
    threshold_db: float = -40.0,
    min_speech_ms: float = 200.0,
    min_silence_ms: float = 300.0,
) -> list[Segment]:
    """Energy-based voice activity detection.

    Frames louder than ``threshold_db`` relative to full scale count as
    speech; segments shorter than ``min_speech_ms`` are dropped and short
    silences are bridged — standard endpointing before ASR.
    """
    if len(audio) == 0:
        return []
    n = int(frame_ms * sr / 1000)
    h = int(hop_ms * sr / 1000)
    count = max(1, (len(audio) - n) // h + 1)
    idx = np.arange(n)[None, :] + h * np.arange(count)[:, None]
    frames = audio[idx]
    rms = np.sqrt(np.mean(frames**2, axis=1) + 1e-12)
    db = 20 * np.log10(rms + 1e-12)
    thresh = 20 * np.log10(10 ** (threshold_db / 20) + 1e-12)
    voiced = db > thresh

    segs: list[Segment] = []
    i = 0
    min_frames = int(min_speech_ms / hop_ms)
    bridge = int(min_silence_ms / hop_ms)
    while i < count:
        if not voiced[i]:
            i += 1
            continue
        j = i
        silence = 0
        while j < count:
            if voiced[j]:
                silence = 0
                j += 1
            else:
                silence += 1
                if silence > bridge:
                    break
                j += 1
        end = max(i, j - silence)
        if end - i >= min_frames:
            segs.append(
                Segment(
                    start=round(i * hop_ms / 1000, 3),
                    end=round(min(end * hop_ms / 1000 + frame_ms / 1000, len(audio) / sr), 3),
                    rms=round(float(rms[i:end].mean()), 4),
                )
            )
        i = j
    return segs


# ---------------------------------------------------------------- diarization

def diarize(
    path_or_audio,
    sr: int | None = None,
    num_speakers: int | None = None,
) -> list[dict]:
    """Speaker diarization via pyannote.audio, when available.

    Returns ``[{start, end, speaker}]`` seconds-based segments, or ``[]`` when
    pyannote/HF credentials are not configured. Wire a real HF token via
    ``HF_TOKEN`` env var; never commit it.
    """
    try:
        import torch  # noqa: F401
        from pyannote.audio import Pipeline  # type: ignore
    except Exception:
        return []

    import os

    token = os.getenv("HF_TOKEN")
    if not token:
        return []
    try:
        audio, sr = (
            (path_or_audio, sr)
            if isinstance(path_or_audio, np.ndarray)
            else preprocess(path_or_audio)
        )
        pipe = Pipeline.from_pretrained(
            "pyannote/speaker-diarization-3.1", use_auth_token=token
        )
        out = pipe({"waveform": torch.from_numpy(audio)[None], "sample_rate": sr})
        segs = []
        for turn, _, speaker in out.itertracks(yield_label=True):
            segs.append(
                {
                    "start": round(turn.start, 3),
                    "end": round(turn.end, 3),
                    "speaker": speaker,
                }
            )
        if num_speakers:
            # collapse to the N most-talkative speakers
            from collections import Counter

            keep = {s for s, _ in Counter(x["speaker"] for x in segs).most_common(num_speakers)}
            segs = [x for x in segs if x["speaker"] in keep]
        return segs
    except Exception:
        return []
