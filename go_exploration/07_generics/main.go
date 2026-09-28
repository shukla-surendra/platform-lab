// Chapter 07 -- generics: type parameters, constraints, generic types.
//
//	go run ./07_generics
package main

import (
	"cmp"
	"fmt"
	"strings"
)

// Map/Filter/Reduce -- one implementation for every element type.
func Map[T, U any](xs []T, fn func(T) U) []U {
	out := make([]U, 0, len(xs))
	for _, x := range xs {
		out = append(out, fn(x))
	}
	return out
}

func Filter[T any](xs []T, keep func(T) bool) []T {
	var out []T
	for _, x := range xs {
		if keep(x) {
			out = append(out, x)
		}
	}
	return out
}

func Reduce[T, A any](xs []T, init A, fn func(A, T) A) A {
	acc := init
	for _, x := range xs {
		acc = fn(acc, x)
	}
	return acc
}

// A constraint is an interface listing allowed types. ~int means "int or any
// type whose underlying type is int" (e.g. `type Celsius int`).
type Number interface {
	~int | ~int64 | ~float64
}

func Sum[T Number](xs []T) T {
	var total T
	for _, x := range xs {
		total += x
	}
	return total
}

// cmp.Ordered = anything supporting < > (ints, floats, strings).
func MaxOf[T cmp.Ordered](first T, rest ...T) T {
	m := first
	for _, x := range rest {
		m = max(m, x)
	}
	return m
}

// comparable = anything usable with == (and as a map key).
func Uniq[T comparable](xs []T) []T {
	seen := make(map[T]struct{}, len(xs)) // struct{} takes zero bytes
	var out []T
	for _, x := range xs {
		if _, ok := seen[x]; !ok {
			seen[x] = struct{}{}
			out = append(out, x)
		}
	}
	return out
}

// --- Generic types ----------------------------------------------------------

type Stack[T any] struct{ items []T }

func (s *Stack[T]) Push(v T) { s.items = append(s.items, v) }

func (s *Stack[T]) Pop() (T, bool) {
	var zero T
	if len(s.items) == 0 {
		return zero, false
	}
	v := s.items[len(s.items)-1]
	s.items = s.items[:len(s.items)-1]
	return v, true
}

func (s *Stack[T]) Len() int { return len(s.items) }

// Pair shows multiple type parameters on a type.
type Pair[K comparable, V any] struct {
	Key K
	Val V
}

func (p Pair[K, V]) String() string { return fmt.Sprintf("%v=%v", p.Key, p.Val) }

type Celsius int

func main() {
	nums := []int{1, 2, 3, 4, 5, 6}
	evens := Filter(nums, func(n int) bool { return n%2 == 0 }) // T inferred as int
	squares := Map(evens, func(n int) int { return n * n })
	labels := Map(squares, func(n int) string { return fmt.Sprintf("<%d>", n) }) // int -> string
	fmt.Println(evens, squares, strings.Join(labels, ""))
	fmt.Println("reduce sum:", Reduce(nums, 0, func(a, n int) int { return a + n }))

	fmt.Println("Sum ints:", Sum(nums), "floats:", Sum([]float64{1.5, 2.25}))
	fmt.Println("Sum Celsius via ~int:", Sum([]Celsius{20, 22}))
	fmt.Println("MaxOf:", MaxOf(3, 9, 2), MaxOf("kiwi", "apple", "pear"))
	fmt.Println("Uniq:", Uniq([]string{"a", "b", "a", "c", "b"}))

	var s Stack[string]
	s.Push("first")
	s.Push("second")
	top, _ := s.Pop()
	fmt.Println("stack pop:", top, "remaining:", s.Len())

	fmt.Println(Pair[string, int]{"replicas", 3})
}
