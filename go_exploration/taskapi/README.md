# taskapi: a Go API server with Postgres, built like a real project

A small but production-shaped REST API for tasks. The domain is kept simple
on purpose so the **project structure and development workflow** are what
you notice: layout, layering, dependency wiring, migrations, testing
strategy, config, containerisation, and graceful shutdown.

The chapters in [`../`](../) teach the language. This project shows how
those pieces fit together in a codebase you'd ship.

## Quick start

```bash
cd go_exploration/taskapi
make help               # every dev command

make db-up              # Postgres 17 in Docker on localhost:55432
make run                # API on http://localhost:8081 (migrations run on start)
make smoke              # in another terminal: hits every endpoint

make test               # unit tests, no DB, ~1s
make test-integration   # + the same repository tests against real Postgres

make up                 # OR: run API + DB both in containers
make down               # stop (data kept); `make db-reset` also deletes the volume
```

```bash
curl -s -X POST localhost:8081/v1/tasks -d '{"title":"learn go","priority":1}'
curl -s 'localhost:8081/v1/tasks?status=todo&limit=10'
curl -s -X PATCH localhost:8081/v1/tasks/1 -d '{"status":"done"}'
curl -s -X DELETE -i localhost:8081/v1/tasks/1
```

## API

| Method | Path | Success | Errors |
|---|---|---|---|
| `GET` | `/healthz` | 200: process alive (k8s liveness) | |
| `GET` | `/readyz` | 200: DB reachable (k8s readiness) | 503 |
| `POST` | `/v1/tasks` | 201 + `Location` header | 400 bad JSON, 422 validation |
| `GET` | `/v1/tasks?status=&limit=&offset=` | 200 `{items,total,limit,offset}` | 400, 422 |
| `GET` | `/v1/tasks/{id}` | 200 | 400 bad id, 404 |
| `PATCH` | `/v1/tasks/{id}` | 200: only sent fields change | 400, 404, 422 |
| `DELETE` | `/v1/tasks/{id}` | 204 | 404 |

Every error has the same shape and carries the request ID that's in the logs:

```json
{"error":"validation failed","fields":{"priority":"must be between 1 and 5"},"request_id":"5abd61f11d86a408"}
```

---

## 1. Project layout

```
taskapi/
├── go.mod, go.sum             module path + pinned dependency versions (commit both)
├── cmd/
│   └── api/main.go            the executable: config → deps → server → shutdown
├── internal/                  importable ONLY from inside this module (compiler-enforced)
│   ├── config/                env vars → typed Config
│   ├── database/              pgx pool, retrying connect, embedded migrations
│   │   └── migrations/*.sql   goose migrations, compiled into the binary via //go:embed
│   ├── task/                  THE DOMAIN: types, validation, Service, Repository interface
│   │   ├── task.go            Task, inputs, errors, Repository interface
│   │   ├── service.go         business rules
│   │   ├── postgres.go        Repository implemented with SQL
│   │   └── memory.go          Repository implemented with a map (test fake)
│   └── httpapi/               HTTP transport: routes, handlers, JSON, middleware
├── scripts/                   smoke test, DB init
├── Dockerfile                 multi-stage → 21 MB distroless image
├── docker-compose.yml         local Postgres (+ API with `make up`)
└── Makefile                   the developer interface
```

Conventions worth knowing:

- **`cmd/<name>/`**: one folder per binary. If you later add a `cmd/worker/`,
  it reuses everything in `internal/`.
- **`internal/`**: Go refuses to compile an import of `internal/...` from
  outside this module. This is your private code. Only create a public
  `pkg/` for code you really intend others to import. Most services don't need one.
- **Package by domain, not by layer.** `task/` holds everything about tasks.
  There's no `models/`, `controllers/`, or `utils/`. When you add `users`,
  you add `internal/user/`.
- Package names are short, lowercase, and singular: `task.Service` and
  `task.ErrNotFound` read well at the call site.

## 2. Layers and the direction of dependencies

