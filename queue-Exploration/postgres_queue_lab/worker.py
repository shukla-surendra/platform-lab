"""A worker ("pod") for the jobqueue schema. docker compose runs two (worker-1, worker-2); add more with
      docker compose run -d --name lab-jobs-worker-3 worker-1 python worker.py --name worker-3

Two threads per worker:
  main loop  claim a job (ack receipt) -> work -> ack (succeeded) / nack (failed: retry or dead) / ack cancel
  heartbeat  every second: mark this worker alive, read UI commands (pause), and for the current job renew
             its lease, report progress, and read cancel requests. If the renewal matches no row, another
             worker reclaimed the job after our lease expired: we lost it and must not write a result.

Jobs don't run real code; the payload describes what to simulate:
  seconds        how long to work                    (default random 1-4)
  fail_rate      chance the attempt fails, 0..1      (default 0)
  stall_seconds  stop heartbeating this long, 1s in  (default 0; > 5s lets another worker reclaim the job)
  crash          true = the process dies half-way    (Docker restarts it; the lease expires; job is reclaimed)
stall_seconds and crash only apply to the first attempt, so you can watch the retry recover."""
import argparse, os, random, signal, threading, time
import psycopg
from psycopg.types.json import Jsonb

DSN = os.environ.get("DATABASE_URL", "postgresql://app:app@localhost:55433/app")
LEASE_SECONDS = 5       # short on purpose so lease expiry is quick to see
HEARTBEAT_SECONDS = 1

# Next claimable job: queued and due, or running with an expired lease (its worker died or stalled).
# SKIP LOCKED lets many workers run this at once without blocking or double-claiming (see race_test.py).
CLAIM = """
WITH next AS (
    SELECT id, status AS prev_status, locked_by AS prev_worker FROM jobqueue.jobs
    WHERE queue = ANY(%(queues)s)
      AND ((status = 'queued' AND run_after <= now()) OR (status = 'running' AND locked_until < now()))
    ORDER BY priority DESC, run_after, id
    FOR UPDATE SKIP LOCKED LIMIT 1)
UPDATE jobqueue.jobs j
SET status = 'running', attempts = j.attempts + 1, locked_by = %(me)s,
    locked_until = now() + make_interval(secs => %(lease)s),
    claimed_at = now(), heartbeat_at = now(), heartbeats = 0, progress = 0
FROM next WHERE j.id = next.id
RETURNING j.id, j.kind, j.payload, j.attempts, j.max_attempts, j.cancel_requested, next.prev_status, next.prev_worker"""

# Every write after the claim is fenced on (id, attempts, locked_by): if our lease expired and another
# worker reclaimed the job, attempts has moved on and our late write matches zero rows.
FENCE = "id = %(id)s AND attempts = %(attempt)s AND locked_by = %(me)s AND status = 'running'"
RELEASE = "locked_by = NULL, locked_until = NULL"


class Shared:
    """State the main loop and heartbeat thread both touch."""
    def __init__(self):
        self.lock = threading.Lock()
        self.state = "idle"        # what the worker row shows
        self.job = None            # fence dict of the job being worked on
        self.progress = 0
        self.stall_until = 0.0     # monotonic time; heartbeats are skipped until then
        self.lost = False          # heartbeat found our lease gone
        self.cancel = False        # UI asked to cancel the current job
        self.paused = False        # UI asked this worker to stop taking new jobs
        self.stopping = False      # SIGTERM / Ctrl+C: finish the current job, then exit


def event(c, job_id, name, me, detail=None):
    c.execute("INSERT INTO jobqueue.job_events (job_id, event, worker, detail) VALUES (%s, %s, %s, %s)",
              (job_id, name, me, detail))


