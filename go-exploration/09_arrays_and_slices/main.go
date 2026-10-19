// Lesson 09: Arrays and Slices
//
// Run it with:  go run ./09_arrays_and_slices
package main

import (
	"fmt"
	"slices"
)

func main() {
	// --- Make a slice ---
	fruits := []string{"apple", "banana", "mango"}
	fmt.Println("fruits:", fruits)
	fmt.Println("first:", fruits[0], "| last:", fruits[len(fruits)-1])
	fmt.Println("how many:", len(fruits))

	// --- Change an item ---
	fruits[1] = "kiwi"
	fmt.Println("after change:", fruits)

	// --- Add items (always save the result of append!) ---
	fruits = append(fruits, "grapes")
	fruits = append(fruits, "orange", "papaya") // add several at once
	fmt.Println("after append:", fruits)

	// --- Loop ---
	for index, fruit := range fruits {
		fmt.Println(index, fruit)
	}

	// --- Start empty and grow ---
	var names []string
	fmt.Println("empty list length:", len(names))
	names = append(names, "Asha")
	names = append(names, "Ravi")
	fmt.Println("names:", names)

	// --- Slicing (taking a part) ---
	nums := []int{10, 20, 30, 40, 50}
	fmt.Println("nums[1:3] =", nums[1:3])
	fmt.Println("nums[:2]  =", nums[:2])
	fmt.Println("nums[3:]  =", nums[3:])

	// --- Careful: a part shares memory with the original ---
	part := nums[0:2]
	part[0] = 999
	fmt.Println("after changing part[0], nums is:", nums) // nums changed too!

	// --- Total and average ---
	scores := []int{70, 85, 90, 65}
	total := 0
	for _, s := range scores {
		total += s
	}
	fmt.Printf("total %d, average %.1f\n", total, float64(total)/float64(len(scores)))

	// --- slices package ---
	values := []int{5, 2, 8, 1}
	slices.Sort(values)
	fmt.Println("sorted:", values)
	fmt.Println("contains 8?", slices.Contains(values, 8))
	fmt.Println("max:", slices.Max(values))

	// --- Array (fixed size) ---
	var days [3]string
	days[0] = "Mon"
	days[1] = "Tue"
	days[2] = "Wed"
	fmt.Println("array:", days, "size:", len(days))
}
