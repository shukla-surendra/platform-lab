# ClickHouse

**Category:** database (column-oriented OLAP)

## What it is

A column-oriented OLAP (online analytical processing) database. Building started in 2009,
went into production in 2012, open-sourced in 2016 under Apache 2.0. Not an
observability-specific tool by itself — it's a general-purpose analytical database that
[SigNoz](../signoz/README.md) uses as its storage engine for metrics, logs, and traces
alike.

## Why it's fast for observability-style queries

**Column-oriented storage** means data is physically stored column-by-column rather than
row-by-row. An aggregate query — "p99 latency, grouped by service, over the last hour" —
only needs to read the specific columns involved (timestamp, service name, latency), not
every field of every row. Verified directly from ClickHouse's own docs: this is the
mechanism behind benchmark numbers like ~100M rows processed in 92ms. This access pattern
— filter/group/aggregate over huge volumes of time-stamped data — is exactly what
metrics, logs, and traces all need, which is why a single well-optimized OLAP engine can
serve all three signal types instead of needing purpose-built stores per signal.

## Scaling: sharding and replication

- **Sharding** — data is split horizontally across independent nodes for scale.
- **Replication** — via the `ReplicatedMergeTree` table engine: multi-master,
  asynchronous by default (any replica can take a write, data propagates to others),
  with quorum-write support (`insert_quorum`) for stronger consistency when needed.
- Replicas need to agree on who has the latest data and coordinate inserts across the
  cluster — that coordination role is handled by **Apache ZooKeeper or ClickHouse Keeper**,
  see [Zookeeper / ClickHouse Keeper](../zookeeper/README.md) for how that piece works and
  which one to actually run.

## Alternatives

- **Elasticsearch/OpenSearch** — full-text search focus rather than pure OLAP aggregate
  queries; see [Elasticsearch](../elasticsearch/README.md).
- **Prometheus's own TSDB** — purpose-built for metrics specifically, not a
  general-purpose analytical database usable for logs/traces too.
- **Other columnar OLAP engines** (Apache Druid, Apache Pinot) — similar category, less
  commonly paired with an observability platform the way ClickHouse is with SigNoz.

## Related

- [SigNoz](../signoz/README.md) — the observability platform this database backs.
- [Zookeeper / ClickHouse Keeper](../zookeeper/README.md) — the coordination layer a
  ClickHouse cluster needs for replication.
