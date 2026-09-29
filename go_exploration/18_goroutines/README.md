# Lesson 18: Goroutines (doing many things at once)

**You will learn:** how to run functions **at the same time**, and how to wait for them to finish.

```bash
go run ./18_goroutines
```

---

## The idea (real life)

You need to: boil water (5 min), toast bread (3 min), and fry an egg (4 min).

- **One by one:** 5 + 3 + 4 = **12 minutes**.
- **All at the same time:** about **5 minutes** (the longest task).

Go makes "at the same time" very easy.

## A goroutine = a function running in the background

Put the word `go` before a function call:

```go
go boilWater()    // starts it, and does NOT wait
go toastBread()
go fryEgg()
```

That's it. Each one is a **goroutine**: a very light worker. You can run thousands of them.

## Problem: main doesn't wait

```go
func main() {
	go fmt.Println("Hello from goroutine")
}
// prints NOTHING
```

Why? `main` started the goroutine and then **finished right away**.
When `main` ends, the **whole program ends**, and all goroutines stop with it.

## Solution: sync.WaitGroup (a counter that waits)

A WaitGroup is like a teacher on a school trip counting students:
*"I'll wait here until **everyone** is back on the bus."*

```go
import "sync"

var wg sync.WaitGroup

wg.Go(func() { boilWater() })   // start a worker, and the WaitGroup counts it
wg.Go(func() { toastBread() })
wg.Go(func() { fryEgg() })

wg.Wait()   // wait here until all 3 are done
fmt.Println("Breakfast ready!")
```

`func() { ... }` is a **function without a name**. We make it on the spot and hand it to `wg.Go`.

### The older way (you'll see it in lots of code)

Before Go 1.25, people wrote it like this. It does the same thing:

```go
wg.Add(1)             // "one more worker to wait for"
go func() {
	defer wg.Done()   // "I'm done", said when the function finishes
	boilWater()
}()
wg.Wait()
```

## Order is NOT fixed

```go
for i := range 3 {
	wg.Go(func() {
		fmt.Println("worker", i)
	})
}
wg.Wait()
```

This might print `worker 2, worker 0, worker 1`, and a different order next time.
Goroutines run **independently**. Don't expect any order.

## Speed test

`main.go` "cooks" breakfast both ways, so you can see the difference:

```
One by one:        took 1.2s
At the same time:  took 0.5s
```

(We use `time.Sleep` to pretend work is happening. 100 milliseconds = 1 "minute".)

## When is this useful?

- Calling **many websites or APIs** at once
- Processing **many files** at once
- A web server handling **many users** at once (Go does this for you automatically)

## Watch out

Two goroutines changing the **same variable** at the same time is a bug (a "race condition").
Lesson 20 shows how to fix that. For now, let each goroutine work on its own data.

## Practice

1. Change the cooking times in `main.go` and predict the total time before you run it.
2. Start 10 goroutines. Each one prints its number. Run it a few times and see the order change.
3. Remove `wg.Wait()`. What happens? Why?

---

**Next:** [Lesson 19: Channels](../19_channels/): how goroutines send data to each other.