def heartbeat_loop(me, s: Shared):
    conn = None
    while True:
        time.sleep(HEARTBEAT_SECONDS)
        with s.lock:
            job, progress, state = s.job, s.progress, s.state
            stalled = time.monotonic() < s.stall_until
        if stalled:          # simulating a frozen process (GC pause, network blip): send nothing at all
            continue
        try:
            conn = conn or psycopg.connect(DSN, autocommit=True)
            row = conn.execute("""UPDATE jobqueue.workers SET last_seen = now(), heartbeats = heartbeats + 1,
                                  state = %s, current_job = %s WHERE name = %s RETURNING paused""",
                               (state, job and job["id"], me)).fetchone()
            renewed = None
            if job:
                renewed = conn.execute(f"""UPDATE jobqueue.jobs SET locked_until = now() + make_interval(secs => %(lease)s),
                                           heartbeat_at = now(), heartbeats = heartbeats + 1, progress = %(progress)s
                                           WHERE {FENCE} RETURNING cancel_requested""",
                                       {**job, "lease": LEASE_SECONDS, "progress": progress}).fetchone()
            with s.lock:
                s.paused = bool(row and row[0])
                if job and s.job is job:   # ignore a result for a job the main loop already finished
                    if renewed is None:
                        s.lost = True
                    else:
                        s.cancel = renewed[0]
        except psycopg.Error as e:
            print(f"{me}: heartbeat failed ({e.__class__.__name__}), retrying")
            conn = None


def work(job_id, attempt, payload, s: Shared):
    """Pretend to work. Returns 'ok', 'lost' or 'cancel'; raises on a simulated failure."""
    seconds = float(payload.get("seconds", random.uniform(1, 4)))
    first = attempt == 1
    stall, crash = first and float(payload.get("stall_seconds", 0)), first and bool(payload.get("crash"))
    start = time.monotonic()
    while (elapsed := time.monotonic() - start) < seconds:
        if stall and elapsed >= 1 and not s.stall_until:
            # Freeze the whole worker (like a GC pause or a suspended VM): no work, no heartbeats.
            print(f"job {job_id}: simulated stall, no heartbeats for {stall:.0f}s", flush=True)
            with s.lock:
                s.stall_until = time.monotonic() + stall
            time.sleep(stall)
            continue
        with s.lock:
            s.progress = min(99, int(elapsed / seconds * 100))
            if s.lost:
                return "lost"
            if s.cancel:
                return "cancel"
        if crash and elapsed >= seconds / 2:
            print(f"job {job_id}: simulated crash, process exiting", flush=True)
            os._exit(1)
        time.sleep(0.2)
    with s.lock:
        if s.lost:
            return "lost"
    if random.random() < float(payload.get("fail_rate", 0)):
        raise RuntimeError(f"simulated failure after {seconds:.1f}s")
    return "ok"