```
            ┌─────────────── cmd/api/main.go (wires everything) ───────────────┐
            ▼                              ▼                                   ▼
   httpapi.API  ──calls──▶  task.Service  ──calls──▶  task.Repository (interface)
   (HTTP, JSON,             (validation,                     ▲            ▲
    status codes)            defaults, rules)                │            │
                                                 PostgresRepository   MemoryRepository
                                                  (pgx + SQL)          (tests)
```

- `task` imports **nothing** from `httpapi` or `database`. The domain
  doesn't know it's being served over HTTP or stored in Postgres.
- `httpapi` declares its own small `TaskService` interface (the **consumer
  defines the interface**, from chapter 05), which `*task.Service` satisfies
  implicitly.
- Only `main.go` knows about every concrete type. This is **dependency
  injection with no framework**: plain constructor calls.

  ```go
  repo := task.NewPostgresRepository(pool)
  svc  := task.NewService(repo)
  api  := httpapi.New(svc, pool, log)
  ```

Why bother? Every layer can be tested alone, and swapping Postgres for
something else touches exactly one file.

## 3. Life of a request

`PATCH /v1/tasks/7  {"status":"done"}`:

1. **`requestID`** middleware: reuses `X-Request-ID` or generates one, then puts it on the `context` and the response header.
2. **`logRequests`**: starts a timer and wraps the ResponseWriter to capture the status.
3. **`recoverPanics`**: turns any panic below it into a JSON 500.
4. **ServeMux** matches `PATCH /v1/tasks/{id}` → `updateTask`.
5. Handler: `pathID` parses `7`, and `decodeJSON` enforces a 1 MiB limit, no unknown fields, and a single object → `task.UpdateInput{Status: &"done"}` (the other fields stay **nil** = "not sent").
6. `Service.Update` trims and validates, returning a `*ValidationError` → 422 if needed.
7. `PostgresRepository.Update` runs `SET status = COALESCE($4, status)`, so nil pointers keep the old values. `pgx.ErrNoRows` is translated to `task.ErrNotFound`.
8. Back in the handler, **`writeError`** is the only place that maps errors to status codes: `ValidationError`→422, `ErrNotFound`→404, anything else→500 (logged, never shown to the client).
9. `logRequests` writes one JSON log line with the route, status, duration, and request ID.

Throughout, `r.Context()` is passed down to pgx. If the client disconnects
or the server shuts down, the SQL query is cancelled.

## 4. Testing strategy

| Level | Where | What it proves | Needs |
|---|---|---|---|
| Unit: domain | `task/service_test.go` | validation, defaults, pagination clamps (fixed clock injected) | nothing |
| Unit: HTTP | `httpapi/server_test.go` | routes, status codes, error shapes, request IDs, panic safety, via `httptest.NewRecorder` | nothing |
| **Contract** | `task/repository_test.go` | *one* test suite that **both** `MemoryRepository` and `PostgresRepository` must pass | nothing / Postgres |
| Integration | `task/postgres_test.go` | runs the contract against real Postgres (`TRUNCATE` between subtests, separate `taskapi_test` DB) | `make test-integration` |
| End-to-end | `scripts/smoke.sh` | the real binary, over the network, with real Postgres | running server |

The **contract test** is the key idea. HTTP tests run against the in-memory
fake so they're fast, and the contract test guarantees the fake behaves
like Postgres (ordering, pagination, not-found errors, partial updates).
Without that guarantee, fakes drift and tests start lying.

Other techniques in use: table-driven tests, `t.Helper()`, `t.Run`
subtests, an injectable clock (`s.now`), injectable env (`config.Load(getenv)`),
and stubbing one interface method by embedding the interface
(`panickingService`).

## 5. Your development loop

```bash
make db-up                  # once per session
make run                    # Ctrl-C and rerun after changes (compiles in <1s)
make test                   # constantly, it's fast
make check                  # before committing: gofmt + vet + tests (what CI runs)
make test-integration       # before pushing / after touching SQL
```

