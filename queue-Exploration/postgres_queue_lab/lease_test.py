"""Lease expiry: pod A claims a job, stalls past its lease without heartbeating, pod B reclaims it.
Shows both pods run the job, and how a fencing token (the attempt number) stops A's late write."""
import time, psycopg
DSN = "postgresql://app:app@localhost:55433/app"
CLAIM = """
UPDATE jobs SET status='running', attempts=attempts+1, locked_by=%(me)s,
       locked_until = now() + interval '2 seconds'
WHERE id = (SELECT id FROM jobs
            WHERE status='queued' OR (status='running' AND locked_until < now())
            ORDER BY id FOR UPDATE SKIP LOCKED LIMIT 1)
RETURNING id, attempts"""
with psycopg.connect(DSN, autocommit=True) as c:
    c.execute("DROP TABLE IF EXISTS jobs; CREATE TABLE jobs (id bigserial PRIMARY KEY, status text NOT NULL DEFAULT 'queued', attempts int NOT NULL DEFAULT 0, locked_by text, locked_until timestamptz, result text); INSERT INTO jobs DEFAULT VALUES;")
a = psycopg.connect(DSN, autocommit=True); b = psycopg.connect(DSN, autocommit=True)
ja = a.execute(CLAIM, {"me": "pod-A"}).fetchone(); print("pod-A claims job", ja[0], "attempt", ja[1])
print("pod-B tries immediately:", b.execute(CLAIM, {"me": "pod-B"}).fetchone(), "(nothing: A holds the lease)")
print("pod-A stalls 3s with no heartbeat (GC pause / network blip)..."); time.sleep(3)
jb = b.execute(CLAIM, {"me": "pod-B"}).fetchone(); print("pod-B reclaims job", jb[0], "attempt", jb[1], " <- job now running on TWO pods")
r = b.execute("UPDATE jobs SET status='done', result='B' WHERE id=%s AND attempts=%s", (jb[0], jb[1])); print("pod-B finishes, fenced update rows:", r.rowcount)
r = a.execute("UPDATE jobs SET status='done', result='A' WHERE id=%s AND attempts=%s", (ja[0], ja[1])); print("pod-A wakes, fenced update rows:", r.rowcount, "(rejected: stale attempt)")
print("final row:", a.execute("SELECT status, attempts, locked_by, result FROM jobs").fetchone())
