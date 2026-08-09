# rust-sqlite-api

An **OTLP-compatible telemetry collector** — logs, metrics, and traces — whose
entire backing store is a SQLite file on a volume inside the container. No
database server, no second container, no network hop. One static binary with
SQLite compiled into it.

**Published:** [`surendrashukla29/rust-sqlite-api:0.2.0`](https://hub.docker.com/r/surendrashukla29/rust-sqlite-api)
— multi-arch (`linux/amd64` + `linux/arm64`), 6.7 MB compressed / 23.5 MB on disk,
statically linked against musl, runs as uid 10001.

```bash
docker run -d -p 8080:8080 -v api-data:/data surendrashukla29/rust-sqlite-api:0.2.0
```

Point any OpenTelemetry SDK or `otel-collector` exporter at it:

```
OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:8080
OTEL_EXPORTER_OTLP_PROTOCOL=http/json
```

**Kubernetes → [`k8s_explorer/rust-sqlite-api-stack/`](../../k8s_explorer/rust-sqlite-api-stack/)**
— a Helm chart deploying this image with its own Prometheus, Grafana, dashboards
and alerts. All k8s work for this image lives there, not here.

**Locally → [`deploy/compose/`](deploy/compose/)** — Prometheus + Grafana with the
same dashboards, for seeing the thing work without a cluster:

```bash
cd deploy/compose && docker compose up -d && open http://localhost:3000
```

The dashboards are mounted from the Helm chart, so there is one definition
rather than two that drift.

## The local loop

Develop natively, containerise only once it passes. `make verify` runs the same
25 assertions against either target, so "it works locally" and "it works in the
image" mean the same thing.

```bash
# terminal 1 — native, auto-restarts nothing, just Ctrl-C and rerun
make dev

# terminal 2 — iterate here
make verify          # 25 assertions; non-zero exit means don't build yet
make dev-reset       # wipe ./data and start cold

# once green:
make check           # fmt + clippy -D warnings + release build --locked
make run             # build the image and start it
make verify          # same assertions, now against the container
make stop
```

**Use `make dev`, not bare `cargo run`.** The default `DATABASE_PATH=/data/app.db`
is correct inside the image and unwritable on macOS, where the root filesystem is
read-only — `cargo run` fails with `Read-only file system (os error 30)`.
`make dev` points it at `./data/` (gitignored) and binds to loopback:

```bash
DATABASE_PATH=./data/app.db BIND_ADDR=127.0.0.1:8080 cargo run
```

**Use `make dev-release` before trusting any timing.** A debug build is roughly
an order of magnitude slower; benchmarking it will send you optimising something
that is not slow in the image.

Other targets: `make otlp` (send the sample payloads and print what came back),
`make smoke` (notes CRUD only), `make logs`, `make shell`, `make size`.

### Building for x86-64

`docker build` produces **host-arch, silently** — on an arm64 Mac `make run`
gives you an arm64 image with no warning, and you find out on the deployment
target. Be explicit:

```bash
make build-amd64     # buildx --platform linux/amd64 --load
make run-amd64       # separate container and volume from the arm64 one
make stop-amd64
```

Both build and run go through QEMU here (~2 min to build vs ~1 min native).
**Do not benchmark the emulated image** — it tells you the thing works, never
how it performs on real x86-64 hardware.

### Publishing

```bash
docker login -u surendrashukla29
make push-dry TAG=0.2.0            # every check + both arches built, no push
make push     TAG=0.2.0            # for real
make push     TAG=0.2.0 PUSH_ARGS=--latest
```

`scripts/publish.sh` gates the push, because publishing is one-way — once a tag
is pulled, changing it breaks whoever pinned it:

| Gate | Why |
|---|---|
| Tag is required, no default | A default tag is how you overwrite `:latest` by accident |
| Tag grammar checked | Catches pasting `repo:tag` into the tag argument |
| Docker Hub login checked **first** | Fails in a second rather than after a multi-minute multi-arch build |
| Version-like tag must match `Cargo.toml` | Otherwise the image's own OCI labels lie about what it is |
| Remote tag must not already exist | Overwriting silently changes what that tag means for everyone who pinned it — `--force` to override |
| `fmt` + `clippy -D warnings` + `build --locked` | |
| **Acceptance run against the actual built image** | Publishing an image whose own tests fail is the failure this script exists to prevent |
| Published manifest re-inspected | A push that "succeeds" with a single-arch manifest is a real and quiet failure |

## Ingest — OTLP/HTTP JSON

| Method | Path | Signal |
|---|---|---|
| `POST` | `/v1/logs` | `resourceLogs[].scopeLogs[].logRecords[]` |
| `POST` | `/v1/metrics` | `resourceMetrics[].scopeMetrics[].metrics[]` — gauge, sum, histogram |
| `POST` | `/v1/traces` | `resourceSpans[].scopeSpans[].spans[]` |

All three return `200` with an OTLP `partialSuccess` body. Shed records are
reported in `rejectedLogRecords` / `rejectedDataPoints` / `rejectedSpans` rather
than as a 4xx, because a 4xx makes a well-behaved exporter retry the whole
payload and duplicate what already landed.

Sample payloads are in `testdata/`; `testdata/send.sh` templates real timestamps
into them and posts all three.

Two OTLP/JSON encoding quirks this handles, both from the proto3 JSON mapping:
64-bit fields (`timeUnixNano`, `asInt`) arrive as **strings**, and
`traceId`/`spanId` are **lowercase hex** rather than the base64 that proto3
normally uses for `bytes`.

## Query

| Method | Path | Notes |
|---|---|---|
| `GET` | `/api/summary` | Row counts and known services. First call when nothing looks like it is arriving — separates "nothing sent" from "sent wrong". |
| `GET` | `/api/logs` | `?service= &severity= &trace_id= &q= &since= &until= &limit=` |
| `GET` | `/api/metrics` | `?name= &service= &kind= &since= &until= &limit=` |
| `GET` | `/api/traces` | `?service= &min_duration_ms= &since= &limit=` — lists by root span |
| `GET` | `/api/traces/{trace_id}` | Full span tree, nested, with `relative_start_ms` per span |
| `GET` | `/metrics` | **This service's own** Prometheus metrics (see below) |
| `GET` | `/healthz` `/readyz` | Liveness / readiness |

`since` and `until` are unix **nanoseconds**, matching OTLP.

```bash
# every log line belonging to one trace, across services
curl 'localhost:8080/api/logs?trace_id=5b8efff798038103d269b633813fc60c'

# traces slower than 50ms
curl 'localhost:8080/api/traces?min_duration_ms=50'

# the assembled waterfall
curl localhost:8080/api/traces/5b8efff798038103d269b633813fc60c
```

Attribute columns are stored as JSON text and inflated back into real objects on
the way out — you get `{"http.route": "/charge"}`, never `"{\"http.route\"...}"`.

## Self-instrumentation — `GET /metrics`

Prometheus text format, describing the **collector**, not the telemetry it was
handed. If the only metrics you export are the ones you were given, you cannot
tell a quiet system from a broken ingest path.

| Metric | Why you would look at it |
|---|---|
| `telemetry_received_total{signal}` | Accepted at the HTTP edge, before queueing |
| `telemetry_written_total{signal}` | Durably committed. Counts rows actually inserted, not attempted |
| `telemetry_dropped_total{signal}` | Shed because the queue was full — ingest outran the disk |
| `telemetry_deduped_total{signal}` | Re-deliveries caught by `UNIQUE(trace_id, span_id)`. A rising value means exporters are timing out |
| `telemetry_skipped_total{signal}` | Parsed but unstorable (exponential histogram, summary, span with no ID) |
| `telemetry_queue_depth` | Sustained non-zero is the early warning that precedes drops |
| `telemetry_batches_total` / `_batch_rows_total` | Divide for mean batch size — tells you whether batching is doing anything |
| `telemetry_write_seconds_total` | Rising toward wall-clock means the writer is the bottleneck |

## Configuration

| Variable | Default | Notes |
|---|---|---|
| `DATABASE_PATH` | `/data/app.db` | Must sit on the volume, or data dies with the container |
| `BIND_ADDR` | `0.0.0.0:8080` | |
| `DB_POOL_SIZE` | `8` | Readers run concurrently under WAL; writes serialise regardless |
| `INGEST_QUEUE_CAPACITY` | `10000` | Bounded on purpose — see §Backpressure |
| `INGEST_BATCH_MAX` | `500` | Rows per transaction |
| `INGEST_FLUSH_MS` | `250` | Latency floor for data becoming queryable |
| `RETENTION_HOURS` | `72` | Older rows deleted in chunks |
| `RETENTION_INTERVAL_SECS` | `600` | How often retention runs |
| `RUST_LOG` | `info` | e.g. `info,rust_sqlite_api::writer=debug` |

## Architecture

```
request path   HTTP → parse OTLP → flatten to rows → bounded queue     (no I/O)
write path     queue → batching writer → one transaction per batch     (one task)
read path      HTTP → spawn_blocking → pooled connection → JSON
```

Keeping those three apart is the entire design, and it exists because of one
property: **SQLite allows exactly one writer.** Telemetry ingest is the opposite
workload — many concurrent producers, all appending. Wiring them together
naively (an `INSERT` per request) means every insert pays its own commit and
they all serialise on the same lock anyway.

### Measured, not assumed

20k spans, arm64 laptop, zero drops, same binary, only `INGEST_BATCH_MAX` changed:

| `batch_max` | spans/sec durable |
|---|---|
| 1 — a transaction per row | 14,914 |
| 500 | **142,059** |

**9.5×.** Stated precisely because the folklore figure for this optimisation is
"100–1000×", and that is not what happens here. Benchmarking the database in
isolation (same pragmas) does show 23× at `synchronous=NORMAL` and 61× at
`FULL` — the gap between 23× and 9.5× is everything the service does *besides*
the insert: JSON parsing, the channel hop, one `spawn_blocking` per batch.

Two conclusions, the second being the useful one:

- WAL with `synchronous=NORMAL` already removed the per-commit fsync, which is
  where most of the folklore speedup came from. Batching on top of WAL is a real
  win but a smaller one.
- At 142k spans/sec durable, **SQLite is no longer the bottleneck** — raw inserts
  benchmark at 3.4M rows/sec, so commits are under 1% of wall time. The next
  optimisation worth making is in parsing, not the database.

Through Docker Desktop's VM the same load runs at 37k spans/sec durable; the
loss is the VM filesystem and port forwarding, not the design.

### Backpressure

The queue is bounded and ingest uses `try_send`, never `send`.

Awaiting a full queue would push backpressure up into the caller's exporter,
which sounds principled but stalls *their* request path — turning a telemetry
problem into an application outage. An unbounded queue is worse still: it does
not remove backpressure, it converts it into unbounded memory growth and an OOM
kill at the worst possible moment.

So overload degrades into counted, visible drops. Telemetry is lossy by
contract; that is the trade every real collector makes.

### Retention

Without it, a telemetry store is a disk-full incident on a timer. Rows past
`RETENTION_HOURS` are deleted **in chunks of 5,000** — one `DELETE` covering a
day of telemetry would hold the single write lock for its whole duration, during
which ingest stalls and the queue drains into drops. Deleting also does not
shrink the file; `auto_vacuum=INCREMENTAL` plus `incremental_vacuum` returns
pages without the full-rewrite stall of a plain `VACUUM`.

## Design decisions worth defending

**Why SQLite at all.** It removes an entire tier. The trade is absolute: the
database is the container's local disk, so this cannot scale past one replica
against one volume — two replicas on a shared volume corrupt writes. Not a bug
to fix; the boundary of the design. The honest answer to "how would you scale
this" is *you don't* — you move to ClickHouse or Postgres, or you shard by
tenant so each replica owns its own file.

**Why `spawn_blocking` around every query.** `rusqlite` is a synchronous C
library. Called directly from an async handler it parks a Tokio worker thread on
a filesystem lock; with the multi-thread runtime it takes only as many
concurrent slow queries as there are cores to stall the whole server. Every read
goes through `AppState::fetch` so the rule is enforced in one place rather than
remembered at eleven call sites.

**Why WAL is set once, not per connection.** `journal_mode` is a *database-level*
setting persisted in the file header; `busy_timeout`, `synchronous`, and
`foreign_keys` are *per-connection* and reset on every new handle. Setting WAL in
the pool's init hook makes all 8 connections race for an exclusive lock on a
fresh database — and SQLite returns `SQLITE_BUSY` for that statement
*immediately*, without consulting the busy handler, so `busy_timeout` does not
save you. The first version did exactly that and logged `database is locked` on
every cold start.

**Why `UNIQUE(trace_id, span_id)`.** OTLP exporters retry on timeout. Without it
a flaky network silently duplicates spans, corrupting every duration and count
derived from them. `ON CONFLICT DO NOTHING` makes re-delivery idempotent — and
`telemetry_written_total` counts rows *actually inserted*, because counting
attempts would overstate by exactly the retry rate, which is the number you would
be trying to measure when you looked.

**Why filters build SQL dynamically.** The tidier `(?1 IS NULL OR col = ?1)`
trick is non-sargable: SQLite cannot prove the comparison holds before binding,
falls back to a full scan, and the indexes never get used. Parameters are still
bound, never interpolated.

**Why trace assembly is not a recursive CTE.** A recursive CTE walks one level
per iteration, re-probing the index each step. A trace is a small bounded
partition, so one indexed fetch plus an O(n) link-up in memory is simpler and
strictly less work. Recursive SQL earns its keep when the working set is too
large to hold — not here.

**Why `/healthz` ignores the database.** A liveness probe that fails on a locked
database gets the container killed and restarted, which unlocks nothing and drops
in-flight requests. Liveness answers *is the process wedged*; readiness answers
*should traffic come here*.

**Why the exec-form `ENTRYPOINT`.** Shell form puts `/bin/sh` at PID 1, and sh
does not forward signals — graceful shutdown would never fire and `docker stop`
would sit out its 10-second grace period. Shutdown order matters too: `serve`
returning drops the last `Sender`, which closes the channel, which tells the
writer to flush its partial batch. Awaiting that is what makes shutdown lossless.
Verified: `docker stop` returns in under a second with a loaded queue.

## Known gaps

Deliberately out of scope, listed so they read as choices rather than oversights:

- **No tests.** No `#[tokio::test]` integration tests against a `:memory:` pool. The largest gap.
- **No auth.** Anyone who can reach the port can write telemetry or read all of it.
- **gRPC OTLP not supported.** HTTP/JSON only — `OTEL_EXPORTER_OTLP_PROTOCOL=http/json` is required. Most SDKs default to gRPC.
- **`application/x-protobuf` not supported.** Some exporters default to it over HTTP.
- **Exponential histograms and summaries** are counted in `telemetry_skipped_total`, not stored.
- **No log full-text index.** `?q=` is `LIKE '%x%'` and cannot use an index; FTS5 is the real answer.
- **No downsampling or rollups.** Raw points only, so `/api/metrics` over a long window is expensive.
- **Not pushed.** No registry, no multi-arch manifest yet — `make push REGISTRY=...` is wired but unrun.
