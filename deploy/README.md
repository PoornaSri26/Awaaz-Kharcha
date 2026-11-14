# AWS deployment

**Path:** S3 upload → EventBridge/S3 event → Lambda (`deploy/lambda/handler.py`)
→ `pipeline.workers.stages.run_job` → result JSON back to S3.

Steps:
1. `pip install -r requirements-dev.txt` then package repo + deps as Lambda layer
   (whisper/sklearn are heavy — use container-image Lambda for CPU whisper).
2. `cd deploy/terraform && terraform init && terraform apply`
3. Upload any `.ogg/.wav` to the bucket; read `<name>.result.json`.

Free-tier notes: Lambda 3008 MB/300 s covers whisper-base int8 on ~30 s clips;
S3+Lambda stay inside free tier at demo volume. For GPU whisper use
SageMaker endpoint instead of Lambda.
