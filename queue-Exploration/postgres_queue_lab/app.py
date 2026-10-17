"""Job management UI + API over the jobqueue schema (see schema.sql).
Runs in docker compose as the `web` service: http://localhost:8000 (API docs at /docs).
Outside Docker:  uv run uvicorn app:app --reload --port 8000"""
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path
import os

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb
from psycopg_pool import ConnectionPool
from pydantic import BaseModel, Field

DSN = os.environ.get("DATABASE_URL", "postgresql://app:app@localhost:55433/app")
STATUSES = ("queued", "running", "succeeded", "dead", "cancelled")
STALE_AFTER = 3   # seconds without a worker heartbeat before the UI calls it stale

pool = ConnectionPool(DSN, min_size=1, max_size=10, open=False, kwargs={"row_factory": dict_row, "autocommit": True})


@asynccontextmanager
async def lifespan(_: FastAPI):
    pool.open(wait=True)
    yield
    pool.close()


app = FastAPI(title="Postgres job queue", lifespan=lifespan)


class NewJob(BaseModel):
    kind: str = Field(min_length=1)
    queue: str = "default"
    payload: dict = {}
    priority: int = 0
    max_attempts: int = Field(3, ge=1, le=50)
    run_after: datetime | None = None    # None = run now
    count: int = Field(1, ge=1, le=1000)  # enqueue several identical jobs at once (handy for demos)


@app.get("/")
def index():
    return FileResponse(Path(__file__).parent / "static" / "index.html")


@app.get("/api/stats")
def stats():
    # Ages are computed in SQL so they use the database clock, the same one leases are measured against.
    with pool.connection() as c:
        rows = c.execute("SELECT status, count(*) AS n FROM jobqueue.jobs GROUP BY status").fetchall()
        counts = {s: 0 for s in STATUSES} | {r["status"]: r["n"] for r in rows}
        workers = c.execute("""
            SELECT w.name, w.queues, w.state, w.current_job, w.paused, w.heartbeats, w.succeeded, w.failed,
                   extract(epoch FROM now() - w.last_seen)::float  AS seen_ago,
                   extract(epoch FROM now() - w.started_at)::float AS uptime,
                   CASE WHEN w.state = 'stopped' THEN 'offline'
                        WHEN w.last_seen < now() - make_interval(secs => %s) THEN 'stale' ELSE 'alive' END AS health,
                   j.kind AS job_kind, j.progress AS job_progress,
                   extract(epoch FROM j.locked_until - now())::float AS lease_left
            FROM jobqueue.workers w
            LEFT JOIN jobqueue.jobs j ON j.id = w.current_job AND j.status = 'running' AND j.locked_by = w.name
            ORDER BY w.name""", (STALE_AFTER,)).fetchall()
        queues = [r["queue"] for r in c.execute("SELECT DISTINCT queue FROM jobqueue.jobs ORDER BY 1")]
    return {"counts": counts, "workers": workers, "queues": queues, "stale_after": STALE_AFTER}


JOB_COLUMNS = """id, queue, kind, payload, status, priority, attempts, max_attempts, run_after, locked_by, locked_until,
    claimed_at, heartbeat_at, heartbeats, progress, cancel_requested, last_error, result, created_at, updated_at, finished_at,
    extract(epoch FROM run_after - now())::float     AS due_in,
    extract(epoch FROM locked_until - now())::float  AS lease_left,
    extract(epoch FROM now() - heartbeat_at)::float  AS heartbeat_ago,
    extract(epoch FROM now() - updated_at)::float    AS updated_ago"""


@app.get("/api/jobs")
def list_jobs(status: str | None = None, queue: str | None = None, kind: str | None = None, limit: int = 100):
    if status and status not in STATUSES:
        raise HTTPException(400, f"status must be one of {STATUSES}")
    with pool.connection() as c:
        return c.execute(f"""
            SELECT {JOB_COLUMNS} FROM jobqueue.jobs
            WHERE (%(status)s::text IS NULL OR status = %(status)s)
              AND (%(queue)s::text  IS NULL OR queue  = %(queue)s)
              AND (%(kind)s::text   IS NULL OR kind ILIKE '%%' || %(kind)s || '%%')
            ORDER BY id DESC LIMIT %(limit)s""",
            {"status": status, "queue": queue, "kind": kind, "limit": min(limit, 500)}).fetchall()


@app.get("/api/jobs/{job_id}")
def get_job(job_id: int):
    with pool.connection() as c:
        job = c.execute(f"SELECT {JOB_COLUMNS} FROM jobqueue.jobs WHERE id = %s", (job_id,)).fetchone()
        if job is None:
            raise HTTPException(404, "job not found")
        job["events"] = c.execute(
            "SELECT at, event, worker, detail FROM jobqueue.job_events WHERE job_id = %s ORDER BY id", (job_id,)).fetchall()
    return job


