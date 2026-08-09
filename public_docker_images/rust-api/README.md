# rust-api

A small, public, **stateless** HTTP server for testing clients against: a
health check, endpoints that generate log lines on demand, and a set of
httpbin-shaped test endpoints. No database, no file, no volume — every
response is derived entirely from the request that produced it.

**Renamed from `rust-sqlite-api`.** That name described an earlier version of
this image — an OTLP telemetry collector with an embedded SQLite database. That
version is retired; the image is `rust-api` now because that is what it
actually is. The old name's last published build,
[`surendrashukla29/rust-sqlite-api:0.2.0`](https://hub.docker.com/r/surendrashukla29/rust-sqlite-api),
stays where it is on Docker Hub — renaming a package does not move history —
but every new tag, starting with `1.0.0`, is pushed to `surendrashukla29/rust-api`.

Statically linked against musl, runs as uid 10001, 18.6 MB on disk.

```bash
docker run -d -p 8080:8080 rust-api:1.0.0
open http://localhost:8080          # landing page — every endpoint, live example
```

## What this is for

A target you point other things at:

- **A client library** you're testing — does it retry on 503, honour a delay,
  survive a huge response body?
- **An ingress rule or a proxy config** — does `/api/test/ip` show your proxy's
  IP or the real caller's? Is `X-Forwarded-For` actually being forwarded?
- **A log shipper or a dashboard** — does it lose lines under a burst? Can you
  prove it, with a number, rather than eyeballing a panel?
- **A load generator** — hit anything under `/api/test/` as hard as you like;
  nothing accumulates.

## Health check

| Method | Path | |
|---|---|---|
| `GET` | `/healthz` | Liveness — is the process answering HTTP at all |
| `GET` | `/readyz` | Readiness. Identical to `/healthz` here — there is no dependency to be unready for |
| `GET` | `/version` | name, version, os, arch. First call when a deploy "didn't take" |
| `GET` | `/api/endpoints` | Every route on this page, as JSON — generated from the same table as the landing page, so the two cannot disagree |

Both probes exist because orchestrators expect both paths, not because they
check different things. There is nothing downstream left to distinguish "up"
from "up but its dependency is unreachable" — that distinction only existed
when this image had a database.

## Log generation

Two endpoints, deliberately different tools:

| | `POST /debug/logstorm` | `POST /debug/random-logs` |
|---|---|---|
| Question it answers | Did every line I asked for arrive downstream? | What does my dashboard/parser/alert do with traffic that looks like production? |
| Volume | Exact — you specify `count` | Random by default (20–300); `count` overrides |
| Level split | Exact — you specify `level` | Realistic mix: mostly INFO/DEBUG, occasional WARN, rare ERROR |
| Message content | One fixed template per level | Random templates with randomised fields (user ids, latencies, status codes, paths) |
| Correlation | `tag` (you supply it, or a plain fallback) | `run_id` (auto-generated if you don't supply one) |

**`POST /debug/logstorm?count=N&tag=X&level=mixed&delay_ms=0`**

```json
{ "requested": 500, "emitted": 300, "suppressed_by_log_level": 200,
  "by_level": { "debug": 0, "error": 50, "info": 150, "warn": 100 },
  "tag": "X" }
```

**`POST /debug/random-logs?count=N&run_id=X&delay_ms=0`** — every parameter is
optional; calling it with none is the intended default experience:

```json
{ "requested": 81, "emitted": 81, "suppressed_by_log_level": 0,
  "by_level": { "debug": 28, "error": 0, "info": 45, "warn": 8 },
  "run_id": "run-62b6286b",
  "sample": [{ "level": "INFO", "message": "user 78372 authenticated successfully" }] }
```

Both cap `count` at 50,000 per request — uncapped, a stray large value fills
the *node's* disk with container logs, a failure that does not look like this
service's fault.

**Compare a log store against `emitted`, never `requested`, for either
endpoint.** `RUST_LOG` discards lines before they are written; counting those
as lost sends you chasing a pipeline problem that does not exist. Both
responses include a ready-to-run LogQL `verify` query using the correlation
field.

`random-logs` learned this the direct way: an early version reported
`requested` lines as emitted regardless of `RUST_LOG`, and a `count=10` call
under the default `info` level claimed 10 lines landed when only 7 (plus one
completion line) actually could. Fixed by checking `tracing::enabled!()` once
per level before counting or logging a line — the same fix `logstorm` already
needed, just not yet copied into the second file when it was written.

**Heartbeat** — an `alive` line every `HEARTBEAT_SECS` (default 30) at INFO,
carrying uptime and a request count. Without it, a quiet-but-healthy service
and a wedged one produce identical log output; an empty log window proves
nothing either way. With it, absence of the line is evidence. It is INFO on
purpose — at DEBUG it would be invisible under the default `RUST_LOG`, which
is exactly when it matters.

## API-testing endpoints

All stateless — no storage, no effect on any counter, safe to hammer.

| Method | Path | Notes |
|---|---|---|
| `GET`/`POST`/`PUT` | `/api/test/echo` | Echoes method, path, query, headers, body. Parses the body as JSON when it is JSON |
| `GET` | `/api/test/status/{code}` | Returns that status, with its canonical reason phrase |
| `GET` | `/api/test/delay/{ms}` | Sleeps, then responds. **Capped at 30s** |
| `GET` | `/api/test/uuid` | A v4 UUID |
| `GET` | `/api/test/headers` | Request headers as received |
| `GET` | `/api/test/ip` | Peer address + `X-Forwarded-For` / `X-Real-Ip` if present |
| `GET` | `/api/test/bytes/{n}` | Deterministic payload, **capped at 10 MB** |
| `GET` | `/api/test/json?count=` | Fixed-shape JSON document for deserialisation tests |

```bash
curl localhost:8080/api/test/status/503
curl localhost:8080/api/test/delay/1500
curl -X POST localhost:8080/api/test/echo -d '{"hello":"world"}'
```

Both caps exist because the uncapped versions fail in a way that does not look
like this service's fault: `/delay/600000` holds a connection for ten minutes
and reads as a hung server; `/bytes/1000000000` is a memory-exhaustion request.

`/api/test/ip` reports the peer, which behind a proxy *is* the proxy — that gap
is the point, and it is what makes `X-Forwarded-For` misconfiguration visible.

## Configuration

| Variable | Default | |
|---|---|---|
| `BIND_ADDR` | `0.0.0.0:8080` | |
| `HEARTBEAT_SECS` | `30` | Seconds between `alive` log lines |
| `RUST_LOG` | `info` | `info,tower_http=debug` for one line per request |

Logs are JSON on stdout — the format a log shipper expects, and the reason
nothing here writes to a file.

## The local loop

```bash
# terminal 1
make dev

# terminal 2
make verify          # 26 assertions; non-zero exit means don't build yet

# once green:
make check           # fmt + clippy -D warnings + release build --locked
make run              # build the image and start it
make verify           # same assertions, now against the container
make stop
```

`make dev-release` before trusting any timing you measure — a debug build is
roughly an order of magnitude slower and will make you "fix" a bottleneck that
does not exist in the image.

`make logstorm` fires a small burst against whatever is on `$PORT`, for a quick
manual check that log generation is wired up.

### Building for x86-64

`docker build` produces **host-arch, silently** — on an arm64 Mac `make run`
gives you an arm64 image with no warning, and you find out on the deployment
target.

```bash
make build-amd64     # buildx --platform linux/amd64 --load
make run-amd64
make stop-amd64
```

Both build and run go through QEMU here. **Do not benchmark the emulated
image** — it tells you the thing works, never how it performs on real x86-64
hardware.

### Publishing

```bash
docker login -u surendrashukla29
make push-dry TAG=1.0.0
make push     TAG=1.0.0
```

`scripts/publish.sh` gates the push, because publishing is one-way — once a
tag is pulled, changing it breaks whoever pinned it: login checked first (fails
in a second, not after a multi-arch build), version-shaped tags must match
`Cargo.toml`, an existing remote tag is refused without `--force`, and a full
acceptance run against the built image must pass before anything is pushed.

## What was removed, and why

This image used to be an OTLP telemetry collector — logs, metrics, and traces
ingested over HTTP and stored in an embedded SQLite database, with a batching
writer, retention, a query API, and Prometheus self-metrics. All of it is gone:
`db.rs`, `otlp.rs`, `writer.rs`, `query.rs`, `ingest.rs`, `retention.rs`,
`model.rs`, `metrics.rs`, `state.rs`, `error.rs`, the `rusqlite`/`r2d2`
dependencies, the `/data` volume, and the C toolchain the Dockerfile needed to
compile SQLite's bundled build. None of that was wrong for what it was — it is
just a different tool than "a sample API for public use" calls for, and keeping
it around would mean every consumer of this image inherits a database they
never asked for.

If you are looking for that version, it is `0.2.0` on Docker Hub. Its design
notes — the batching-writer measurement, the WAL/`SQLITE_BUSY` startup race,
the OTLP JSON encoding quirks — are preserved in [`CHANGELOG.md`](CHANGELOG.md)
rather than repeated here, since none of it applies to what this image is now.

## Known gaps

- **No auth, on any endpoint.** Anyone who can reach the port can generate
  load and log volume. Fine for a public test target; do not put anything
  behind it that assumes otherwise.
- **No rate limiting.** The `count`/`delay_ms`/`bytes` caps bound a single
  request; nothing bounds request *rate*.
- **No tests.** `scripts/verify.sh` is the acceptance check; there is no
  `#[tokio::test]` suite.
