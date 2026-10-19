// Lesson 02: Variables
//
// Run it with:  go run ./02_variables
package main

import "fmt"

// Constants never change.
const appName = "Go Learning"

func main() {
	fmt.Println("App:", appName)

	// 1. Full form: var name type = value
	var name string = "Asha"
	var age int = 25

	// 2. Go guesses the type
	var city = "Pune" // Go knows this is a string

	// 3. Short form (most common)
	price := 99.50    // float64
	isStudent := true // bool

	fmt.Println("Name:", name)
	fmt.Println("Age:", age)
	fmt.Println("City:", city)
	fmt.Println("Price:", price)
	fmt.Println("Student?", isStudent)

	// Changing a value: use = (not :=)
	score := 10
	fmt.Println("Score before:", score)
	score = 20
	fmt.Println("Score after:", score)

	// Empty boxes get a zero value
	var count int
	var message string
	var done bool
	fmt.Println("Zero values:", count, message, done)
	fmt.Println("(the empty string prints as nothing)")

	// Make several variables in one line
	x, y := 5, 10
	fmt.Println("x =", x, "and y =", y)
}