def run_one(c, me, queues, s: Shared):
    with c.transaction():
        row = c.execute(CLAIM, {"me": me, "queues": queues, "lease": LEASE_SECONDS}).fetchone()
        if row is None:
            return False
        job_id, kind, payload, attempt, max_attempts, cancel_requested, prev_status, prev_worker = row
        if prev_status == "running":
            event(c, job_id, "reclaimed", me, f"lease of {prev_worker} expired")
        event(c, job_id, "claimed", me, f"attempt {attempt}/{max_attempts}")
    fence = {"id": job_id, "attempt": attempt, "me": me}
    with s.lock:
        s.job, s.progress, s.stall_until, s.lost, s.cancel = fence, 0, 0.0, False, cancel_requested
        s.state = "draining" if s.stopping else "busy"
    print(f"{me}: job {job_id} ({kind}) attempt {attempt}/{max_attempts}")

    error = None
    if attempt > max_attempts:   # reclaimed after its last attempt's worker vanished
        outcome, error = "fail", f"{prev_worker}'s lease expired during the final attempt ({max_attempts}/{max_attempts})"
    else:
        try:
            outcome = work(job_id, attempt, payload, s)
        except Exception as e:
            outcome, error = "fail", str(e)

    with s.lock:   # stop heartbeating this job before the final write
        s.job, s.state = None, "draining" if s.stopping else "idle"

    with c.transaction():
        if outcome == "lost":
            event(c, job_id, "lost_lease", me, f"attempt {attempt}: heartbeat found the lease gone; result discarded")
            print(f"{me}: job {job_id} lost its lease, result discarded")
            return True
        if outcome == "ok":
            sql = f"""UPDATE jobqueue.jobs SET status = 'succeeded', progress = 100, result = %(result)s,
                      finished_at = now(), last_error = NULL, {RELEASE} WHERE {FENCE}"""
            args, name, detail = {"result": Jsonb({"worker": me, "attempt": attempt})}, "succeeded", None
        elif outcome == "cancel":
            sql = f"UPDATE jobqueue.jobs SET status = 'cancelled', finished_at = now(), {RELEASE} WHERE {FENCE}"
            args, name, detail = {}, "cancelled", "cancel acknowledged by worker"
        elif attempt >= max_attempts:
            sql = f"UPDATE jobqueue.jobs SET status = 'dead', last_error = %(err)s, finished_at = now(), {RELEASE} WHERE {FENCE}"
            args, name, detail = {"err": error}, "dead", error
        else:
            backoff = 2 ** attempt   # 2s, 4s, 8s, ...
            sql = f"""UPDATE jobqueue.jobs SET status = 'queued', last_error = %(err)s,
                      run_after = now() + make_interval(secs => %(backoff)s), {RELEASE} WHERE {FENCE}"""
            args, name, detail = {"err": error, "backoff": backoff}, "failed", f"{error}; retry in {backoff}s"
        if not c.execute(sql, {**fence, **args}).rowcount:
            # Someone reclaimed it while we weren't heartbeating: the fence rejected our late write.
            event(c, job_id, "lost_lease", me, f"attempt {attempt}: final write fenced out; result discarded")
            print(f"{me}: job {job_id} fenced out (stale attempt {attempt}), result discarded")
            return True
        event(c, job_id, name, me, detail)
        counter = "succeeded" if name == "succeeded" else "failed" if name in ("failed", "dead") else None
        if counter:
            c.execute(f"UPDATE jobqueue.workers SET {counter} = {counter} + 1 WHERE name = %s", (me,))
    print(f"{me}: job {job_id} {name}" + (f" ({detail})" if detail else ""))
    return True


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--name", default=os.environ.get("WORKER_NAME", f"worker-{os.getpid()}"))
    p.add_argument("--queues", default=os.environ.get("WORKER_QUEUES", "default"), help="comma-separated")
    a = p.parse_args()
    me, queues, s = a.name, a.queues.split(","), Shared()

    def stop(signum, _):
        if s.stopping:   # second signal: give up on the current job (its lease will expire)
            os._exit(1)
        print(f"{me}: {signal.Signals(signum).name} received, finishing current job then exiting")
        with s.lock:
            s.stopping, s.state = True, "draining"
    signal.signal(signal.SIGTERM, stop)   # docker stop
    signal.signal(signal.SIGINT, stop)    # Ctrl+C

    with psycopg.connect(DSN, autocommit=True) as c, psycopg.connect(DSN, autocommit=True) as listener:
        c.execute("""INSERT INTO jobqueue.workers (name, queues, state) VALUES (%s, %s, 'idle')
                     ON CONFLICT (name) DO UPDATE SET queues = EXCLUDED.queues, state = 'idle', current_job = NULL,
                       paused = false, started_at = now(), last_seen = now(), heartbeats = 0, succeeded = 0, failed = 0""",
                  (me, queues))
        listener.execute("LISTEN jobqueue_new")
        threading.Thread(target=heartbeat_loop, args=(me, s), daemon=True).start()
        print(f"{me}: watching queues {queues}, lease {LEASE_SECONDS}s, heartbeat every {HEARTBEAT_SECONDS}s")
        while not s.stopping:
            with s.lock:
                paused = s.paused
                s.state = "paused" if paused else "idle"
            if paused or not run_one(c, me, queues, s):
                # Idle: sleep until a job is inserted/requeued, or 1s at most (for delayed jobs, retries,
                # expired leases and pause/resume, which don't send a notification).
                for _ in listener.notifies(timeout=1, stop_after=1):
                    pass
        c.execute("UPDATE jobqueue.workers SET state = 'stopped', current_job = NULL, last_seen = now() WHERE name = %s", (me,))
        print(f"{me}: stopped")


if __name__ == "__main__":
    main()
