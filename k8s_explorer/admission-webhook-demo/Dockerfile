FROM python:3.12-slim
WORKDIR /app
COPY webhook_server.py .
USER 65534:65534
ENTRYPOINT ["python", "webhook_server.py"]
