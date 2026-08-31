# Build from the 03-drift-engine/ directory (needs ../common/), not from
# batch/ itself:
#   docker build -f batch/Dockerfile -t drift-batch:local .
FROM python:3.12-slim

WORKDIR /app
COPY batch/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY common/ ./common/
COPY batch/run_batch_drift_check.py .

CMD ["python", "run_batch_drift_check.py"]
