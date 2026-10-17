"""20 workers, one noisy tenant (A) with a big backlog and four small ones. Checks: running(A) never above
its cap, A's start rate stays within rate+burst, small tenants aren't stuck behind A, quota rejects.
Run:  uv run python tenant_limits_test.py   (recreates the ratelab schema; drop it with DROP SCHEMA ratelab CASCADE)"""
import collections, pathlib, threading, time
import psycopg
DSN = "postgresql://app:app@localhost:55433/app"
with psycopg.connect(DSN, autocommit=True) as c:
    c.execute((pathlib.Path(__file__).parent / "tenant_limits.sql").read_text())
    c.execute("""INSERT INTO ratelab.tenants (tenant_id, max_running, rate_per_sec, burst, tokens, max_queued) VALUES
      ('A', 3, 40, 10, 10, 1000), ('B', 2, 20, 5, 5, 100), ('C', 2, 20, 5, 5, 100), ('D', 2, 20, 5, 5, 100), ('E', 2, 20, 5, 5, 100)""")
    c.execute("SELECT ratelab.submit('A', 1000)")
    for t in "BCDE": c.execute("SELECT ratelab.submit(%s, 50)", (t,))
    try: c.execute("SELECT ratelab.submit('B', 60)"); print("quota: NOT enforced")
    except psycopg.Error as e: print("quota enforced:", e.sqlstate, str(e).splitlines()[0])

log, lock, stop = [], threading.Lock(), time.monotonic() + 25
def worker(n):
    with psycopg.connect(DSN, autocommit=True) as c:
        while time.monotonic() < stop:
            with c.transaction():
                row = c.execute("SELECT id, tenant_id FROM ratelab.claim(%s)", (f"w{n}",)).fetchone()
            if not row:
                if not c.execute("SELECT 1 FROM ratelab.jobs WHERE status <> 'done' LIMIT 1").fetchone(): return
                time.sleep(0.005); continue
            t0 = time.monotonic(); time.sleep(0.02)   # "work"
            c.execute("UPDATE ratelab.jobs SET status = 'done' WHERE id = %s", (row[0],))
            with lock: log.append((row[1], t0, time.monotonic()))
T0 = time.monotonic()
ths = [threading.Thread(target=worker, args=(i,)) for i in range(20)]
[t.start() for t in ths]; [t.join() for t in ths]
done = collections.defaultdict(list)
for t, s, e in log: done[t].append((s, e))
for t in sorted(done):
    ev = sorted([(s, 1) for s, _ in done[t]] + [(e, -1) for _, e in done[t]], key=lambda x: (x[0], x[1]))
    cur = peak = 0
    for _, d in ev: cur += d; peak = max(peak, cur)
    starts = sorted(s for s, _ in done[t])
    busiest = max(sum(1 for x in starts if w <= x < w + 1) for w in starts)
    print(f"tenant {t}: {len(starts):4} jobs, peak running {peak}, busiest 1s window {busiest} starts, "
          f"all done after {max(e for _, e in done[t]) - T0:.1f}s")
