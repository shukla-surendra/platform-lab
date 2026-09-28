package main

import (
	"errors"
	"testing"
)

func TestClassify(t *testing.T) {
	tests := []struct{ in, want string }{
		{"1", "ok"},
		{"99", "404"},
		{"0", "400 field=id"},
		{"x", "400 bad number"},
	}
	for _, tc := range tests {
		t.Run(tc.in, func(t *testing.T) {
			_, err := LookupFromInput(tc.in)
			if got := Classify(err); got != tc.want {
				t.Errorf("got %q want %q (err=%v)", got, tc.want, err)
			}
		})
	}
}

func TestWrappingPreservesIdentity(t *testing.T) {
	_, err := LookupFromInput("42")
	if !errors.Is(err, ErrNotFound) {
		t.Fatal("wrap chain lost ErrNotFound")
	}
	if err.Error() != "lookup: find user 42: not found" {
		t.Fatalf("message = %q", err.Error())
	}
}
