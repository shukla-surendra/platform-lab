# Changelog

## 1.0.0 — unreleased (local only)

**Breaking. Renamed from `rust-sqlite-api`, and removes SQLite, OTLP ingest,
and every stateful feature the image had.** The service is now a fully
stateless public API-testing sample: health check, on-demand log generation,
and a set of httpbin-shaped test endpoints. Nothing else.

### Renamed

- Package, binary, image, and directory: `rust-sqlite-api` → `rust-api`. The
  old name described what the image used to be (SQLite-backed); nothing left
  in `1.0.0` touches SQLite, so the name was actively misleading.
- The old name's history is untouched — `surendrashukla29/rust-sqlite-api:0.2.0`
  stays on Docker Hub exactly where it was published. This is a *new* tag
  target, `surendrashukla29/rust-api`, not a Hub-side rename (Docker Hub has no
  such operation); nothing has been pushed there yet.
- Not renamed: `k8s/k8s_explorer/rust-sqlite-api-stack/` and everything in it. That
  chart already needs a rewrite for the `1.0.0` stateless design (noted below,
  unchanged from `0.4.0`) — renaming it now would be relabelling code that is
  about to be rebuilt anyway.

### Removed

- `db.rs`, `otlp.rs`, `writer.rs`, `query.rs`, `ingest.rs`, `retention.rs`,
  `model.rs`, `metrics.rs`, `state.rs`, `error.rs` — the entire OTLP-ingest /
  SQLite-storage / self-metrics layer, ~1,800 lines.
- OTLP endpoints (`/v1/logs`, `/v1/metrics`, `/v1/traces`), the query API
  (`/api/summary`, `/api/logs`, `/api/metrics`, `/api/traces*`), the notes CRUD
  demo (`/api/notes*`), and self-instrumentation (`GET /metrics`).
- `rusqlite`, `r2d2`, `r2d2_sqlite` dependencies. The Dockerfile no longer
  installs a C toolchain — everything left is pure Rust.
- The `/data` volume, `DATABASE_PATH`, `DB_POOL_SIZE`, `INGEST_*`,
  `RETENTION_*`, `PERSIST_TELEMETRY`. Nothing is written to disk anymore.
- `testdata/` (the OTLP sample payloads) and the root `data/` dev directory.

### Added

- **`POST /debug/random-logs`** — a random volume (20–300 unless `count` is
  given) of realistic log lines at a realistic level mix (mostly INFO/DEBUG,
  occasional WARN, rare ERROR), with randomised message content, correlated by
  an auto-generated or supplied `run_id`. Deliberately a different tool from
  `logstorm`: exact-count verification vs. traffic that looks like production.
- **`GET /api/endpoints`** — every route as JSON, generated from the same
  registry (`src/endpoints.rs`) as the landing page's table. The two are
  spliced from one source at first request, so they cannot list different
  routes — the alternative is exactly the kind of doc/code drift this project
  has hit before.
- `rand` (pure Rust, no C dependency) for `random-logs`.

### Kept

- Health check: `/healthz`, `/readyz`, `/version`.
- Log generation: `POST /debug/logstorm`, the heartbeat.
- The API-testing surface: `/`, `/api/test/*` (echo, status, delay, uuid,
  headers, ip, bytes, json) — added in `0.4.0`, unaffected by this cut.

### Fixed

- `random-logs` initially reported every generated line as `emitted`
  regardless of `RUST_LOG` — the exact bug `logstorm` was written to avoid,
  reintroduced by not carrying the fix into the second file. A `count=10` call
  under the default `info` level claimed 10 lines landed when only 7 could.
  Fixed by checking `tracing::enabled!()` once per level before counting or
  logging; `scripts/verify.sh` now asserts `requested == emitted + suppressed`
  for both endpoints so this can't regress silently again.

### Changed

- Image: **18.6 MB**, down from 23.5 MB.
- `AppState`/`Extension<Arc<...>>` replaced the connection-pool state with a
  single request counter, used only so the heartbeat has a number that moves.
