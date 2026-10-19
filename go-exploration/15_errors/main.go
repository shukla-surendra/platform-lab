// Lesson 15: Errors
//
// Run it with:  go run ./15_errors
package main

import (
	"errors"
	"fmt"
	"strconv"
)

// A named error that callers can check for with errors.Is
var ErrNotFound = errors.New("not found")

// Returns an error when b is zero.
func divide(a, b float64) (float64, error) {
	if b == 0 {
		return 0, errors.New("cannot divide by zero")
	}
	return a / b, nil
}

// fmt.Errorf puts values into the message.
func checkAge(age int) error {
	if age < 0 {
		return fmt.Errorf("age %d is not valid", age)
	}
	return nil
}

// A tiny "database"
var users = map[string]int{"Asha": 25, "Ravi": 30}

func findUser(name string) (int, error) {
	age, ok := users[name]
	if !ok {
		return 0, ErrNotFound
	}
	return age, nil
}

// Adds context with %w, keeping the original error inside.
func loadProfile(name string) (string, error) {
	age, err := findUser(name)
	if err != nil {
		return "", fmt.Errorf("loading profile of %s: %w", name, err)
	}
	return fmt.Sprintf("%s is %d", name, age), nil
}

func main() {
	// --- Errors from the standard library ---
	for _, text := range []string{"42", "hello"} {
		n, err := strconv.Atoi(text)
		if err != nil {
			fmt.Println("Could not convert:", err)
			continue
		}
		fmt.Println("Converted:", n)
	}

	// --- Our own errors ---
	result, err := divide(10, 2)
	if err != nil {
		fmt.Println("Error:", err)
	} else {
		fmt.Println("10 / 2 =", result)
	}

	_, err = divide(10, 0)
	if err != nil {
		fmt.Println("Error:", err)
	}

	// --- Short form: if err := ...; err != nil ---
	if err := checkAge(-5); err != nil {
		fmt.Println("Error:", err)
	}

	// --- Wrapping and errors.Is ---
	for _, name := range []string{"Asha", "Meena"} {
		profile, err := loadProfile(name)
		if errors.Is(err, ErrNotFound) {
			fmt.Println("Error:", err)
			fmt.Println("  -> errors.Is found ErrNotFound inside. We could create the user now.")
			continue
		}
		fmt.Println("Profile:", profile)
	}
}
