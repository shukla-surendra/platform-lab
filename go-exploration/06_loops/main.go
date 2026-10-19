// Lesson 06: Loops
//
// Run it with:  go run ./06_loops
package main

import "fmt"

func main() {
	// --- Shape 1: repeat N times ---
	fmt.Println("--- range 5 ---")
	for i := range 5 {
		fmt.Println("Hello", i)
	}

	// --- Shape 2: classic counter ---
	fmt.Println("--- 5 times table ---")
	for i := 1; i <= 5; i++ {
		fmt.Printf("5 x %d = %d\n", i, 5*i)
	}

	// --- Shape 3: while-style ---
	fmt.Println("--- while-style ---")
	money := 100
	for money > 0 {
		fmt.Println("Spending 30. Money left:", money)
		money -= 30
	}

	// --- Shape 4: forever + break ---
	fmt.Println("--- forever + break ---")
	count := 0
	for {
		count++
		fmt.Println("count is", count)
		if count == 3 {
			break
		}
	}

	// --- continue: skip even numbers ---
	fmt.Println("--- odd numbers only ---")
	for i := 1; i <= 10; i++ {
		if i%2 == 0 {
			continue
		}
		fmt.Print(i, " ")
	}
	fmt.Println()

	// --- range over text ---
	fmt.Println("--- letters of Go! ---")
	for index, letter := range "Go!" {
		fmt.Println(index, string(letter))
	}

	// --- Adding numbers ---
	total := 0
	for i := 1; i <= 100; i++ {
		total += i
	}
	fmt.Println("Sum of 1 to 100 =", total)
}
