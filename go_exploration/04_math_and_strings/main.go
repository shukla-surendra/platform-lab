// Lesson 04: Math and Text
//
// Run it with:  go run ./04_math_and_strings
package main

import (
	"fmt"
	"strconv"
	"strings"
)

func main() {
	// ===== Part A: Math =====
	fmt.Println("--- Math ---")
	fmt.Println("7 + 2 =", 7+2)
	fmt.Println("7 - 2 =", 7-2)
	fmt.Println("7 * 2 =", 7*2)
	fmt.Println("7 / 2 =", 7/2, "  <- int / int drops the decimal")
	fmt.Println("7.0 / 2.0 =", 7.0/2.0)
	fmt.Println("7 % 2 =", 7%2, "  <- remainder")

	score := 10
	score += 5
	score++
	fmt.Println("score:", score) // 16

	// ===== Part B: Text =====
	fmt.Println("\n--- Text ---")
	first := "Ravi"
	last := "Kumar"
	full := first + " " + last
	fmt.Println("Full name:", full)
	fmt.Println("Length:", len(full))

	fmt.Println(strings.ToUpper("hello"))
	fmt.Println(strings.Contains("hello world", "world"))
	fmt.Println(strings.Replace("I like tea", "tea", "coffee", 1))
	fmt.Println("[" + strings.TrimSpace("   hi   ") + "]")
	fmt.Println(strings.Split("a,b,c", ","))
	fmt.Println(strings.Repeat("ha", 3))

	// ===== Part C: Changing types =====
	fmt.Println("\n--- Conversion ---")
	apples := 7
	price := 2.5
	total := float64(apples) * price // must convert apples to float64 first
	fmt.Println("Total price:", total)

	cost := 9.99
	fmt.Println("int(9.99) =", int(cost), "  <- decimal part is cut off")

	text := strconv.Itoa(42)
	fmt.Println("strconv.Itoa(42) gives the text:", text)

	n, err := strconv.Atoi("42")
	fmt.Println("strconv.Atoi(\"42\") gives the number:", n, "error:", err)

	_, err = strconv.Atoi("hello")
	fmt.Println("strconv.Atoi(\"hello\") fails with:", err)

	fmt.Println("string(65) =", string(rune(65)), "  <- a letter, not \"65\"!")
}
