// Lesson 08: Functions
//
// Run it with:  go run ./08_functions
package main

import "fmt"

// 1. No input, no output
func sayHello() {
	fmt.Println("Hello!")
}

// 2. With input
func greet(name string) {
	fmt.Println("Hello,", name)
}

func introduce(name string, age int) {
	fmt.Printf("%s is %d years old\n", name, age)
}

// 3. With input and output
func double(n int) int {
	return n * 2
}

func isAdult(age int) bool {
	return age >= 18
}

// 4. Two outputs
func divide(a, b int) (int, int) {
	quotient := a / b
	remainder := a % b
	return quotient, remainder
}

// 6. defer runs at the end of the function
func work() {
	defer fmt.Println("3. Cleaning up (deferred)")
	fmt.Println("1. Starting work")
	fmt.Println("2. Doing work")
}

func main() {
	sayHello()
	sayHello()

	greet("Asha")
	greet("Ravi")
	introduce("Meena", 30)

	result := double(3)
	fmt.Println("double(3) =", result)
	fmt.Println("double(double(3)) =", double(double(3))) // output of one goes into the other

	fmt.Println("Is 16 an adult?", isAdult(16))
	fmt.Println("Is 21 an adult?", isAdult(21))

	q, r := divide(17, 5)
	fmt.Println("17 / 5 = quotient", q, "remainder", r)

	onlyQ, _ := divide(20, 3) // _ ignores the second value
	fmt.Println("20 / 3 quotient only:", onlyQ)

	work()
}
