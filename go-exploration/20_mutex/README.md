# Lesson 20: Mutex (safely sharing a variable)

**You will learn:** what goes wrong when many goroutines change the same variable, and how to fix it.

```bash
go run ./20_mutex
go run -race ./20_mutex     # Go's race detector finds the bug for you
```

---

## The problem: a race condition

1000 goroutines each add 1 to `count`:

```go
count := 0
var wg sync.WaitGroup
for range 1000 {
	wg.Go(func() {
		count++
	})
}
wg.Wait()
fmt.Println(count)   // expect 1000... but you might get 947, 982, ...
```

**Why?** `count++` is really 3 small steps:

1. read `count` (say it's 5)
2. add 1 (now 6)
3. write 6 back

If two goroutines both read `5` at the same moment, both write `6`. **One +1 is lost.**

This is called a **race condition**. Two goroutines "race" to change the same thing.

## Real-life example

Two people edit the same Google Sheet cell at the **exact** same time, both starting from `5`.
Both type `6`. The answer should be `7`.

## The fix: a Mutex (a lock)

A **mutex** is like the lock on a **bathroom door**: only one person inside at a time.

```go
var mu sync.Mutex
count := 0

for range 1000 {
	wg.Go(func() {
		mu.Lock()     // lock the door (others wait outside)
		count++       // safe: only one goroutine is here
		mu.Unlock()   // unlock (next one can come in)
	})
}
```

Now the answer is **always 1000**.

## Tip: use defer for Unlock

If a function has many `return` points, it's easy to forget `Unlock`. Use `defer`:

```go
mu.Lock()
defer mu.Unlock()
// ... any code, any number of returns ...
```

## A clean pattern: put the lock inside a struct

```go
type SafeCounter struct {
	mu    sync.Mutex
	count int
}

func (c *SafeCounter) Increment() {
	c.mu.Lock()
	defer c.mu.Unlock()
	c.count++
}

func (c *SafeCounter) Value() int {
	c.mu.Lock()
	defer c.mu.Unlock()
	return c.count
}
```

Now anyone using `SafeCounter` **can't** forget to lock. The methods do it for them.
(Use a pointer receiver `*SafeCounter`. Copying a mutex breaks it.)

## The race detector: let Go find the bug

```bash
go run -race ./20_mutex
```

Go watches your program while it runs and prints `WARNING: DATA RACE` when it sees two goroutines touching the same variable unsafely.
**Use `-race` whenever you work with goroutines.** It works with `go test -race` too.

## Mutex or channel?

| Use a **Mutex** when… | Use a **Channel** when… |
|---|---|
| protecting a shared variable (counter, map, cache) | sending work or results **between** goroutines |

Both are fine. Pick the one that makes the code easier to read.

## Practice

1. Run `go run -race ./20_mutex` and read the warning. Which line does it point to?
2. Make a `SafeMap` struct with a `map[string]int` and a mutex. Add `Set(key, value)` and `Get(key)` methods.
3. Use 100 goroutines to count words in a slice of sentences, storing the counts in your `SafeMap`.

---

**Next:** [Lesson 21: Context](../21_context/): telling goroutines to stop.
