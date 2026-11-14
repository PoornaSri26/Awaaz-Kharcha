"""Locust load test for POST /v1/jobs — run: locust -f pipeline/benchmarks/locustfile.py --host http://localhost:8100"""
from locust import HttpUser, task, between
import glob, os

CLIPS = sorted(glob.glob("eval/clips/*.wav")) or ["eval/clips/clip_00_clean.wav"]

class VoiceUser(HttpUser):
    wait_time = between(0.5, 2)
    @task
    def upload(self):
        path = CLIPS[self.client.environment.runner.user_count % len(CLIPS)]
        with open(path, "rb") as f:
            self.client.post("/v1/jobs", files={"file": (os.path.basename(path), f, "audio/wav")}, timeout=60)
