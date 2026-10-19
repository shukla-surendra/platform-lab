// Lesson 18: Goroutines
//
// Run it with:  go run ./18_goroutines
package main

import (
	"fmt"
	"sync"
	"time"
)

// Each "minute" of cooking is 100 milliseconds, so the demo is quick.
const minute = 100 * time.Millisecond

func cook(dish string, minutes int) {
	fmt.Printf("  started %s\n", dish)
	time.Sleep(time.Duration(minutes) * minute) // pretend to work
	fmt.Printf("  finished %s (%d min)\n", dish, minutes)
}

func main() {
	// --- One by one ---
	fmt.Println("One by one:")
	start := time.Now()
	cook("water", 5)
	cook("toast", 3)
	cook("egg", 4)
	fmt.Println("took", time.Since(start).Round(100*time.Millisecond))

	// --- At the same time ---
	fmt.Println("\nAt the same time:")
	start = time.Now()

	var wg sync.WaitGroup
	wg.Go(func() { cook("water", 5) })
	wg.Go(func() { cook("toast", 3) })
	wg.Go(func() { cook("egg", 4) })
	wg.Wait() // wait for all three

	fmt.Println("took", time.Since(start).Round(100*time.Millisecond))

	// --- Order is not fixed ---
	fmt.Println("\nFive workers (order changes every run):")
	for i := range 5 {
		wg.Go(func() {
			fmt.Println("  worker", i)
		})
	}
	wg.Wait()

	// --- The older Add/Done style (same result) ---
	fmt.Println("\nOlder Add/Done style:")
	wg.Add(1)
	go func() {
		defer wg.Done()
		fmt.Println("  hello from an old-style goroutine")
	}()
	wg.Wait()

	fmt.Println("\nBreakfast ready!")
}
