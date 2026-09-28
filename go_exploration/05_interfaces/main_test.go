package main

import (
	"bytes"
	"errors"
	"math"
	"strings"
	"testing"
)

func TestTotalArea(t *testing.T) {
	got := TotalArea(Rect{2, 3}, Circle{1})
	if want := 6 + math.Pi; math.Abs(got-want) > 1e-9 {
		t.Fatalf("got %v want %v", got, want)
	}
}

func TestDescribe(t *testing.T) {
	tests := []struct {
		in   any
		want string
	}{
		{nil, "nil"},
		{7, "int 7"},
		{"abc", "string of len 3"},
		{Rect{1, 2}, "shape with area 2.00"},
		{errors.New("x"), "error: x"},
		{true, "other bool"},
	}
	for _, tc := range tests {
		if got := Describe(tc.in); got != tc.want {
			t.Errorf("Describe(%v) = %q want %q", tc.in, got, tc.want)
		}
	}
}

func TestUpperWriter(t *testing.T) {
	var buf bytes.Buffer
	UpperWriter{&buf}.Write([]byte("abc"))
	if buf.String() != "ABC" {
		t.Fatal(buf.String())
	}
}

func TestCountLines(t *testing.T) {
	if n, _ := CountLines(strings.NewReader("1\n2\n")); n != 2 {
		t.Fatal(n)
	}
}
