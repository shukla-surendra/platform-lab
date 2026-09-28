// Chapter 02 -- functions: multiple returns, variadics, closures, defer.
//
//	go run ./02_functions
package main

import (
	"errors"
	"fmt"
	"strings"
)

// Divide returns two values -- the Go way to report failure without exceptions.
func Divide(a, b int) (int, error) {
	if b == 0 {
		return 0, errors.New("divide by zero")
	}
	return a / b, nil
}

// MinMax uses NAMED results: they're declared variables, and a bare
// `return` returns them. Handy for short functions, confusing in long ones.
func MinMax(xs ...int) (lo, hi int) { // xs is a variadic []int
	if len(xs) == 0 {
		return
	}
	lo, hi = xs[0], xs[0]
	for _, x := range xs[1:] {
		lo, hi = min(lo, x), max(hi, x) // min/max are builtins since 1.21
	}
	return
}

// Counter returns a closure that captures `n` -- each counter has its own n.
func Counter() func() int {
	n := 0
	return func() int {
		n++
		return n
	}
}

// Apply shows functions as first-class values.
func Apply(xs []string, fn func(string) string) []string {
	out := make([]string, 0, len(xs))
	for _, x := range xs {
		out = append(out, fn(x))
	}
	return out
}

// deferDemo: deferred calls run when the function returns, LIFO order.
// Arguments are evaluated when `defer` executes, not when the call runs.
func deferDemo() (result string) {
	var log []string
	defer func() { result = strings.Join(log, " ") }() // runs last, can edit named result
	for i := range 3 {
		defer func() { log = append(log, fmt.Sprint("defer", i)) }()
	}
	log = append(log, "body")
	return "ignored" // overwritten by the first deferred func
}

// safeDiv turns a panic into an error with recover -- recover only works inside a deferred func.
func safeDiv(a, b int) (q int, err error) {
	defer func() {
		if r := recover(); r != nil {
			err = fmt.Errorf("recovered: %v", r)
		}
	}()
	return a / b, nil // b == 0 panics with a runtime error
}

func main() {
	if q, err := Divide(10, 3); err == nil {
		fmt.Println("10/3 =", q)
	}
	if _, err := Divide(1, 0); err != nil {
		fmt.Println("error:", err)
	}

	lo, hi := MinMax(4, 9, -2, 7)
	nums := []int{5, 1, 8}
	lo2, hi2 := MinMax(nums...) // spread a slice into a variadic
	fmt.Println("minmax:", lo, hi, "|", lo2, hi2)

	c1, c2 := Counter(), Counter()
	c1()
	c1()
	fmt.Println("closures keep separate state:", c1(), c2())

	fmt.Println(Apply([]string{"go", "k8s"}, strings.ToUpper))
	fmt.Println(Apply([]string{"a", "b"}, func(s string) string { return s + s }))

	fmt.Println("defer order:", deferDemo())

	_, err := safeDiv(1, 0)
	fmt.Println("panic -> error:", err)
}