### Walkthrough: adding a feature end to end

Say tasks need an **`assignee`**. The order you'd work in:

1. **Migration**: add `internal/database/migrations/00002_add_assignee.sql`:
   ```sql
   -- +goose Up
   ALTER TABLE tasks ADD COLUMN assignee TEXT NOT NULL DEFAULT '';
   -- +goose Down
   ALTER TABLE tasks DROP COLUMN assignee;
   ```
   Never edit a migration that has already run anywhere. Add a new one.
2. **Domain types** (`task/task.go`): add `Assignee string` with `json`/`db` tags
   to `Task` and `CreateInput`, and `Assignee *string` to `UpdateInput`.
3. **Contract test first**: add a case to `repository_test.go` for creating
   and updating the assignee. Run `make test`. It fails.
4. **Fake**: update `memory.go`. `make test` passes.
5. **SQL**: add the column to `columns`, the `INSERT`, and the `UPDATE ... COALESCE`.
   Run `make test-integration`. It passes against real Postgres.
6. **Rules**: any validation goes in `validate()`, with a service test.
7. **HTTP**: nothing to do. JSON decoding picks up the new field. Maybe add
   `?assignee=` filtering in `listTasks`.
8. `make check`, `make smoke`, commit.

The compiler helps here. `pgx.RowToStructByName` fails loudly if a column
and a struct field don't match, so step 5 can't be half-done silently.

## 6. Operational details (and why)

| Detail | Where | Why |
|---|---|---|
| Config from env only | `config/` | same image in every environment (12-factor) |
| Connect retries with backoff | `database.Connect` | the API often starts before Postgres in compose/k8s |
| Migrations embedded + run on start | `//go:embed`, goose | the binary is self-contained. At scale you'd run migrations as a separate job instead |
| Server timeouts | `main.go` `http.Server` | the zero-timeout defaults let slow clients hold connections forever |
| `BaseContext` = signal ctx | `main.go` | SIGTERM cancels in-flight DB queries too |
| Graceful shutdown | `srv.Shutdown` | k8s sends SIGTERM and then waits `terminationGracePeriodSeconds` |
| `/healthz` vs `/readyz` | `httpapi` | liveness restarts a dead pod. Readiness only takes it out of the Service while the DB is down |
| Structured JSON logs + request ID | `slog`, middleware | searchable in Loki/ELK, and a client-reported error ID leads straight to its log line |
| Internal errors hidden | `writeError` | never leak SQL or driver messages to clients |
| Static binary, distroless, nonroot | `Dockerfile` | 21 MB image, no shell, no package manager, smaller attack surface |
| Version stamped via `-ldflags -X` | `Makefile`, `Dockerfile` | the startup log says exactly which commit is running |

## 7. Dependencies (only two direct ones)

| Module | Why this one |
|---|---|
| `github.com/jackc/pgx/v5` | the standard Postgres driver + pool for Go. Speaks Postgres natively (faster, richer types than `database/sql`+`lib/pq`) |
| `github.com/pressly/goose/v3` | SQL-file migrations that can be embedded in the binary |

Everything else (routing, JSON, logging, HTTP server, testing) is the
standard library. No web framework, no ORM, and the SQL is right there in
`postgres.go`.

Common alternatives you'll see in other codebases: `chi` or `gin` (routers,
less necessary since Go 1.22), `sqlc` (generates type-safe Go from `.sql`
queries, a natural next step from here), `golang-migrate` (migrations),
`testcontainers-go` (Postgres started from inside `go test`).

## Next exercises

1. Add the `assignee` feature using the walkthrough above.
2. Add `?sort=priority` to the list endpoint (whitelist the column. Never interpolate user input into SQL).
3. Add a `/metrics` endpoint with `prometheus/client_golang` and a request-duration histogram middleware.
4. Replace the hand-written SQL with **sqlc** and compare.
5. Write a Helm chart or k8s manifests using `/healthz` and `/readyz` as probes.
