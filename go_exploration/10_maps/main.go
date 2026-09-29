// Lesson 10: Maps
//
// Run it with:  go run ./10_maps
package main

import (
	"fmt"
	"slices"
	"strings"
)

func main() {
	// --- Make a map ---
	ages := map[string]int{
		"Asha": 25,
		"Ravi": 30,
	}
	fmt.Println("ages:", ages)

	// --- Add, change, read, delete ---
	ages["Meena"] = 28
	ages["Asha"] = 26
	fmt.Println("Ravi's age:", ages["Ravi"])
	delete(ages, "Ravi")
	fmt.Println("after delete:", ages, "| entries:", len(ages))

	// --- Missing key gives zero value ---
	fmt.Println("Nobody's age:", ages["Nobody"])

	// --- comma ok: does the key exist? ---
	age, ok := ages["Nobody"]
	fmt.Println("Nobody -> age:", age, "found:", ok)

	if age, ok := ages["Meena"]; ok {
		fmt.Println("Found Meena, age", age)
	}

	// --- Loop (order is random!) ---
	fmt.Println("--- loop (random order) ---")
	for name, age := range ages {
		fmt.Println(name, "is", age)
	}

	// --- Loop in sorted order ---
	fmt.Println("--- loop (sorted by name) ---")
	var names []string
	for name := range ages {
		names = append(names, name)
	}
	slices.Sort(names)
	for _, name := range names {
		fmt.Println(name, "is", ages[name])
	}

	// --- Counting words ---
	text := "go is fun and go is fast"
	counts := map[string]int{}
	for _, word := range strings.Fields(text) {
		counts[word]++
	}
	fmt.Println("word counts:", counts) // fmt prints maps in sorted key order

	// --- Map of string to string ---
	capitals := map[string]string{
		"India":  "New Delhi",
		"France": "Paris",
	}
	if capital, ok := capitals["Japan"]; ok {
		fmt.Println(capital)
	} else {
		fmt.Println("Japan is not in the map")
	}
}
