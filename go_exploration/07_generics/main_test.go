package main

import (
	"slices"
	"testing"
)

func TestMapFilterReduce(t *testing.T) {
	got := Map(Filter([]int{1, 2, 3, 4}, func(n int) bool { return n > 2 }), func(n int) string { return string(rune('a' + n)) })
	if !slices.Equal(got, []string{"d", "e"}) {
		t.Fatal(got)
	}
	if Reduce([]string{"a", "b"}, "", func(acc, s string) string { return acc + s }) != "ab" {
		t.Fatal("reduce")
	}
}

func TestSumUnderlyingType(t *testing.T) {
	if Sum([]Celsius{1, 2}) != Celsius(3) {
		t.Fatal("sum")
	}
}

func TestStack(t *testing.T) {
	var s Stack[int]
	if _, ok := s.Pop(); ok {
		t.Fatal("pop on empty should fail")
	}
	s.Push(1)
	s.Push(2)
	if v, _ := s.Pop(); v != 2 {
		t.Fatal("LIFO broken")
	}
}

func TestUniqKeepsOrder(t *testing.T) {
	if got := Uniq([]int{3, 1, 3, 2, 1}); !slices.Equal(got, []int{3, 1, 2}) {
		t.Fatal(got)
	}
}
