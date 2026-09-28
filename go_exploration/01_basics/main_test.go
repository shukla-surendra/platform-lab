package main

import "testing"

func TestFizzBuzz(t *testing.T) {
	cases := map[int]string{1: "1", 3: "Fizz", 5: "Buzz", 15: "FizzBuzz", 98: "98"}
	for in, want := range cases {
		if got := FizzBuzz(in); got != want {
			t.Errorf("FizzBuzz(%d) = %q, want %q", in, got, want)
		}
	}
}
