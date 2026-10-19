// Lesson 17: Generics
//
// Run it with:  go run ./17_generics
package main

import (
	"cmp"
	"fmt"
)

// T is a placeholder for int or float64.
func Sum[T int | float64](nums []T) T {
	var total T
	for _, n := range nums {
		total += n
	}
	return total
}

// comparable = types that work with ==
func Contains[T comparable](items []T, target T) bool {
	for _, item := range items {
		if item == target {
			return true
		}
	}
	return false
}

// cmp.Ordered = types that work with < and >
func Max[T cmp.Ordered](a, b T) T {
	if a > b {
		return a
	}
	return b
}

// keep is a function we pass in. It decides which items stay.
func Filter[T any](items []T, keep func(T) bool) []T {
	var result []T
	for _, item := range items {
		if keep(item) {
			result = append(result, item)
		}
	}
	return result
}

// ----- A generic type -----

type Stack[T any] struct {
	items []T
}

func (s *Stack[T]) Push(item T) {
	s.items = append(s.items, item)
}

func (s *Stack[T]) Pop() T {
	last := s.items[len(s.items)-1]
	s.items = s.items[:len(s.items)-1]
	return last
}

func (s *Stack[T]) Len() int {
	return len(s.items)
}

func main() {
	fmt.Println("Sum of ints:  ", Sum([]int{1, 2, 3}))
	fmt.Println("Sum of floats:", Sum([]float64{1.5, 2.5}))

	fmt.Println("Contains b?", Contains([]string{"a", "b"}, "b"))
	fmt.Println("Contains 5?", Contains([]int{1, 2, 3}, 5))

	fmt.Println("Max(3, 7) =", Max(3, 7))
	fmt.Println(`Max("apple", "mango") =`, Max("apple", "mango"))

	evens := Filter([]int{1, 2, 3, 4, 5, 6}, func(n int) bool {
		return n%2 == 0
	})
	fmt.Println("Evens:", evens)

	longWords := Filter([]string{"go", "golang", "hi", "gopher"}, func(w string) bool {
		return len(w) > 3
	})
	fmt.Println("Long words:", longWords)

	// Stack of ints
	nums := Stack[int]{}
	nums.Push(1)
	nums.Push(2)
	nums.Push(3)
	fmt.Println("Popped:", nums.Pop(), "| left:", nums.Len())

	// Stack of strings: same code, different type
	plates := Stack[string]{}
	plates.Push("red plate")
	plates.Push("blue plate")
	fmt.Println("Top plate:", plates.Pop())
}
