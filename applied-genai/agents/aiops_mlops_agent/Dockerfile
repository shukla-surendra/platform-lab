# One image, three roles (ops-server / knowledge-server / agent) selected by docker-compose's
# `command:` override per service -- the code is identical, only which entrypoint script runs
# differs. Keeps the image list to one Dockerfile instead of three near-duplicates.

FROM python:3.11-slim

# Without this, Python block-buffers stdout when it isn't a TTY (always true under `docker
# compose logs`), so daemon.py's/agent_cli.py's prints -- and ops-server's/knowledge-server's
# startup banners -- can sit invisible in a buffer indefinitely instead of showing up in logs.
ENV PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Overridden per-service by docker-compose.yml; this default just answers `docker run` sanely.
CMD ["python", "agent_cli.py", "--help"]
