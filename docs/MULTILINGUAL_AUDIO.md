# Multilingual Audio Processing — Awaaz Kharcha

A voice-first expense tracker for Indian languages. Users speak (or forward a
WhatsApp voice note) and get structured expense records — amount, category,
date, merchant, payment mode — across **Hindi/Hinglish, Telugu, Tamil,
Bengali, Kannada, Malayalam and English**, including heavy code-mixing
("auto ke liye 150 diye", "nenu 200 petrol kosam kharchu chesanu").

Everything runs locally on CPU — no GPU, no model downloads required for the
core app.

---

## Pipeline

```
voice note / mic / upload
  → decode + resample 16 kHz mono        (awaaz/audio.py::load_audio, to_mono_16k)
  → 80 Hz high-pass (rumble/DC)          (audio.py::highpass)
  → spectral-subtraction denoise         (audio.py::denoise)
  → energy VAD endpointing               (audio.py::voice_activity)
  → language ID                          (stt_local.py::detect_language)
  → speech-to-text                       (Gnani Prisma API | faster-whisper)
  → optional speaker diarization         (audio.py::diarize, pyannote)
  → expense parsing                      (parser.py rules + nlp.py classifier)
  → SQLite + reports
```

Every stage is a pure function returning structured results, with per-stage
latency recorded (`stages_ms`) — the same chain powers the FastAPI service
(`api.py`, `pipeline/api/app.py`) and the AWS Lambda worker
(`deploy/lambda/handler.py`).

---

## Techniques

### Noise reduction — spectral subtraction
`denoise()` estimates a stationary noise magnitude spectrum from the quietest
STFT frames (20th percentile of frame energy), subtracts an oversubtraction
factor (1.5×) with a spectral floor, and inverts the STFT. Pure
numpy/scipy — no external model.

**Measured:** +9.9 dB mean SNR improvement at 0 dB input SNR, up to +12.1 dB
at 20 dB, across 50 synthetic speech-like clips at 4 noise levels
(`eval/make_clips.py`, `eval/` results in README).

### Feature extraction
- **MFCC** (13 coeffs) with delta + delta-delta — `mfcc_delta()`
- **Log-mel spectrogram** (64 mels) — `logmel_spectrogram()`
- **Pitch (F0)** via normalized autocorrelation — `pitch_f0()`
- **RMS envelope, spectral centroid, zero-crossing** — voicing/loudness cues

Hand-built mel filterbank + DCT; used for speaker/language cues and as
features for downstream small models.

### Voice activity detection
Energy-based endpointing: 30 ms frames, dB threshold relative to full scale,
200 ms minimum speech, 300 ms silence bridging. Trims silence before STT —
cuts transcription cost and latency on voice notes with leading/trailing
quiet.

### Language ID & code-mix handling
- **faster-whisper** per-file language detection + language hint
  (`stt_local.py`) — handles code-mixed speech where forced lang-ID fails
- **Gnani Prisma** auto-detects 10 Indic locales on the hosted path
- **hinglish** (romanised code-mix) is a first-class label in the
  fine-tuning dataset (`nlp/data/synthetic.jsonl`)

### Speaker diarization
Optional pyannote.audio integration (`audio.py::diarize`) gated on
`HF_TOKEN` — returns `[{start, end, speaker}]` segments; degrades to `[]`
when unconfigured so the app never blocks. Enables attributing expenses to
speakers in shared recordings.

### Inverse text normalization
Spoken number words survive as digits for the parser — "dedh sau" → usable
amount, "do sau pachaas" handled by the multilingual number-word lexicon.

---

## Measured results

| Metric | Result | Method |
|---|---|---|
| Denoise SNR gain | **+9.9 to +12.1 dB** | synthetic clips @ 0/5/10/20 dB SNR |
| Category classifier (TF-IDF+LR) | **95.5%** held-out accuracy | 1,326 lexicon examples |
| NLP fine-tune pipeline | verified end-to-end | HF Trainer, 3 scripts, LoRA option |
| Whisper base | transcribing verified | CPU int8, faster-whisper |
| API latency | per-stage `stages_ms` logged | `pipeline/results/job_log.jsonl` |

Load-test and WER numbers are tracked in `pipeline/benchmarks/results.md` —
reported as load-test figures, not production traffic.

---

## Code map

| File | Role |
|---|---|
| `awaaz/audio.py` | decode, resample, highpass, denoise, VAD, MFCC/mel/pitch, diarize hook, SNR utils |
| `awaaz/stt_local.py` | faster-whisper ASR + language ID (optional dep) |
| `awaaz/nlp.py` | sklearn category classifier (char n-gram TF-IDF + LR) |
| `awaaz/pipeline.py` | JSONL dataset export (Spark-ingestible) |
| `nlp/` | transformer fine-tuning: data gen, augment, train_*/eval, configs, Colab notebook |
| `pipeline/` | FastAPI service, worker stages, batch Parquet flow, validation, benchmarks |
| `api.py`, `pipeline/api/app.py` | REST endpoints |
| `deploy/` | AWS Lambda + Terraform (S3 → worker → result JSON) |
| `eval/` | clip generator, SNR benchmark, metrics helpers |

## Tests

`tests/test_audio.py` (11), `tests/test_pipeline_extras.py` (10),
`tests/test_nlp.py` (6) — 168+ tests covering DSP correctness, VAD
endpointing, MFCC shapes, pitch accuracy, denoise SNR gains, classifier
training/persistence, pipeline export, and API import guards.
