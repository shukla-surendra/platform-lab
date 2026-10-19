package main

import "testing"

// 1. The simplest test: call, compare, report.
func TestAdd(t *testing.T) {
	got := Add(2, 3)
	want := 5

	if got != want {
		t.Errorf("Add(2, 3) = %d, want %d", got, want)
	}
}

// 2. A table test: many cases, one loop.
func TestGrade(t *testing.T) {
	tests := []struct {
		marks int
		want  string
	}{
		{95, "A"},
		{75, "B"},
		{55, "C"},
		{30, "Fail"},
		{0, "Fail"},
	}

	for _, tc := range tests {
		got := Grade(tc.marks)
		if got != tc.want {
			t.Errorf("Grade(%d) = %q, want %q", tc.marks, got, tc.want)
		}
	}
}

// 3. Testing the happy path of a function that returns an error.
func TestDiscount(t *testing.T) {
	got, err := Discount(200, 10)
	if err != nil {
		t.Fatalf("unexpected error: %v", err) // stop: got is meaningless now
	}
	if got != 180 {
		t.Errorf("Discount(200, 10) = %v, want 180", got)
	}
}

// 4. Testing that bad input gives an error.
func TestDiscountError(t *testing.T) {
	_, err := Discount(100, 150)
	if err == nil {
		t.Error("expected an error for 150%, got nil")
	}
}
