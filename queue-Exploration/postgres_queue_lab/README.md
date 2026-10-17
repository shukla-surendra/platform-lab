# Postgres queue lab

Scripts behind section 6 of [postgres_as_a_queue.html](../postgres_as_a_queue.html):
how many pods can share one jobs table without processing a job twice. Plus a small job management app
built the same way, with a web UI and two workers, all in Docker. How much load it puts on Postgres, how to size it, and per-tenant limits are in [postgres_queue_case_study.html](../postgres_queue_case_study.html).

| File | What it is |
|---|---|
| `race_test.py` | 50 concurrent workers ("pods") claim 5,000 jobs with four claim strategies and count how many times each job was processed |
| `lease_test.py` | A pod stalls past its lease, a second pod reclaims the job, and a fencing token rejects the first pod's late write |
| `schema.sql` | DDL for the job app: `jobqueue.jobs`, `jobqueue.job_events`, `jobqueue.workers` (own schema, so the scripts above can't drop it) |
| `app.py` + `static/index.html` | Job management UI and its API |
| `worker.py` | A worker: claims with `SKIP LOCKED`, heartbeats, acks/nacks, is fenced on `attempts` |
| `Dockerfile` | One image for the web app and the workers |
| `tenant_limits.sql` + `tenant_limits_test.py` | Prototype of per-tenant limits (concurrency cap, token-bucket start rate, backlog quota, fair ordering) in a scratch `ratelab` schema, and a 20-worker test that checks every limit holds. Run: `uv run python tenant_limits_test.py` |

## Setup

Needs Docker, and [uv](https://docs.astral.sh/uv/) for the scripts.

```bash
cd postgres_queue_lab
docker compose up -d --build
docker compose ps            # wait until lab-postgres shows "(healthy)"
```

| What | Where |
|---|---|
| Job management UI | http://localhost:8000 (API docs at http://localhost:8000/docs) |
| Postgres | `localhost:55433` (user `app`, password `app`, database `app`) |
| Web UI (Adminer) | http://localhost:8081 (System `PostgreSQL`, server `postgres`, user/password/database `app`) |

## Scripts

Dependencies are in `pyproject.toml`; `uv run` installs them on first use. This folder is a member of the
repo-root uv workspace, so the lockfile is the root `uv.lock`.

```bash
uv run python race_test.py      # all four strategies
uv run python race_test.py skip_locked
uv run python lease_test.py
```

Each script drops and recreates its tables (`public.jobs`, `public.processed`), so you can rerun them as often
as you like. Open the `jobs` table in Adminer while `race_test.py` runs to watch statuses change.

## Job management app

`docker compose up` starts everything; nothing runs on your Mac except the browser.

- `migrate` applies `schema.sql` and exits (it's safe to rerun, so it runs on every `up`).
- `web` serves the UI and API on port 8000.
- `worker-1` and `worker-2` process jobs. If one crashes, Docker restarts it.

**In the UI:**

- **Submit** jobs with a queue, priority, max attempts, delay and count. The preset buttons fill in a scenario.
- **Workers**: a dot that pulses on each heartbeat, its state (idle / busy / paused / draining / stopped), the heartbeat count and how long ago it was last seen, the current job with its progress and the time left on its lease, and how many jobs it finished. **Pause / Resume** takes effect on the worker's next heartbeat. **Forget** removes a dead worker's row.
- **Jobs**: status, attempts, worker, progress, heartbeat count and how long ago it arrived, lease time left, when a queued job is due. **Cancel** stops a queued job at once. For a running job the worker picks the cancel up on its next heartbeat and writes the cancel ack itself. **Retry** and **Delete** work on finished jobs.
- **Job details** (click a row): the lease and heartbeat details, the payload and result, and the full history with each step labelled (receipt ack, ack, nack → retry, nack → dead, cancel ack, reclaim, fenced out).

**How a job flows** (lease 5s, heartbeat every 1s):

1. **Claim = receipt ack.** A worker takes the next due job (highest priority first) with `FOR UPDATE SKIP LOCKED`,
   bumps `attempts` (the fencing token) and gets a lease.
2. **Heartbeat.** Every second the worker updates its `workers` row, even when idle, which is how the UI tells idle
   from dead. While busy it also pushes the job's lease forward, reports progress, and reads `cancel_requested`.
3. **Ack / nack.** Success sets the job to `succeeded`. A failure is a nack: the job goes back to `queued` with a
   2s, 4s, 8s… backoff, or becomes `dead` after `max_attempts`.
4. **Lease expiry.** If a worker stops heartbeating for 5s (crash or freeze), any worker may reclaim the job. The old
   worker's late writes include `attempts = <its attempt>` in the WHERE clause, match nothing, and are discarded.
5. **Graceful stop.** `docker compose stop` sends SIGTERM. The worker finishes its current job (it has up to 30s),
   then marks itself stopped.

Workers don't run real code. The payload says what to simulate:

| Payload key | Effect |
|---|---|
| `seconds` | how long to work (default: random 1–4) |
| `fail_rate` | chance the attempt fails, 0–1 (default 0) |
| `stall_seconds` | attempt 1 only: the worker freezes this long with no heartbeats. Over 5s, the other worker reclaims the job and the frozen one is fenced out |
| `crash` | attempt 1 only: the worker process exits half-way. Docker restarts it, the lease expires, and the job is reclaimed |

No Postgres extensions are needed: `SKIP LOCKED`, `jsonb`, identity columns and `LISTEN/NOTIFY` are all built in.

```bash
docker compose logs -f worker-1 worker-2          # watch claims, acks and fencing
docker compose up -d --build web worker-1 worker-2  # after editing app.py / worker.py / index.html
docker compose run -d --name lab-jobs-worker-3 worker-1 python worker.py --name worker-3   # a third worker
```

To start the job tables over:

```bash
docker compose exec -T postgres psql -U app -d app -c 'DROP SCHEMA jobqueue CASCADE'
docker compose up -d --force-recreate migrate
```

You can also run the app outside Docker against the same database:
`uv run uvicorn app:app --reload --port 8000` and `uv run python worker.py --name local-1`.

When you're done:

```bash
docker compose down -v       # stop and delete all tables and data
```

## How the compose file works

- **Postgres** listens on `55433` on your Mac (not the usual 5432, so it won't clash with a local Postgres).
  `max_connections=200` because `race_test.py` opens 50 worker connections at once, and the default is 100.
- **Adminer** is a small web UI. It reaches Postgres as `postgres:5432` inside Docker, and only starts once
  Postgres is healthy. It uses port 8081 so it can run alongside the Kafka UI (8080) from `rabbitmq_kafka_lab`.
- **migrate / web / workers** share one image (`Dockerfile`) and reach Postgres as `postgres:5432`. Web and workers
  wait for `migrate` to finish, so the tables always exist before anything uses them.