@app.post("/api/jobs", status_code=201)
def create_jobs(j: NewJob):
    with pool.connection() as c, c.transaction():
        ids = [r["id"] for r in c.execute("""
            INSERT INTO jobqueue.jobs (queue, kind, payload, priority, max_attempts, run_after)
            SELECT %s, %s, %s, %s, %s, coalesce(%s, now()) FROM generate_series(1, %s)
            RETURNING id""",
            (j.queue, j.kind, Jsonb(j.payload), j.priority, j.max_attempts, j.run_after, j.count)).fetchall()]
        c.execute("INSERT INTO jobqueue.job_events (job_id, event, worker) SELECT unnest(%s::bigint[]), 'enqueued', 'ui'", (ids,))
    return {"ids": ids}


@app.post("/api/jobs/{job_id}/cancel")
def cancel_job(job_id: int):
    with pool.connection() as c, c.transaction():
        # Not running, or running with nobody holding a live lease: cancel straight away.
        row = c.execute("""
            UPDATE jobqueue.jobs SET status = 'cancelled', finished_at = now(), locked_by = NULL, locked_until = NULL
            WHERE id = %s AND (status = 'queued' OR (status = 'running' AND locked_until < now()))
            RETURNING id, status""", (job_id,)).fetchone()
        if row:
            c.execute("INSERT INTO jobqueue.job_events (job_id, event, worker) VALUES (%s, 'cancelled', 'ui')", (job_id,))
            return row
        # Running on a live worker: the worker owns the row, so ask it. It sees the flag on its next heartbeat,
        # stops, and writes 'cancelled' itself (the cancel acknowledgement).
        row = c.execute("""
            UPDATE jobqueue.jobs SET cancel_requested = true
            WHERE id = %s AND status = 'running' AND NOT cancel_requested
            RETURNING id, status, cancel_requested""", (job_id,)).fetchone()
        if row:
            c.execute("INSERT INTO jobqueue.job_events (job_id, event, worker, detail) VALUES (%s, 'cancel_requested', 'ui', %s)",
                      (job_id, "waiting for the worker to acknowledge on its next heartbeat"))
            return row
        job = c.execute("SELECT status, cancel_requested FROM jobqueue.jobs WHERE id = %s", (job_id,)).fetchone()
    if job is None:
        raise HTTPException(404, "job not found")
    if job["cancel_requested"]:
        raise HTTPException(409, "cancel already requested; waiting for the worker's acknowledgement")
    raise HTTPException(409, f"job is {job['status']}; only queued or running jobs can be cancelled")


@app.post("/api/jobs/{job_id}/retry")
def retry_job(job_id: int):
    # Fresh start: attempts back to 0 so it gets its full max_attempts again.
    with pool.connection() as c, c.transaction():
        row = c.execute("""
            UPDATE jobqueue.jobs SET status = 'queued', attempts = 0, run_after = now(), last_error = NULL, result = NULL,
                   locked_by = NULL, locked_until = NULL, claimed_at = NULL, heartbeat_at = NULL, heartbeats = 0,
                   progress = 0, cancel_requested = false, finished_at = NULL
            WHERE id = %s AND status IN ('dead', 'cancelled', 'succeeded') RETURNING id, status""", (job_id,)).fetchone()
        if row:
            c.execute("INSERT INTO jobqueue.job_events (job_id, event, worker) VALUES (%s, 'retried', 'ui')", (job_id,))
            return row
        job = c.execute("SELECT status FROM jobqueue.jobs WHERE id = %s", (job_id,)).fetchone()
    if job is None:
        raise HTTPException(404, "job not found")
    raise HTTPException(409, f"job is {job['status']}; only finished jobs can be retried")


@app.delete("/api/jobs/{job_id}")
def delete_job(job_id: int):
    with pool.connection() as c:
        row = c.execute("DELETE FROM jobqueue.jobs WHERE id = %s AND status <> 'running' RETURNING id", (job_id,)).fetchone()
    if row is None:
        raise HTTPException(409, "job not found, or running (cancel it first)")
    return row


@app.post("/api/purge")
def purge_finished():
    """Delete succeeded and cancelled jobs (keeps dead ones so you can inspect them)."""
    with pool.connection() as c:
        n = c.execute("DELETE FROM jobqueue.jobs WHERE status IN ('succeeded', 'cancelled')").rowcount
    return {"deleted": n}


@app.post("/api/workers/{name}/{action}")
def worker_command(name: str, action: str):
    """pause / resume: the worker reads the flag on its next heartbeat. Pausing lets the current job finish."""
    if action not in ("pause", "resume"):
        raise HTTPException(404, "action must be pause or resume")
    with pool.connection() as c:
        row = c.execute("UPDATE jobqueue.workers SET paused = %s WHERE name = %s RETURNING name, paused",
                        (action == "pause", name)).fetchone()
    if row is None:
        raise HTTPException(404, "worker not found")
    return row


@app.delete("/api/workers/{name}")
def forget_worker(name: str):
    """Remove a stopped or stale worker's row. A live worker would just keep heartbeating, so refuse."""
    with pool.connection() as c:
        row = c.execute("""DELETE FROM jobqueue.workers WHERE name = %s
                           AND (state = 'stopped' OR last_seen < now() - make_interval(secs => %s)) RETURNING name""",
                        (name, STALE_AFTER)).fetchone()
    if row is None:
        raise HTTPException(409, "worker not found, or still alive")
    return row
