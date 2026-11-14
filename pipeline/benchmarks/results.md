# Benchmark results

| Test | Result | Notes |
|---|---|---|
| Denoise SNR gain | +9.9 to +12.1 dB | synthetic clips, eval/make_clips.py |
| Whisper base | verified transcribing | CPU int8, faster-whisper |
| Online latency | TODO — run locustfile | needs live API + real clips |
| Batch throughput | TODO — run batch/flow.py | needs clip corpus |

Run: `uvicorn pipeline.api.app:app` then `locust -f pipeline/benchmarks/locustfile.py`
