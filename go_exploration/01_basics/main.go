// Chapter 01 -- variables, types, constants, control flow.
//
//	go run ./01_basics
package main

import (
	"fmt"
	"math"
	"strings"
	"unicode/utf8"
)

// Typed and untyped constants. iota counts up from 0 inside a const block.
const Pi = 3.14159 // untyped: takes whatever numeric type the context needs

type Weekday int

const (
	Sunday  Weekday = iota // 0
	Monday                 // 1 -- the expression `Weekday = iota` repeats implicitly
	Tuesday                // 2
)

func main() {
	// --- Declaration forms ---------------------------------------------------
	var a int            // zero value: 0
	var b = "inferred"   // type inferred as string
	c := 42              // short declaration, only inside functions
	var x, y = 1.5, true // several at once

	fmt.Println("zero values:", a, fmt.Sprintf("%q", ""), 0.0, false, "nil-for-pointers/slices/maps")
	fmt.Println(b, c, x, y)

	// --- No implicit conversions --------------------------------------------
	var i int = 7
	var f float64 = float64(i) / 2 // i / 2 would be integer division = 3
	fmt.Printf("float64(7)/2 = %.1f, 7/2 = %d\n", f, i/2)

	// Integer overflow wraps silently.
	var small int8 = math.MaxInt8
	small++
	fmt.Println("int8 max + 1 =", small)

	// --- Strings are immutable byte slices; range yields runes -------------
	s := "héllo, 世界"
	fmt.Println("len (bytes):", len(s), "| runes:", utf8.RuneCountInString(s))
	for idx, r := range "hé" {
		fmt.Printf("  byte offset %d -> %q\n", idx, r)
	}
	fmt.Println(strings.ToUpper(s), strings.Contains(s, "世"), strings.Split("a,b,c", ","))

	// --- Control flow: if with init statement -------------------------------
	if n := len(s); n > 10 {
		fmt.Println("long string,", n, "bytes") // n is scoped to the if/else
	}

	// for is the ONLY loop keyword.
	sum := 0
	for i := 1; i <= 10; i++ { // classic
		sum += i
	}
	for sum > 50 { // while-style
		sum -= 10
	}
	for i := range 3 { // Go 1.22+: range over an int
		fmt.Print(i, " ")
	}
	fmt.Println("| sum:", sum)

	// switch: no fall-through by default, cases can be expressions.
	switch day := Monday; day {
	case Sunday:
		fmt.Println("weekend")
	case Monday, Tuesday:
		fmt.Println("weekday", int(day))
	}
	switch { // tagless switch = clean if/else-if chain
	case sum < 0:
		fmt.Println("negative")
	default:
		fmt.Println("non-negative")
	}

	// Labeled break out of nested loops.
outer:
	for i := range 3 {
		for j := range 3 {
			if i*j == 2 {
				fmt.Println("found i*j==2 at", i, j)
				break outer
			}
		}
	}

	fmt.Println(FizzBuzz(15))
}

// FizzBuzz returns the FizzBuzz word for n -- exported (capitalised) so tests can call it.
func FizzBuzz(n int) string {
	switch {
	case n%15 == 0:
		return "FizzBuzz"
	case n%3 == 0:
		return "Fizz"
	case n%5 == 0:
		return "Buzz"
	default:
		return fmt.Sprint(n)
	}
}
