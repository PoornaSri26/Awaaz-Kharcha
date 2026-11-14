FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt requirements-dev.txt ./
RUN pip install -q -r requirements-dev.txt
COPY . .
EXPOSE 8100
CMD ["uvicorn", "pipeline.api.app:app", "--host", "0.0.0.0", "--port", "8100"]
