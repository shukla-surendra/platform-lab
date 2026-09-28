# 09 · Shared state (`sync`) and `context`

```bash
go run -race ./09_sync_context
go test -race ./09_sync_context
```

Channels are for passing ownership. When several goroutines really do share
one piece of data, protect it.

## `sync` toolbox

| Tool | Use |
|---|---|
| `sync.Mutex` | exclusive lock. `mu.Lock(); defer mu.Unlock()` |
| `sync.RWMutex` | many concurrent readers **or** one writer |
| `sync/atomic` (`atomic.Int64`, …) | lock-free counters and flags |
| `sync.Once` | run an init exactly once, however many goroutines call it |
| `sync.WaitGroup` | wait for N goroutines (chapter 08) |

Rules:

- **Never copy** a struct that contains a mutex after first use. Pass `*Cache`. `go vet` catches this.
- Keep the lock next to the data it guards (same struct), and keep critical sections short.
- **Always test concurrent code with `-race`.** The race detector finds unsynchronised access at runtime.

## `context.Context`

Nearly every blocking API in Go takes a `ctx` as its **first parameter**:
HTTP handlers, database drivers, the Kubernetes client-go, and the gRPC and
AWS/Azure SDKs. A context carries three things:

1. **Cancellation.** `ctx.Done()` is a channel that closes when the work should stop.
2. **Deadline.** `context.WithTimeout(ctx, 2*time.Second)`.
3. **Request-scoped values.** `context.WithValue` for request IDs and auth
   info. Don't use it for optional arguments.

```
Background ─▶ WithValue(req-id) ─▶ WithTimeout(200ms) ─▶ SlowQuery(ctx)
                                           │
                            cancel() or deadline → Done() closes → every child stops
```

Cancelling a parent cancels all of its children. That's how an HTTP server
stops all the database work for a request when the client disconnects.

Rules:

- `ctx, cancel := context.WithTimeout(...)` → **always** `defer cancel()`.
- In blocking code, `select` on `ctx.Done()` and return `ctx.Err()`, wrapped.
- Check what happened with `errors.Is(err, context.DeadlineExceeded)` or `context.Canceled`.
- Don't store a context in a struct. Pass it explicitly.

`FirstSuccess` in `main.go` combines everything: run replicas in parallel,
take the first success, and let the deferred `cancel()` stop the losers.
(`golang.org/x/sync/errgroup` packages up this kind of pattern.)

## Try it

1. Remove the `RLock`/`RUnlock` from `Get` and run `go test -race`.
2. Give `handle` a 30ms timeout. Which branch wins?
