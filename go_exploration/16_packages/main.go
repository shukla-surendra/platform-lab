// Lesson 16: Packages and Modules
//
// Run it with:  go run ./16_packages
// (Run the FOLDER, so Go also sees helpers.go.)
package main

import (
	"fmt"

	// module name (from go.mod) + folder path
	"platformlab/go_exploration/16_packages/calc"
)

func main() {
	// printTitle lives in helpers.go. Same package, so no import needed.
	printTitle("Using the calc package")

	fmt.Println("calc.Add(2, 3) =", calc.Add(2, 3))
	fmt.Println("calc.Average(10, 20, 30) =", calc.Average([]float64{10, 20, 30}))
	fmt.Println("calc.Pi =", calc.Pi)

	// calc.secret()  // ERROR: secret starts with a small letter, so it's private to calc
	fmt.Println(calc.Describe())
}
