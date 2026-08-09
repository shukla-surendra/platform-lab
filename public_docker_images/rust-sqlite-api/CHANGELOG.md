# Changelog

## 0.4.0 — unreleased (local + minikube only)

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
