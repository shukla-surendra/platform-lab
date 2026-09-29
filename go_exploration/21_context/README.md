# Lesson 21: Context (telling work to stop)

**You will learn:** how to cancel work, or give it a time limit.

```bash
go run ./21_context
```

---

## The problem

You order food on an app. It starts searching for a delivery driver.
Then **you cancel the order**. The search should **stop**, not keep running forever.

Or: you call a website, but it's very slow. You want to **give up after 2 seconds**.

In Go, both are done with a **context**.

## What is a context?

A `context.Context` is a **"stop signal"** that you pass to functions.
The function checks it now and then: *"Have I been told to stop?"*

```go
import "context"
```

By convention, `ctx` is **always the first parameter**:

```go
func doWork(ctx context.Context, name string) error
```

## 1. Starting point: context.Background()

```go
ctx := context.Background()   // an empty context, never cancelled
```

Every context "tree" starts with this, usually in `main`.

## 2. Cancel by hand: WithCancel

```go
ctx, cancel := context.WithCancel(context.Background())

go searchDriver(ctx)

time.Sleep(300 * time.Millisecond)
cancel()   // tell searchDriver to stop
```

## 3. Time limit: WithTimeout

```go
ctx, cancel := context.WithTimeout(context.Background(), 2*time.Second)
defer cancel()   // always call cancel when you're done (it frees resources)

err := slowTask(ctx)   // gets stopped after 2 seconds
```

## How does a function "listen" for stop?

It watches the `ctx.Done()` channel with `select` (from Lesson 19):

```go
func searchDriver(ctx context.Context) error {
	for {
		select {
		case <-ctx.Done():          // stop signal arrived
			return ctx.Err()        // says why: "context canceled" or "context deadline exceeded"
		default:
			fmt.Println("searching...")
			time.Sleep(100 * time.Millisecond)
		}
	}
}
```

## Most of the time, you just pass it along

Many standard library functions already accept a `ctx` and stop when it's cancelled.
For example, an HTTP request:

```go
ctx, cancel := context.WithTimeout(context.Background(), 2*time.Second)
defer cancel()

req, _ := http.NewRequestWithContext(ctx, "GET", "https://example.com", nil)
resp, err := http.DefaultClient.Do(req)   // gives up after 2 seconds
```

Database calls work the same way. Your job is usually just to **pass `ctx` down** to the next function.

## Rules to remember

1. `ctx` is the **first** parameter: `func Do(ctx context.Context, ...)`.
2. After `WithCancel` or `WithTimeout`, always `defer cancel()`.
3. Don't store a context inside a struct. Pass it to each function.

## Practice

1. Change the timeout in `main.go` from 500ms to 2s. What changes in the output?
2. Write `func countTo(ctx context.Context, n int)` that prints 1..n with a 100ms sleep each, but stops early if ctx is cancelled. Call it with a 350ms timeout.

---

🎉 **Part 3 done!** You can now write concurrent programs.

**Next:** [Lesson 22: Testing](../22_testing/): checking your code works automatically.
