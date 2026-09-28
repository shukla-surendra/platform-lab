# 08 · Goroutines and channels

```bash
go run ./08_goroutines_channels
go test -race ./08_goroutines_channels
```

## Goroutines

`go f()` runs `f` concurrently. A goroutine starts with a few KB of stack,
so running thousands is normal. The Go runtime schedules them onto OS
threads (the M:N scheduler, with `GOMAXPROCS` threads running Go code).

**`main` returning kills every goroutine.** You must wait for them:

```go
var wg sync.WaitGroup
wg.Go(func() { ... })   // Go 1.25+; older: wg.Add(1); go func(){ defer wg.Done(); ... }()
wg.Wait()
```

## Channels

> "Don't communicate by sharing memory; share memory by communicating."

| | Syntax | Behaviour |
|---|---|---|
| Unbuffered | `make(chan int)` | send blocks until a receiver takes it (a handoff) |
| Buffered | `make(chan int, 10)` | send blocks only when the buffer is full |
| Directional | `chan<- int` / `<-chan int` | send-only / receive-only in function signatures |
| Close | `close(ch)` | receivers drain what's left, then get the zero value with `ok == false` |

- `for v := range ch` loops until the channel is **closed**.
- Only the **sender** closes, and only once. Sending on a closed channel panics.
- A nil channel blocks forever, which is handy for switching off a `select` case.

## `select`

`select` waits on several channel operations and runs whichever is ready
first. Combine it with `time.After` for timeouts, or with `ctx.Done()`
(chapter 09) for cancellation. A `default:` case makes the select non-blocking.

## Patterns in `main.go`

1. **Fan-out with WaitGroup.**
2. **Pipeline:** `gen → square → square`. Each stage owns and closes its output channel.
3. **Worker pool:** N workers `range` over a jobs channel. After all jobs are sent, close it, wait, then close the results channel.
4. **Timeout with select.** The goroutine's channel is buffered (`cap 1`) so it can still send after we stop waiting and exit instead of **leaking**.
5. **Semaphore:** a buffered channel of `struct{}` limits concurrency.

## Goroutine leaks

A goroutine blocked forever on a send or receive is never garbage-collected.
Every goroutine you start needs a clear way to exit: the channel gets
closed, the context gets cancelled, or the send can't block.

## Try it

1. Make `fetchWithTimeout`'s channel unbuffered and think through what happens to the goroutine on timeout.
2. Run `go run -race` after removing the `sem` logic and sharing a counter `n++` between goroutines.
