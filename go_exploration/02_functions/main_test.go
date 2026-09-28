package main

import "testing"

func TestDivide(t *testing.T) {
	if q, err := Divide(9, 2); err != nil || q != 4 {
		t.Fatalf("Divide(9,2) = %d, %v", q, err)
	}
	if _, err := Divide(1, 0); err == nil {
		t.Fatal("expected error for divide by zero")
	}
}

func TestMinMax(t *testing.T) {
	lo, hi := MinMax(3, -1, 8)
	if lo != -1 || hi != 8 {
		t.Fatalf("got %d,%d", lo, hi)
	}
	if lo, hi := MinMax(); lo != 0 || hi != 0 {
		t.Fatalf("empty: got %d,%d", lo, hi)
	}
}

func TestCounterIndependent(t *testing.T) {
	a, b := Counter(), Counter()
	a()
	a()
	if a() != 3 || b() != 1 {
		t.Fatal("counters share state")
	}
}

func TestDeferOrder(t *testing.T) {
	if got, want := deferDemo(), "body defer2 defer1 defer0"; got != want {
		t.Fatalf("got %q want %q", got, want)
	}
}

func TestSafeDiv(t *testing.T) {
	if _, err := safeDiv(1, 0); err == nil {
		t.Fatal("expected recovered error")
	}
}
