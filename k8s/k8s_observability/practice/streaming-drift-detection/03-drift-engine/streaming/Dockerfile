# Build from the 03-drift-engine/ directory (needs ../common/), not from
# streaming/ itself:
#   docker build -f streaming/Dockerfile -t drift-streaming:local .
FROM python:3.12-slim

WORKDIR /app
COPY streaming/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY common/ ./common/
COPY streaming/run_streaming_drift_check.py .

CMD ["python", "run_streaming_drift_check.py"]
