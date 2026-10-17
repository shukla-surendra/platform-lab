-- Tables for the job management UI (app.py) and workers (worker.py).
-- Safe to run again: everything is CREATE ... IF NOT EXISTS / CREATE OR REPLACE.
-- `docker compose up` runs this automatically (the `migrate` service) before the web app and workers start.
-- Lives in its own schema so race_test.py / lease_test.py (which DROP public.jobs) can't touch it.
--
-- Reset:  docker compose exec -T postgres psql -U app -d app -c 'DROP SCHEMA jobqueue CASCADE'
--         docker compose up -d --force-recreate migrate
--
-- No extensions needed: SKIP LOCKED, jsonb, identity columns and LISTEN/NOTIFY are all core Postgres.

CREATE SCHEMA IF NOT EXISTS jobqueue;

-- One row per job. Life cycle:
--   queued -> running -> succeeded                 (worker acks success)
--                     -> queued again              (worker nacks: failed, attempts left, retried after a backoff)
--                     -> dead                      (failed on its last attempt)
--                     -> cancelled                 (UI asked; worker saw it on a heartbeat and acked the cancel)
--   queued -> cancelled                            (cancelled from the UI before a worker took it)
--   running, lease expired -> running on another worker   (worker died or stopped heartbeating: reclaimed)
CREATE TABLE IF NOT EXISTS jobqueue.jobs (
    id               bigint      GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    queue            text        NOT NULL DEFAULT 'default',
    kind             text        NOT NULL,                     -- what to run, e.g. 'send_email'
    payload          jsonb       NOT NULL DEFAULT '{}',
    status           text        NOT NULL DEFAULT 'queued'
                     CHECK (status IN ('queued', 'running', 'succeeded', 'dead', 'cancelled')),
    priority         int         NOT NULL DEFAULT 0,           -- higher runs first
    attempts         int         NOT NULL DEFAULT 0,           -- also the fencing token (see lease_test.py)
    max_attempts     int         NOT NULL DEFAULT 3 CHECK (max_attempts > 0),
    run_after        timestamptz NOT NULL DEFAULT now(),       -- not picked up before this (delays, backoff)
    -- Lease: who holds the job and until when. Heartbeats push locked_until forward.
    locked_by        text,
    locked_until     timestamptz,
    claimed_at       timestamptz,                              -- when the current attempt was claimed
    heartbeat_at     timestamptz,                              -- last heartbeat for the current attempt
    heartbeats       int         NOT NULL DEFAULT 0,           -- heartbeats in the current attempt
    progress         int         NOT NULL DEFAULT 0 CHECK (progress BETWEEN 0 AND 100),
    cancel_requested boolean     NOT NULL DEFAULT false,       -- UI sets it; worker sees it on its next heartbeat
    last_error       text,
    result           jsonb,
    created_at       timestamptz NOT NULL DEFAULT now(),
    updated_at       timestamptz NOT NULL DEFAULT now(),
    finished_at      timestamptz                               -- when the final ack (succeeded/dead/cancelled) landed
);

-- Claim query: "next queued job in this queue, highest priority, oldest first".
-- Partial, so finished jobs (most of the table over time) don't bloat it.
CREATE INDEX IF NOT EXISTS jobs_claim
    ON jobqueue.jobs (queue, priority DESC, run_after, id)
    WHERE status = 'queued';

-- Reclaiming jobs whose worker died: running jobs with an expired lease.
CREATE INDEX IF NOT EXISTS jobs_lease
    ON jobqueue.jobs (locked_until)
    WHERE status = 'running';

-- UI list: filter by status, newest first.
CREATE INDEX IF NOT EXISTS jobs_status_id
    ON jobqueue.jobs (status, id DESC);

-- Audit trail shown in the UI's job detail panel. Heartbeats are counted on the job row, not logged here.
CREATE TABLE IF NOT EXISTS jobqueue.job_events (
    id      bigint      GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    job_id  bigint      NOT NULL REFERENCES jobqueue.jobs (id) ON DELETE CASCADE,
    at      timestamptz NOT NULL DEFAULT now(),
    -- enqueued, claimed, reclaimed, succeeded, failed, dead, cancel_requested, cancelled, lost_lease, retried
    event   text        NOT NULL,
    worker  text,
    detail  text
);

CREATE INDEX IF NOT EXISTS job_events_job ON jobqueue.job_events (job_id, id);

-- One row per worker process. Each worker heartbeats its row every second, busy or idle, so the UI can
-- tell a live idle worker from a dead one. `paused` is a command from the UI, read on each heartbeat.
CREATE TABLE IF NOT EXISTS jobqueue.workers (
    name        text        PRIMARY KEY,
    queues      text[]      NOT NULL,
    state       text        NOT NULL CHECK (state IN ('idle', 'busy', 'paused', 'draining', 'stopped')),
    current_job bigint,
    paused      boolean     NOT NULL DEFAULT false,
    started_at  timestamptz NOT NULL DEFAULT now(),
    last_seen   timestamptz NOT NULL DEFAULT now(),
    heartbeats  bigint      NOT NULL DEFAULT 0,
    succeeded   int         NOT NULL DEFAULT 0,
    failed      int         NOT NULL DEFAULT 0
);

-- Keep updated_at current on every change.
CREATE OR REPLACE FUNCTION jobqueue.touch_updated_at() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
    NEW.updated_at := now();
    RETURN NEW;
END $$;

CREATE OR REPLACE TRIGGER jobs_touch
    BEFORE UPDATE ON jobqueue.jobs
    FOR EACH ROW EXECUTE FUNCTION jobqueue.touch_updated_at();

-- Wake idle workers the moment a job becomes claimable, instead of making them poll.
-- Workers LISTEN on 'jobqueue_new'; the payload is the queue name.
CREATE OR REPLACE FUNCTION jobqueue.notify_new_job() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
    PERFORM pg_notify('jobqueue_new', NEW.queue);
    RETURN NULL;
END $$;

CREATE OR REPLACE TRIGGER jobs_notify
    AFTER INSERT OR UPDATE OF status ON jobqueue.jobs
    FOR EACH ROW WHEN (NEW.status = 'queued')
    EXECUTE FUNCTION jobqueue.notify_new_job();
