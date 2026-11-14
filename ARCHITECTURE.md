# Awaaz Kharcha — pipeline architecture

## Online path (voice note → expense)

```
POST /v1/jobs (FastAPI, api/app.py)
  → pipeline/workers/stages.py::run_job
      preprocess (16 kHz mono + 80 Hz HP) → denoise (spectral subtraction)
      → VAD → langid (faster-whisper, optional) → STT → diarize (pyannote, opt)
      → NLP parse (rule parser + sklearn category clf) → JSON
  Every stage timed → stages_ms + total_ms + RTF in response.
```

Scale story: today it's synchronous in-process. The stage boundaries are pure
functions, so swapping to Redis+RQ/Celery workers or Cloud Tasks is a routing
change, not a rewrite. p50/p95 targets to measure via benchmarks/locustfile.py.

## Offline path (dataset building)

```
batch/flow.py: validate_clip (duration+SNR gate) → preprocess → features
  → Parquet (pyarrow) partitioned layout — Spark/Beam can consume unchanged.
validation/checks.py: schema + quality gates (upgrade path: Great Expectations /
  TFX Data Validation for drift checks at scale).
```

## Honest scaling note

Volume today is single-user demo scale — no Spark/Beam/TFX justified. Parquet
partitioning and stage purity mean the batch stage moves to Spark and the
online path to Beam streaming without redesign.
