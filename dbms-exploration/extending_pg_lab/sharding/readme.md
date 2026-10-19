Citus extends PostgreSQL to distribute tables across PostgreSQL worker nodes.

```
docker compose up -d
```

```
docker exec -it citus-coordinator \
  psql -U postgres -d shard_lab
```


```
$ docker exec -it citus-coordinator \
  psql -U postgres -d shard_lab
psql (18.4 (Debian 18.4-1.pgdg13+1))
Type "help" for help.

shard_lab=# SELECT version();
                                                      version
--------------------------------------------------------------------------------------------------------------------
 PostgreSQL 18.4 (Debian 18.4-1.pgdg13+1) on x86_64-pc-linux-gnu, compiled by gcc (Debian 14.2.0-19) 14.2.0, 64-bit
(1 row)

shard_lab=# SELECT citus_version();
                                     citus_version
----------------------------------------------------------------------------------------
 Citus 14.2.0 on x86_64-pc-linux-gnu, compiled by gcc (Debian 14.2.0-19) 14.2.0, 64-bit
(1 row)
```

```
$ docker exec -it citus-coordinator \
  getent hosts worker1
172.19.0.4      worker1

$ docker exec -it citus-coordinator \
  getent hosts worker1
172.19.0.4      worker1

$ docker exec -it citus-coordinator \
  getent hosts worker2
172.19.0.3      worker2

$ docker exec citus-worker1 \
  psql -U postgres -d shard_lab \
  -c "SHOW hba_file;"
                 hba_file
-------------------------------------------
 /var/lib/postgresql/18/docker/pg_hba.conf
(1 row)

$ docker exec citus-worker2 \
  psql -U postgres -d shard_lab \
  -c "SHOW hba_file;"
                 hba_file
-------------------------------------------
 /var/lib/postgresql/18/docker/pg_hba.conf
(1 row)
```

```
$ docker exec citus-worker1 sh -c \
"echo 'host all all 0.0.0.0/0 trust' >> /var/lib/postgresql/18/docker/pg_hba.conf"

$ docker exec citus-worker2 sh -c \
"echo 'host all all 0.0.0.0/0 trust' >> /var/lib/postgresql/18/docker/pg_hba.conf"
```

```
$ docker exec -it citus-coordinator \
  psql -U postgres -d shard_lab
psql (18.4 (Debian 18.4-1.pgdg13+1))
Type "help" for help.

shard_lab=# SELECT citus_add_node('worker1', 5432);
 citus_add_node
----------------
              1
(1 row)

shard_lab=# SELECT citus_add_node('worker2', 5432);
 citus_add_node
----------------
              2
(1 row)

shard_lab=# SELECT citus_add_node('worker2', 5432);
 citus_add_node
----------------
              2
(1 row)
```



```sql
CREATE TABLE orders (
    id BIGINT,
    customer_id BIGINT,
    order_date DATE,
    amount NUMERIC(12,2)
);
```
Tell citus to distrubute this table

```sql
SELECT create_distributed_table(
    'orders',
    'customer_id'
);
```

```sql
INSERT INTO orders VALUES
(1, 101, '2026-01-01', 500),
(2, 202, '2026-01-02', 600),
(3, 303, '2026-01-03', 700),
(4, 404, '2026-01-04', 800);

```
Check which record rexists in what 
```sql
WITH orders_with_shard AS MATERIALIZED (
    SELECT
        o.*,
        get_shard_id_for_distribution_column('orders', o.customer_id) AS shardid
    FROM orders o
)
SELECT
    ows.*,
    n.nodename,
    n.nodeport
FROM orders_with_shard ows
JOIN pg_dist_placement pl
    ON pl.shardid = ows.shardid
JOIN pg_dist_node n
    ON n.groupid = pl.groupid
   AND n.noderole = 'primary'
ORDER BY ows.id;
```


```
Intestingly

Now you can combine sharding + partitioning.

```
                       Citus
                         │
              Distributed orders
                         │
             distribution key
                = customer_id
                         │
             ┌───────────┴───────────┐
             ↓                       ↓
         Worker 1                Worker 2
             │                       │
        PostgreSQL              PostgreSQL
             │                       │
       ┌─────┴─────┐           ┌─────┴─────┐
       ↓           ↓           ↓           ↓
    2025          2026       2025          2026
  partition     partition   partition     partition
```


Sharding distributes data across machines; partitioning organizes data within a database/shard.

