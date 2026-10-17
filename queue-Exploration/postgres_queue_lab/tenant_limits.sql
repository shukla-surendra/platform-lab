-- Prototype: per-tenant fair claim with a concurrency cap, a token-bucket start rate and a backlog quota.
-- Self-contained in a scratch schema (ratelab) so it does not touch the job app. Tested by tenant_limits_test.py;
-- explained in ../postgres_queue_case_study.html section 7.

DROP SCHEMA IF EXISTS ratelab CASCADE;
CREATE SCHEMA ratelab;
CREATE TABLE ratelab.jobs (
  id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY, tenant_id text NOT NULL,
  status text NOT NULL DEFAULT 'queued', priority int NOT NULL DEFAULT 0, run_after timestamptz NOT NULL DEFAULT now(),
  attempts int NOT NULL DEFAULT 0, locked_by text, locked_until timestamptz);
CREATE INDEX jobs_tenant_ready   ON ratelab.jobs (tenant_id, priority DESC, run_after, id) WHERE status = 'queued';
CREATE INDEX jobs_tenant_running ON ratelab.jobs (tenant_id) WHERE status = 'running';
CREATE INDEX jobs_lease ON ratelab.jobs (locked_until) WHERE status = 'running';

CREATE TABLE ratelab.tenants (
  tenant_id      text PRIMARY KEY,
  max_running    int     NOT NULL DEFAULT 5,     -- concurrency cap
  rate_per_sec   numeric NOT NULL DEFAULT 10,    -- token bucket: job starts per second
  burst          numeric NOT NULL DEFAULT 10,    -- bucket size
  max_queued     int     NOT NULL DEFAULT 10000, -- backlog quota, checked at submit
  tokens         numeric NOT NULL DEFAULT 10,
  refilled_at    timestamptz NOT NULL DEFAULT now(),
  last_served_at timestamptz NOT NULL DEFAULT '-infinity');

CREATE FUNCTION ratelab.claim(p_worker text, p_lease int DEFAULT 30) RETURNS SETOF ratelab.jobs
LANGUAGE plpgsql AS $$
DECLARE
  t ratelab.tenants;
  j ratelab.jobs;
  avail numeric;
BEGIN
  -- 1. Expired leases first: already counted as running for their tenant, so no limit applies.
  RETURN QUERY UPDATE ratelab.jobs SET attempts = attempts + 1, locked_by = p_worker,
                      locked_until = now() + make_interval(secs => p_lease)
    WHERE id = (SELECT id FROM ratelab.jobs WHERE status = 'running' AND locked_until < now()
                FOR UPDATE SKIP LOCKED LIMIT 1) RETURNING *;
  IF FOUND THEN RETURN; END IF;

  -- 2. Least recently served tenant that has a due job and a token. Locking its row serialises claims
  --    for that tenant; other workers SKIP it and serve another tenant meanwhile.
  SELECT * INTO t FROM ratelab.tenants tn
  WHERE least(burst, tokens + extract(epoch FROM clock_timestamp() - refilled_at) * rate_per_sec) >= 1
    AND EXISTS (SELECT 1 FROM ratelab.jobs q WHERE q.tenant_id = tn.tenant_id AND q.status = 'queued' AND q.run_after <= now())
  ORDER BY last_served_at
  FOR UPDATE SKIP LOCKED LIMIT 1;
  IF NOT FOUND THEN RETURN; END IF;

  -- 3. Concurrency cap. This is a new statement, so it sees every claim committed before we got the lock;
  --    and nobody else can claim for this tenant until we commit. Finishing jobs only lower the count.
  IF (SELECT count(*) FROM ratelab.jobs WHERE tenant_id = t.tenant_id AND status = 'running') >= t.max_running THEN
    UPDATE ratelab.tenants SET last_served_at = clock_timestamp() WHERE tenant_id = t.tenant_id;  -- rotate past it
    RETURN;
  END IF;

  -- 4. Claim the tenant's next job, then spend a token.
  UPDATE ratelab.jobs SET status = 'running', attempts = attempts + 1, locked_by = p_worker,
         locked_until = now() + make_interval(secs => p_lease)
  WHERE id = (SELECT id FROM ratelab.jobs WHERE tenant_id = t.tenant_id AND status = 'queued' AND run_after <= now()
              ORDER BY priority DESC, run_after, id FOR UPDATE SKIP LOCKED LIMIT 1)
  RETURNING * INTO j;
  IF NOT FOUND THEN RETURN; END IF;
  avail := least(t.burst, t.tokens + extract(epoch FROM clock_timestamp() - t.refilled_at) * t.rate_per_sec);
  UPDATE ratelab.tenants SET tokens = avail - 1, refilled_at = clock_timestamp(), last_served_at = clock_timestamp()
  WHERE tenant_id = t.tenant_id;
  RETURN NEXT j;
END $$;

-- Submit with a backlog quota: lock the tenant row so two submits can't both squeeze under the limit.
CREATE FUNCTION ratelab.submit(p_tenant text, p_count int) RETURNS int LANGUAGE plpgsql AS $$
DECLARE lim int; queued int;
BEGIN
  SELECT max_queued INTO lim FROM ratelab.tenants WHERE tenant_id = p_tenant FOR UPDATE;
  IF NOT FOUND THEN RAISE EXCEPTION 'unknown tenant %', p_tenant; END IF;
  SELECT count(*) INTO queued FROM ratelab.jobs WHERE tenant_id = p_tenant AND status = 'queued';
  IF queued + p_count > lim THEN
    RAISE EXCEPTION 'tenant % over its queue quota (% queued, limit %)', p_tenant, queued, lim USING ERRCODE = 'P0429';
  END IF;
  INSERT INTO ratelab.jobs (tenant_id) SELECT p_tenant FROM generate_series(1, p_count);
  RETURN queued + p_count;
END $$;
