```sql
 SELECT citus_add_node('worker1', 5432); --5432 internal docker port
 SELECT citus_add_node('worker2', 5432); --5432 internal docker port
 SELECT * FROM citus_get_active_worker_nodes();
```

```sql
-- Parent table, partitioned by created_at (monthly range partitions)
CREATE TABLE events (
    id              bigserial,
    tenant_id       bigint NOT NULL,   -- this will be our distribution column
    event_type      text NOT NULL,
    payload         jsonb,
    created_at      timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (id, tenant_id, created_at)   -- must include partition + distribution cols
) PARTITION BY RANGE (created_at);
```

```sql
-- Distribute by tenant_id — Citus will hash-shard it across workers
SELECT create_distributed_table('events', 'tenant_id');
```

```sql
CREATE TABLE events_2026_06 PARTITION OF events
    FOR VALUES FROM ('2026-06-01') TO ('2026-07-01');

CREATE TABLE events_2026_07 PARTITION OF events
    FOR VALUES FROM ('2026-07-01') TO ('2026-08-01');

CREATE TABLE events_2026_08 PARTITION OF events
    FOR VALUES FROM ('2026-08-01') TO ('2026-09-01');

CREATE TABLE events_2026_09 PARTITION OF events
    FOR VALUES FROM ('2026-09-01') TO ('2026-10-01');
```


```sql
INSERT INTO events (tenant_id, event_type, payload, created_at)
SELECT
    (random() * 100)::int,
    (ARRAY['click','view','purchase'])[floor(random()*3+1)],
    jsonb_build_object('key', 'value', 'n', g),
    now() - (random() * interval '90 days')
FROM generate_series(1, 100000) AS g;
```

see all table including regular and partioned

```sql

SELECT
    COALESCE(parent.relname, c.relname) AS main_table,
    CASE WHEN parent.relname IS NOT NULL THEN c.relname END AS partition_name,
    c.relkind AS kind   -- 'p' = partitioned parent, 'r' = regular/partition
FROM pg_class c
LEFT JOIN pg_inherits i ON i.inhrelid = c.oid
LEFT JOIN pg_class parent ON parent.oid = i.inhparent
WHERE c.relkind IN ('p', 'r')
  AND (c.relispartition OR c.relkind = 'p')
ORDER BY main_table, partition_name NULLS FIRST;

```