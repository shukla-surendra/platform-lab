# Lesson 19: Channels (passing messages between goroutines)

**You will learn:** how goroutines send results to each other safely.

```bash
go run ./19_channels
```

---

## The idea (real life)

A **channel** is a **pipe**. One goroutine puts a value in one end, another takes it out of the other end.

```
  goroutine A  ──►  [ channel ]  ──►  goroutine B
   (sender)                            (receiver)
```

Go's motto: *"Don't share memory. **Send messages** instead."*

## Making and using a channel

```go
ch := make(chan string)    // a pipe that carries strings

go func() {
	ch <- "hello"          // SEND: put "hello" into the pipe
}()

msg := <-ch                // RECEIVE: take a value out of the pipe
fmt.Println(msg)           // hello
```

The arrow `<-` shows which way the data goes:

| Code | Meaning |
|---|---|
| `ch <- value` | send value **into** the channel |
| `value := <-ch` | take a value **out of** the channel |

## Channels wait for each other

- **Receiving** waits until someone sends.
- **Sending** waits until someone receives.

That's why we didn't need a WaitGroup above: `<-ch` **waits** for the goroutine to send.

## Collecting results from many goroutines

A very common pattern: start many workers, and they send their results back on one channel.

```go
results := make(chan int)

for _, n := range []int{2, 3, 4} {
	go func() {
		results <- n * n   // each worker sends its answer
	}()
}

for range 3 {              // we know 3 answers are coming
	fmt.Println(<-results)
}
```

## Closing a channel + range

When the sender is done, it can **close** the channel. This means *"no more values are coming"*.
Then the receiver can use `range` to read **until the channel is closed**:

```go
ch := make(chan int)

go func() {
	for i := 1; i <= 3; i++ {
		ch <- i
	}
	close(ch)              // "I'm done sending"
}()

for n := range ch {        // stops by itself when ch is closed
	fmt.Println(n)
}
```

**Rules:**
- Only the **sender** closes a channel.
- Don't send to a closed channel. That's a crash.

## Buffered channels: a pipe with some storage

```go
ch := make(chan string, 3)   // can hold 3 values without waiting
ch <- "a"
ch <- "b"
ch <- "c"                    // still no wait
// ch <- "d"                 // this one WOULD wait: the buffer is full
```

Think of it as a **mailbox with 3 slots**. The sender only waits when the mailbox is full.

## select: wait on several channels at once

`select` is like `switch`, but for channels. It runs whichever channel is ready **first**:

```go
select {
case msg := <-fastChannel:
	fmt.Println("got", msg)
case <-time.After(2 * time.Second):
	fmt.Println("timeout! gave up after 2 seconds")
}
```

`time.After(2 * time.Second)` is a channel that gets a value after 2 seconds.
So this code means: *"Wait for a message, but **not more than 2 seconds**."*

## Summary

| Code | Meaning |
|---|---|
| `make(chan T)` | new channel (sender and receiver wait for each other) |
| `make(chan T, 5)` | channel with 5 storage slots |
| `ch <- v` | send |
| `v := <-ch` | receive |
| `close(ch)` | no more values (only the sender does this) |
| `for v := range ch` | receive until closed |
| `select { case ... }` | wait for whichever channel is ready first |

## Practice

1. Start 5 goroutines that each send `"done from worker N"` into one channel. Receive and print all 5.
2. Write a goroutine that sends the numbers 1 to 10 and then closes the channel. In `main`, `range` over it and add them up.
3. Use `select` with `time.After(500 * time.Millisecond)` to time out a worker that sleeps for 1 second.

---

**Next:** [Lesson 20: Mutex](../20_mutex/): safely sharing a variable.
