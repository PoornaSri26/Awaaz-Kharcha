# Benchmark results

Hardware: local Windows CPU (no GPU), faster-whisper `base` int8.
Dataset: 50 synthetic speech-like clips (`eval/clips`, 2 s each @ 16 kHz).
Command: `python -m pipeline.workers.runner bench eval/clips`

## Batch throughput (offline path)

| Metric | Value |
|---|---|
| Clips processed | 50 |
| Successful transcriptions | 15 (synthetic tones → empty transcript is expected) |
| p50 total latency | **6,291 ms** |
| Mean total latency | 11,252 ms |
| Throughput | **~320 clips/hour** (~0.09× realtime avg) |

## Per-stage latency (sample job)

| Stage | ms | Share |
|---|---|---|
| preprocess | 2.9 | <0.1% |
| denoise | 83.0 | ~0.6% |
| vad | 3.5 | <0.1% |
| langid | **12,922** | ~dominant |
| stt | 3,312 | ~24% |

## Key finding (STAR material)

`detect_language` runs a full Whisper transcription pass just to read
`info.language` — it was **~4× the STT stage itself** and the pipeline's
bottleneck. Fix applied: reuse the STT pass's language info instead of a
second transcription (or restrict langid to first 30 s). DSP stages are
<100 ms combined — noise reduction is *not* the latency problem.

## Denoise SNR gain (synthetic, 4 levels × 50 clips)

+9.9 dB @ 0 dB input → +12.1 dB @ 20 dB input.
