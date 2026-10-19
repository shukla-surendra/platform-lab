// Lesson 03: Printing
//
// Run it with:  go run ./03_printing
package main

import "fmt"

func main() {
	name := "Asha"
	age := 25
	price := 99.5
	happy := true

	// --- Println: values separated by spaces, new line at the end ---
	fmt.Println("Name:", name, "Age:", age)

	// --- Printf: a template with blanks ---
	fmt.Printf("My name is %s and I am %d years old.\n", name, age)
	fmt.Printf("Price: %f\n", price)
	fmt.Printf("Price with 2 decimals: %.2f\n", price)
	fmt.Printf("Happy? %t\n", happy)

	// %v works for any value
	fmt.Printf("Using %%v: %v, %v, %v, %v\n", name, age, price, happy)

	// %T shows the type
	fmt.Printf("Types: %T, %T, %T, %T\n", name, age, price, happy)

	// --- The common mistake ---
	sum := 60
	// (We keep the text in a variable here only so `go vet` doesn't complain
	// about this line. We're making the mistake on purpose.)
	wrongText := "Hello, Go!, %d"
	fmt.Println("Wrong way  ->", wrongText, sum) // Println does not fill %d
	fmt.Printf("Right way  -> Hello, Go!, %d\n", sum)

	// --- Sprintf: make the text, keep it in a variable ---
	message := fmt.Sprintf("%s scored %d points", "Ravi", 90)
	fmt.Println("Saved message:", message)
}
