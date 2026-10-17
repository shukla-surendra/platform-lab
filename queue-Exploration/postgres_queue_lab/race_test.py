"""50 concurrent workers ("pods") claim jobs from one table with different claim strategies.
Every claimed job is recorded in `processed`; any job_id appearing more than once was processed twice."""
import sys, threading, time
import psycopg

DSN = "postgresql://app:app@localhost:55433/app"
JOBS, WORKERS = 5000, 50

SETUP = """
DROP TABLE IF EXISTS jobs, processed;
CREATE TABLE jobs (id bigserial PRIMARY KEY, status text NOT NULL DEFAULT 'queued',
  attempts int NOT NULL DEFAULT 0, locked_by text, locked_until timestamptz,
  run_after timestamptz NOT NULL DEFAULT now());
CREATE INDEX jobs_ready ON jobs (run_after) WHERE status = 'queued';
CREATE TABLE processed (job_id bigint, worker text);
INSERT INTO jobs (status) SELECT 'queued' FROM generate_series(1, %s);
"""

STRATEGIES = {
  # 1. Naive: read, then update without re-checking status. Race window between the two statements.
  "naive_select_then_update": [
    "SELECT id FROM jobs WHERE status = 'queued' ORDER BY id LIMIT 1",
    "UPDATE jobs SET status = 'running', locked_by = %(me)s WHERE id = %(id)s RETURNING id"],
  # 2. Optimistic: same, but the UPDATE re-checks status and the worker retries if it lost the race.
  "optimistic_recheck": [
    "SELECT id FROM jobs WHERE status = 'queued' ORDER BY id LIMIT 1",
    "UPDATE jobs SET status = 'running', locked_by = %(me)s WHERE id = %(id)s AND status = 'queued' RETURNING id"],
  # 3. FOR UPDATE without SKIP LOCKED: correct, but workers queue up behind each other's locks.
  "for_update_no_skip": [
    """UPDATE jobs SET status = 'running', locked_by = %(me)s
       WHERE id = (SELECT id FROM jobs WHERE status = 'queued' ORDER BY id FOR UPDATE LIMIT 1)
       RETURNING id"""],
  # 4. The documented claim: FOR UPDATE SKIP LOCKED.
  "skip_locked": [
    """UPDATE jobs SET status = 'running', locked_by = %(me)s
       WHERE id = (SELECT id FROM jobs WHERE status = 'queued' ORDER BY id FOR UPDATE SKIP LOCKED LIMIT 1)
       RETURNING id"""],
}

def worker(name, stmts, stats):
    lost = 0
    with psycopg.connect(DSN, autocommit=True) as conn:
        while True:
            if len(stmts) == 1:
                row = conn.execute(stmts[0], {"me": name}).fetchone()
                if row is None:
                    # empty result can also mean "row changed under me" for no-skip; re-check
                    if conn.execute("SELECT 1 FROM jobs WHERE status='queued' LIMIT 1").fetchone():
                        lost += 1; continue
                    break
            else:
                cand = conn.execute(stmts[0]).fetchone()
                if cand is None:
                    break
                row = conn.execute(stmts[1], {"me": name, "id": cand[0]}).fetchone()
                if row is None:
                    lost += 1; continue
            conn.execute("INSERT INTO processed VALUES (%s, %s)", (row[0], name))   # "do the work"
            conn.execute("UPDATE jobs SET status = 'done' WHERE id = %s", (row[0],))
    stats[name] = lost

def run(strategy):
    with psycopg.connect(DSN, autocommit=True) as conn:
        conn.execute(SETUP % JOBS)
    stats, threads = {}, []
    t0 = time.perf_counter()
    for i in range(WORKERS):
        t = threading.Thread(target=worker, args=(f"pod-{i:02d}", STRATEGIES[strategy], stats))
        t.start(); threads.append(t)
    for t in threads: t.join()
    elapsed = time.perf_counter() - t0
    with psycopg.connect(DSN) as conn:
        total, distinct = conn.execute("SELECT count(*), count(DISTINCT job_id) FROM processed").fetchone()
        dup_jobs, worst = conn.execute("""SELECT count(*), coalesce(max(c),0) FROM
            (SELECT job_id, count(*) c FROM processed GROUP BY job_id HAVING count(*) > 1) d""").fetchone()
        pods_used = conn.execute("SELECT count(DISTINCT worker) FROM processed").fetchone()[0]
    print(f"{strategy:26} processed={total:5} distinct={distinct:5} jobs_done_twice+={dup_jobs:4} "
          f"max_times_one_job={worst} lost_races={sum(stats.values()):5} pods_that_worked={pods_used} time={elapsed:.2f}s")

for s in (sys.argv[1:] or STRATEGIES):
    run(s)
