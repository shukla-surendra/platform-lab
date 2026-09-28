package main

import (
	"testing"
	"time"
)

func TestPipeline(t *testing.T) {
	var got []int
	for v := range square(gen(1, 2, 3)) {
		got = append(got, v)
	}
	if len(got) != 3 || got[2] != 9 {
		t.Fatal(got)
	}
}

func TestWorkerPoolRunsConcurrently(t *testing.T) {
	start := time.Now()
	res := WorkerPool([]int{0, 1, 2, 3}, 4, func(j int) int {
		time.Sleep(50 * time.Millisecond)
		return j + 1
	})
	if el := time.Since(start); el > 150*time.Millisecond {
		t.Fatalf("expected parallel run, took %s", el)
	}
	for i, r := range res {
		if r.Job != i || r.Output != i+1 {
			t.Fatalf("result %d = %+v", i, r)
		}
	}
}

func TestSelectTimeout(t *testing.T) {
	if fetchWithTimeout(100*time.Millisecond, 10*time.Millisecond) != "timeout" {
		t.Fatal("expected timeout")
	}
	if fetchWithTimeout(0, time.Second) != "response" {
		t.Fatal("expected response")
	}
}
