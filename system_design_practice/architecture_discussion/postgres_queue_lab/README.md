# Postgres queue lab

Scripts behind section 6 of [postgres_as_a_queue.html](../postgres_as_a_queue.html):
how many pods can share one jobs table without processing a job twice.

| Script | What it shows |
|---|---|
| `race_test.py` | 50 concurrent workers ("pods") claim 5,000 jobs with four claim strategies and count how many times each job was processed |
| `lease_test.py` | A pod stalls past its lease, a second pod reclaims the job, and a fencing token rejects the first pod's late write |

## Setup

Needs Docker and [uv](https://docs.astral.sh/uv/).

```bash
cd postgres_queue_lab
docker compose up -d
docker compose ps            # wait until lab-postgres shows "(healthy)"
```

| What | Where |
|---|---|
| Postgres | `localhost:55433` (user `app`, password `app`, database `app`) |
| Web UI (Adminer) | http://localhost:8081 (System `PostgreSQL`, server `postgres`, user/password/database `app`) |

## Run

```bash
uv run --no-project --with 'psycopg[binary]' python race_test.py      # all four strategies
uv run --no-project --with 'psycopg[binary]' python race_test.py skip_locked
uv run --no-project --with 'psycopg[binary]' python lease_test.py
```

Each script drops and recreates its tables, so you can rerun them as often as you like.
Open the `jobs` table in Adminer while `race_test.py` runs to watch statuses change.

When you're done:

```bash
docker compose down -v       # stop and delete all tables and data
```

## How the compose file works

- **Postgres** listens on `55433` on your Mac (not the usual 5432, so it won't clash with a local Postgres).
  `max_connections=200` because `race_test.py` opens 50 worker connections at once, and the default is 100.
- **Adminer** is a small web UI. It reaches Postgres as `postgres:5432` inside Docker, and only starts once
  Postgres is healthy. It uses port 8081 so it can run alongside the Kafka UI (8080) from `rabbitmq_kafka_lab`.
