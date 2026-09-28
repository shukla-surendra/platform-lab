# 11 · HTTP server (standard library only)

```bash
go run ./11_http_server          # terminal 1
# terminal 2:
curl -s localhost:8080/healthz
curl -s -X POST localhost:8080/todos -d '{"title":"learn go"}'
curl -s localhost:8080/todos
curl -s localhost:8080/todos/1
curl -s -X DELETE -i localhost:8080/todos/1
# Ctrl-C in terminal 1 → graceful shutdown log

go test ./11_http_server
```

`net/http` is production-grade. Many Go services use no web framework at all.

## Routing (Go 1.22+ `ServeMux`)

```go
mux.HandleFunc("GET /todos/{id}", s.getTodo)
id := r.PathValue("id")
```

Method matching and path wildcards are built in. A wrong method returns
`405` automatically.

## Handler shape

```go
func(w http.ResponseWriter, r *http.Request)
```

Read from `r` (`r.Body`, `r.PathValue`, `r.URL.Query()`, `r.Context()`) and
write to `w`. Set headers **before** calling `WriteHeader`, and call
`WriteHeader` before writing the body. Every request runs in its own
goroutine, which is why `Store` holds a mutex.

## Middleware

This is just a function `func(http.Handler) http.Handler`. `logging` wraps
the mux and uses a `statusRecorder`, which **embeds**
`http.ResponseWriter` (chapter 04) and overrides only `WriteHeader`, so it
can log the status code.

## Production details already in `main.go`

| Detail | Why |
|---|---|
| `ReadHeaderTimeout` on `http.Server` | the zero-timeout default lets slow clients (Slowloris) tie up connections forever |
| `http.MaxBytesReader` | caps request body size |
| `DisallowUnknownFields` | typo'd JSON fields become a 400 instead of being silently ignored |
| `signal.NotifyContext` + `Shutdown` | on SIGTERM (what Kubernetes sends before killing a pod), stop accepting new connections and drain in-flight requests |
| `log/slog` JSON logs | structured logging in the stdlib (Go 1.21+) |
| `PORT` env var | 12-factor config |

## Testing (`main_test.go`)

- `httptest.NewServer(handler)`: a real server on a random port, for end-to-end tests.
- `httptest.NewRecorder()`: call `handler.ServeHTTP(rec, req)` directly, with no network.

## Ship it

```bash
CGO_ENABLED=0 GOOS=linux GOARCH=amd64 go build -o todo-api ./11_http_server
# → single static binary; runs in a `FROM scratch` or distroless image
```

## Try it

1. Add `PATCH /todos/{id}` that sets `done: true`.
2. Add a middleware that requires the header `X-API-Key: secret` on everything except `/healthz`.
