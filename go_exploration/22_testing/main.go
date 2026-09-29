// Lesson 22: Testing
//
// Run the program: go run ./22_testing
// Run the tests:   go test -v ./22_testing
//
// The functions here are tested in main_test.go.
package main

import (
	"errors"
	"fmt"
)

// Add returns a + b.
func Add(a, b int) int {
	return a + b
}

// Grade turns marks (0-100) into a grade.
func Grade(marks int) string {
	switch {
	case marks >= 90:
		return "A"
	case marks >= 70:
		return "B"
	case marks >= 50:
		return "C"
	default:
		return "Fail"
	}
}

// Discount returns the price after taking off percent %.
// percent must be between 0 and 100.
func Discount(price float64, percent float64) (float64, error) {
	if percent < 0 || percent > 100 {
		return 0, errors.New("percent must be between 0 and 100")
	}
	return price - price*percent/100, nil
}

func main() {
	fmt.Println("Add(2, 3) =", Add(2, 3))
	fmt.Println("Grade(75) =", Grade(75))

	price, err := Discount(200, 10)
	fmt.Println("Discount(200, 10%) =", price, err)

	_, err = Discount(200, 150)
	fmt.Println("Discount(200, 150%) error:", err)

	fmt.Println("\nNow run the tests:  go test -v ./22_testing")
}
