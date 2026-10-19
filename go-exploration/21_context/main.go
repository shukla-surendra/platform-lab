// Lesson 21: Context
//
// Run it with:  go run ./21_context
package main

import (
	"context"
	"fmt"
	"time"
)

// searchDriver keeps searching until ctx says stop.
func searchDriver(ctx context.Context) error {
	for i := 1; ; i++ {
		select {
		case <-ctx.Done():
			return ctx.Err() // why we stopped
		default:
			fmt.Println("   searching for a driver... try", i)
			time.Sleep(100 * time.Millisecond)
		}
	}
}

// slowTask takes 1 second, unless ctx stops it first.
func slowTask(ctx context.Context) error {
	select {
	case <-time.After(1 * time.Second):
		fmt.Println("   slow task finished")
		return nil
	case <-ctx.Done():
		return ctx.Err()
	}
}

func main() {
	// --- 1. Cancel by hand ---
	fmt.Println("1. Cancel by hand (after 350ms):")
	ctx, cancel := context.WithCancel(context.Background())
	go func() {
		time.Sleep(350 * time.Millisecond)
		fmt.Println("   user pressed cancel!")
		cancel()
	}()
	err := searchDriver(ctx)
	fmt.Println("   stopped because:", err)

	// --- 2. Time limit ---
	fmt.Println("\n2. Timeout of 500ms on a 1-second task:")
	ctx2, cancel2 := context.WithTimeout(context.Background(), 500*time.Millisecond)
	defer cancel2()
	if err := slowTask(ctx2); err != nil {
		fmt.Println("   stopped because:", err)
	}

	// --- 3. Enough time ---
	fmt.Println("\n3. Timeout of 2s on a 1-second task:")
	ctx3, cancel3 := context.WithTimeout(context.Background(), 2*time.Second)
	defer cancel3()
	if err := slowTask(ctx3); err != nil {
		fmt.Println("   stopped because:", err)
	}
}
