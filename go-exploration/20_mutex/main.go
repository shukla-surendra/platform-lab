// Lesson 20: Mutex
//
// Run it with:  go run ./20_mutex
// Find the bug: go run -race ./20_mutex
package main

import (
	"fmt"
	"sync"
)

// SafeCounter keeps its lock inside, so users can't forget to lock.
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

func main() {
	var wg sync.WaitGroup

	// --- 1. BROKEN: race condition ---
	count := 0
	for range 1000 {
		wg.Go(func() {
			count++ // many goroutines change count at the same time: BUG
		})
	}
	wg.Wait()
	fmt.Println("1. Without a lock: ", count, "(should be 1000, may be less)")

	// --- 2. FIXED with a mutex ---
	var mu sync.Mutex
	safeCount := 0
	for range 1000 {
		wg.Go(func() {
			mu.Lock()
			safeCount++
			mu.Unlock()
		})
	}
	wg.Wait()
	fmt.Println("2. With a mutex:   ", safeCount)

	// --- 3. Lock inside a struct (cleanest) ---
	counter := &SafeCounter{}
	for range 1000 {
		wg.Go(func() {
			counter.Increment()
		})
	}
	wg.Wait()
	fmt.Println("3. With SafeCounter:", counter.Value())
}