- `helm dependency build` in `k8s/k8s_explorer/rust-sqlite-api-stack/` is now
  built around functionality this image no longer has (SQLite persistence,
  OTLP ingest, telemetry metrics/alerts, the Grafana dashboards that read
  them). **Not updated as part of this change** — flagged, not fixed.

## 0.4.0 — superseded by 1.0.0, never published

Turns the image into a usable API-testing target and makes its log output
provable, without changing anything about OTLP ingest or storage.

### Added

- **Heartbeat.** `HEARTBEAT_SECS` (default 30) emits an `alive` line at INFO
  with uptime, received/written/dropped, queue depth, write errors. INFO on
  purpose — at DEBUG it would be invisible under the default `RUST_LOG`, which
  is exactly when it matters. Without it a quiet healthy service and a wedged
  one produce identical output; with it, absence of the line is evidence.
- **`POST /debug/logstorm`** — `?count=N&tag=X&level=mixed&delay_ms=0`. Emits a
  known number of lines at known levels and returns `emitted` vs
  `suppressed_by_log_level` plus the LogQL to verify against a log store.
  Counts only what the subscriber actually emits, so `RUST_LOG` filtering
  cannot masquerade as pipeline loss.
- **`PERSIST_TELEMETRY=false`** — telemetry is parsed, queued, counted, then
  discarded instead of written. The discard happens at the *writer*, not the
  HTTP edge, so backpressure and every counter except `written` keep their
  normal meaning. New `telemetry_discarded_total{signal}`.
- **`GET /`** — self-contained landing page listing every endpoint, with a live
  try-it button. Compiled into the binary with `include_str!`; no CDN, no
  external font, no runtime file read.
- **`GET /version`** — name, version, os, arch.
- **`/api/test/*`** — stateless, httpbin-shaped: `echo` (GET/POST/PUT),
  `status/{code}`, `delay/{ms}` (30s cap), `uuid`, `headers`, `ip`,
  `bytes/{n}` (10 MB cap), `json?count=`. None touch SQLite.

### Changed

- `Dockerfile` now copies `static/`. `include_str!` is a **compile-time** read,
  so omitting it built fine on the host and failed only inside the container.

### Notes

22 routes, up from 13. Nothing removed — OTLP ingest, the query API, and notes
CRUD are untouched.

---

## 0.2.0 — published

[`surendrashukla29/rust-sqlite-api:0.2.0`](https://hub.docker.com/r/surendrashukla29/rust-sqlite-api),
multi-arch `linux/amd64` + `linux/arm64`, 6.7 MB pulled.

- OTLP/HTTP JSON ingest: `/v1/logs`, `/v1/metrics`, `/v1/traces`.
- Query API: `/api/summary`, `/api/logs`, `/api/metrics`, `/api/traces`,
  `/api/traces/{trace_id}` with in-memory span-tree assembly.
- Prometheus self-instrumentation at `/metrics`.
- Batching writer — one transaction per batch. **Measured 9.5×** over a
  transaction per row (14,914 → 142,059 spans/sec durable), not the folklore
  100–1000×, because WAL with `synchronous=NORMAL` already removed the
  per-commit fsync.
- Bounded ingest queue with `try_send`: overload degrades into counted, visible
  drops rather than unbounded memory growth.
- `UNIQUE(trace_id, span_id)` makes exporter re-delivery idempotent;
  `telemetry_written_total` counts rows actually inserted, not attempted.
- Time-based retention in chunks, with `auto_vacuum=INCREMENTAL`.
- Graceful SIGTERM: the writer flushes its partial batch before exit.

### Fixed during development

- `journal_mode=WAL` set once on a bootstrap connection rather than in the pool
  init hook — SQLite returns `SQLITE_BUSY` for that statement immediately,
  without consulting the busy handler, so every cold start logged
  `database is locked`.
- `telemetry_written_total` counted attempted inserts, overstating by exactly
  the dedupe rate — the number you would consult that metric to find.
