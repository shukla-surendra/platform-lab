// Package calc is a tiny toolbox of math helpers.
package calc

// Pi starts with a capital letter, so other packages can use it.
const Pi = 3.14159

// Add is public (capital A).
func Add(a, b int) int {
	return a + b
}

// Average is public. It returns 0 for an empty list.
func Average(nums []float64) float64 {
	if len(nums) == 0 {
		return 0
	}
	total := 0.0
	for _, n := range nums {
		total += n
	}
	return total / float64(len(nums))
}

// Describe is public, and it can call the private function below.
func Describe() string {
	return "calc says: " + secret()
}

// secret is private (small s). Only code inside package calc can call it.
func secret() string {
	return "I am only visible inside the calc package"
}
