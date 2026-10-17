# One image for both the web UI (app.py) and the workers (worker.py); docker-compose.yml picks the command.
FROM python:3.12-slim

COPY --from=ghcr.io/astral-sh/uv:0.12.1 /uv /usr/local/bin/uv

WORKDIR /app
# Dependencies first so code edits don't reinstall them. This folder's lockfile lives in the repo-root
# workspace (outside the build context), so install straight from pyproject.toml.
COPY pyproject.toml .
RUN uv pip install --system --no-cache -r pyproject.toml

COPY app.py worker.py ./
COPY static ./static

ENV PYTHONUNBUFFERED=1
