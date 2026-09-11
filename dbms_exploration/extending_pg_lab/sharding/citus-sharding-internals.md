# Citus Sharding Internals — Design Interview Notes

## 1. The core idea

Citus is a **PostgreSQL extension**, not a separate database. It turns one logical table
into many physical PostgreSQL tables ("shards"), scattered across worker nodes, and
routes queries to the right shard(s) via the coordinator.

```
Logical table: orders
        │
        │  distribution column = customer_id
        ▼
 ┌───────────────────────────────────-───────┐
 │        hash(customer_id) space            │
 │   0 ───────────────────────────── 2^32-1  │
 └────────────────────────────────────-──────┘
        │            │            │
     shard 1       shard 2      shard 3   ...  (N shards, fixed at distribution time)
```

Key point for interviews: **sharding happens at the logical-table level, placement
happens at the physical-node level.** These are two separate concerns, and Citus keeps
them in two separate metadata layers. That separation is *why* rebalancing later is
possible without changing how the data is sharded.

---

## 2. How a shard and its ID get created

When you run:

```sql
SELECT create_distributed_table('orders', 'customer_id');
```

Citus does the following, in order:

1. **Picks a shard count.** Default is `citus.shard_count` (100 by default). This is
   fixed once the table is distributed — you do not add "more shards" later, you only
   move existing shards to more nodes (see §4).
2. **Divides the hash space.** `customer_id` is hashed (PostgreSQL's internal hash
   function) into a 32-bit integer space. That space is divided into `shard_count`
   contiguous ranges — one range per shard.
3. **Assigns a `shardid`.** Each range gets a globally unique `shardid`, allocated from
   a sequence. This is recorded in `pg_dist_shard`:

   ```
   pg_dist_shard: logicalrelid | shardid | shardminvalue | shardmaxvalue
   ```

4. **Creates the physical table.** For every shard, Citus creates an actual table on a
   worker, named `orders_<shardid>` (e.g. `orders_102008`), with the same schema/
   constraints as `orders`.
5. **Records placement.** Which worker holds which shard is written to
   `pg_dist_placement` (logical: shardid → group) and `pg_dist_node`
   (group → nodename/port). A row's shard is *never* stored on the coordinator itself
   — the coordinator only holds metadata + routing logic.

So a **shard** = a hash range + a physical table. A **shard ID** = the stable identifier
tying a hash range to wherever its physical table currently lives. The ID doesn't change
even if the shard is later *moved* to a different node — only its placement row changes.

### Why hashing, not simple modulo
Hash-range shards (like Citus, DynamoDB, Cassandra) tolerate adding nodes much better
than naive `hash(key) % num_nodes` schemes, because the *shard-to-key* mapping is fixed
independently of the *node count*. Only the shard→node assignment moves. This is the
detail interviewers usually want to hear.

---

## 3. Routing a query at execution time

For an INSERT/lookup with a distribution-column predicate, the coordinator:

1. Hashes the distribution column value → lands in exactly one shard's range.
2. Looks up `pg_dist_placement` → which node(s) hold that shard.
3. Rewrites the query to target `orders_<shardid>` on that node, and forwards it.

For a query *without* a predicate on the distribution column (e.g. `SELECT sum(amount)
FROM orders`), the coordinator fans the query out to **all** shards in parallel and
merges results — this is where Citus gets its parallelism, but also where cross-shard
joins/aggregations get expensive if the distribution key is chosen poorly.

---

## 4. Can you add nodes midway? Yes — this is the key design point

Because shard **count** is fixed but shard **placement** is just metadata, scaling out
is a two-step story:

### Step 1 — Add the node
```sql
SELECT citus_add_node('worker3', 5432);
```
This only registers the node in `pg_dist_node`. No data moves yet. Existing shards stay
exactly where they are — the new node holds zero shards until you rebalance.

### Step 2 — Rebalance shards onto it
```sql
SELECT rebalance_table_shards('orders');
```
Citus computes an assignment that evens out shard count (or shard size, depending on
strategy) across all nodes, including the new one, then **moves** individual shards:

- For each shard to move: create the table on the destination node, copy the data
  (logical replication under the hood in modern Citus), catch up, then atomically
  swap `pg_dist_placement` to point at the new node and drop the old copy.
- This is done shard-by-shard, so the cluster stays live — Citus 11+ does this with
  **near-zero downtime** using logical replication rather than blocking writes.
- The `shardid` and its hash range **never change** during a rebalance — only which
  node is the current owner.

```
Before:                          After adding worker3 + rebalance:

Worker1: shards 1,2,3,4          Worker1: shards 1,2
Worker2: shards 5,6,7,8          Worker2: shards 5,6
                                  Worker3: shards 3,4,7,8   ← moved here
```

### What does NOT happen automatically
- Rebalancing is **not automatic** — you trigger it explicitly (or schedule it).
- Shard **count** doesn't grow when you add a node. If you under-provisioned shard
  count originally (e.g. `shard_count = 4` and you now have 8 nodes), some nodes will
  simply get zero shards — you can't split an existing shard into two without
  re-distributing the table from scratch. This is why Citus docs recommend
  over-provisioning shard count relative to your *expected max* node count
  (e.g. shard_count = 32 even if you start with 2 nodes).

---

## 5. Metadata tables cheat-sheet (coordinator only)

| Table | Purpose |
|---|---|
| `pg_dist_shard` | shardid ↔ hash range ↔ logical table |
| `pg_dist_placement` | shardid ↔ which node group currently owns it |
| `pg_dist_node` | node group ↔ nodename/port/role (primary/secondary) |
| `citus_shards` | convenience view joining the above + live size info |

`citus_shards` is the fastest way to answer "where does my data live right now" without
hand-joining the raw catalogs (as in your earlier query).

---

## 6. Points worth raising in a design interview

- **Shard count is a capacity-planning decision made up front** — too few shards limits
  how far you can ever scale out horizontally; too many adds per-shard overhead.
- **Choice of distribution column drives everything** — it determines shard skew (hot
  keys → hot shards), and whether joins/aggregations can be co-located (same key on
  both tables → single-node joins) vs requiring cross-node shuffles.
- **Adding a node is cheap; rebalancing is the actual cost** — it's a data-movement
  operation bound by network/disk I/O, not a metadata change. Interviewers often want
  you to distinguish "control-plane" changes (add node, instant) from "data-plane"
  changes (shard move, takes time proportional to data size).
- **Compare to consistent hashing** — Citus's fixed hash-range shards are conceptually
  similar to consistent hashing's benefit (minimal data movement on topology change),
  but implemented as discrete static ranges + an explicit rebalancer, rather than a ring
  with virtual nodes. Good talking point if asked "why not consistent hashing directly."
- **Replication factor / HA** — `pg_dist_node` supports secondary/replica roles;
  `noderole = 'primary'` filters matter once you add read replicas, since a shard can
  then have multiple placement rows.
