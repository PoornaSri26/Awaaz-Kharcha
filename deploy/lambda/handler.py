"""S3 -> Lambda -> pipeline worker -> result JSON back to S3.

Deploy: see deploy/terraform/main.tf (S3 bucket + event -> this Lambda).
The heavy deps (whisper, sklearn model) live in a Lambda layer or container
image; for CPU whisper use the container-image Lambda variant.
"""
import json, os, urllib.request
import boto3

s3 = boto3.client("s3")

def handler(event, context):
    results = []
    for record in event.get("Records", []):
        bucket = record["s3"]["bucket"]["name"]
        key = record["s3"]["object"]["key"]
        if not key.lower().endswith((".wav", ".ogg", ".mp3", ".m4a", ".flac")):
            continue
        local = f"/tmp/{os.path.basename(key)}"
        s3.download_file(bucket, key, local)
        try:
            # run the same stage chain the API uses
            from pipeline.workers.stages import run_job
            res = run_job(local, job_id=key)
            out = {"job_id": res.job_id, "ok": res.ok, "transcript": res.transcript,
                   "language": res.language, "expenses": res.expenses,
                   "stages_ms": res.stages_ms, "errors": res.errors}
        except Exception as e:
            out = {"job_id": key, "ok": False, "errors": [str(e)]}
        out_key = key.rsplit(".", 1)[0] + ".result.json"
        s3.put_object(Bucket=bucket, Key=out_key,
                      Body=json.dumps(out).encode(), ContentType="application/json")
        results.append(out_key)
    return {"processed": results}
