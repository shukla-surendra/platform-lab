// Lesson 05: if / else
//
// Run it with:  go run ./05_if_else
package main

import "fmt"

func main() {
	// --- Simple if / else ---
	raining := true
	if raining {
		fmt.Println("Take an umbrella")
	} else {
		fmt.Println("Wear sunglasses")
	}

	// --- else if: more than two choices ---
	marks := 72
	if marks >= 90 {
		fmt.Println("Grade A")
	} else if marks >= 70 {
		fmt.Println("Grade B")
	} else if marks >= 50 {
		fmt.Println("Grade C")
	} else {
		fmt.Println("Fail")
	}

	// --- AND (&&), OR (||), NOT (!) ---
	age := 20
	hasTicket := true
	if age >= 18 && hasTicket {
		fmt.Println("You can enter the movie")
	}

	isWeekend := false
	isHoliday := true
	if isWeekend || isHoliday {
		fmt.Println("No office today!")
	}

	if !raining {
		fmt.Println("It is not raining")
	} else {
		fmt.Println("It is raining")
	}

	// --- Even or odd ---
	num := 7
	if num%2 == 0 {
		fmt.Println(num, "is even")
	} else {
		fmt.Println(num, "is odd")
	}

	// --- Short variable inside if ---
	if length := len("hello"); length > 3 {
		fmt.Println("Long word, length is", length)
	}
	// fmt.Println(length)  // ERROR: length does not exist out here
}
