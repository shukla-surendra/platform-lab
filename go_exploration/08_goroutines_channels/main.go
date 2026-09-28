// Chapter 08 -- goroutines, channels, select, worker pool, pipeline.
//
//	go run ./08_goroutines_channels
//	go run -race ./08_goroutines_channels   # always try the race detector
package main

import (
	"fmt"
	"sync"
	"time"
)

// --- 1. Goroutines + WaitGroup ----------------------------------------------

func fanOutHello() {
	var wg sync.WaitGroup
	for i := range 3 {
		wg.Go(func() { // Go 1.25+: Add(1) + go + Done() in one call
			fmt.Println("  hello from goroutine", i)
		})
	}
	wg.Wait() // without this, main may exit before goroutines run
}

// --- 2. Pipeline: generator -> square -> consumer ----------------------------

// gen returns a RECEIVE-ONLY channel and closes it when done.
func gen(nums ...int) <-chan int {
	out := make(chan int)
	go func() {
		defer close(out) // closing tells receivers "no more values"
		for _, n := range nums {
			out <- n // blocks until someone receives (unbuffered)
		}
	}()
	return out
}

func square(in <-chan int) <-chan int {
	out := make(chan int)
	go func() {
		defer close(out)
		for n := range in { // range over a channel ends when it's closed
			out <- n * n
		}
	}()
	return out
}

// --- 3. Worker pool -----------------------------------------------------------

type Result struct {
	Job    int
	Output int
	Worker int
}

// WorkerPool processes jobs with n concurrent workers and returns results
// in job order.
func WorkerPool(jobs []int, n int, work func(int) int) []Result {
	jobCh := make(chan int)
	resCh := make(chan Result, len(jobs)) // buffered: workers never block on send

	var wg sync.WaitGroup
	for w := range n {
		wg.Go(func() {
			for j := range jobCh {
				resCh <- Result{Job: j, Output: work(j), Worker: w}
			}
		})
	}

	for _, j := range jobs {
		jobCh <- j
	}
	close(jobCh) // workers' range loops end
	wg.Wait()
	close(resCh)

	results := make([]Result, len(jobs))
	for r := range resCh {
		results[r.Job] = r // jobs are 0..len-1 here, so index by job
	}
	return results
}

// --- 4. select: first-of-many, timeouts --------------------------------------

func fetchWithTimeout(delay, timeout time.Duration) string {
	ch := make(chan string, 1) // buffer 1 so the sender never leaks if we time out
	go func() {
		time.Sleep(delay)
		ch <- "response"
	}()
	select {
	case r := <-ch:
		return r
	case <-time.After(timeout):
		return "timeout"
	}
}

func main() {
	fmt.Println("1) goroutines + WaitGroup")
	fanOutHello()

	fmt.Println("2) pipeline")
	for v := range square(square(gen(1, 2, 3))) {
		fmt.Print("  ", v)
	}
	fmt.Println()

	fmt.Println("3) worker pool (4 workers, 8 jobs of 50ms each)")
	start := time.Now()
	res := WorkerPool([]int{0, 1, 2, 3, 4, 5, 6, 7}, 4, func(j int) int {
		time.Sleep(50 * time.Millisecond)
		return j * 10
	})
	for _, r := range res {
		fmt.Printf("  job %d -> %d (worker %d)\n", r.Job, r.Output, r.Worker)
	}
	fmt.Printf("  took ~%s (sequential would be 400ms)\n", time.Since(start).Round(10*time.Millisecond))

	fmt.Println("4) select with timeout")
	fmt.Println("  fast:", fetchWithTimeout(10*time.Millisecond, 100*time.Millisecond))
	fmt.Println("  slow:", fetchWithTimeout(200*time.Millisecond, 50*time.Millisecond))

	fmt.Println("5) buffered channel as a semaphore (max 2 at once)")
	sem := make(chan struct{}, 2)
	var wg sync.WaitGroup
	for i := range 5 {
		wg.Go(func() {
			sem <- struct{}{}        // acquire
			defer func() { <-sem }() // release
			fmt.Printf("  task %d running\n", i)
			time.Sleep(20 * time.Millisecond)
		})
	}
	wg.Wait()
}
