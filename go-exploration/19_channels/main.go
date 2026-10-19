// Lesson 19: Channels
//
// Run it with:  go run ./19_channels
package main

import (
	"fmt"
	"time"
)

func main() {
	// --- 1. Send and receive ---
	ch := make(chan string)
	go func() {
		ch <- "hello from a goroutine" // send
	}()
	msg := <-ch // receive (waits until something arrives)
	fmt.Println("1.", msg)

	// --- 2. Collect results from many workers ---
	results := make(chan int)
	numbers := []int{2, 3, 4}
	for _, n := range numbers {
		go func() {
			results <- n * n
		}()
	}
	fmt.Print("2. squares: ")
	for range len(numbers) {
		fmt.Print(<-results, " ") // order may change
	}
	fmt.Println()

	// --- 3. close + range ---
	counter := make(chan int)
	go func() {
		for i := 1; i <= 5; i++ {
			counter <- i
		}
		close(counter) // no more values
	}()
	total := 0
	for n := range counter { // stops when counter is closed
		total += n
	}
	fmt.Println("3. total of 1..5 =", total)

	// --- 4. Buffered channel: a mailbox with 3 slots ---
	mailbox := make(chan string, 3)
	mailbox <- "a"
	mailbox <- "b"
	mailbox <- "c" // no goroutine needed: there is room
	fmt.Println("4. mailbox has", len(mailbox), "letters:", <-mailbox, <-mailbox, <-mailbox)

	// --- 5. select with a timeout ---
	slow := make(chan string)
	go func() {
		time.Sleep(1 * time.Second) // a slow worker
		slow <- "slow result"
	}()

	select {
	case r := <-slow:
		fmt.Println("5. got", r)
	case <-time.After(300 * time.Millisecond):
		fmt.Println("5. timeout! the slow worker took too long")
	}

	// --- 6. select: whichever is first wins ---
	fast := make(chan string)
	go func() {
		time.Sleep(100 * time.Millisecond)
		fast <- "fast result"
	}()
	select {
	case r := <-fast:
		fmt.Println("6. got", r)
	case <-time.After(300 * time.Millisecond):
		fmt.Println("6. timeout")
	}
}
