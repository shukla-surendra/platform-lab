package main

import (
	"slices"
	"testing"
)

func TestWordCount(t *testing.T) {
	got := WordCount("Go go GO rust")
	if got["go"] != 3 || got["rust"] != 1 || len(got) != 2 {
		t.Fatalf("got %v", got)
	}
}

func TestTopWords(t *testing.T) {
	got := TopWords("b a b c a b", 2)
	if want := []string{"b", "a"}; !slices.Equal(got, want) {
		t.Fatalf("got %v want %v", got, want)
	}
	if got := TopWords("x", 5); len(got) != 1 {
		t.Fatalf("n larger than words: got %v", got)
	}
}

func TestSubSliceSharesBacking(t *testing.T) {
	base := []int{1, 2, 3}
	v := base[:1]
	v = append(v, 42)
	if base[1] != 42 {
		t.Fatal("expected append on sub-slice to overwrite base")
	}
}
