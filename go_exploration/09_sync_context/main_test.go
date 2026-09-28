package main

import (
	"context"
	"errors"
	"sync"
	"testing"
	"time"
)

func TestCacheConcurrent(t *testing.T) { // meaningful under `go test -race`
	c := NewCache()
	var wg sync.WaitGroup
	for range 50 {
		wg.Go(func() { c.Set("a", "1"); c.Get("a") })
	}
	wg.Wait()
	if c.hits.Load() != 50 {
		t.Fatalf("hits = %d", c.hits.Load())
	}
}

func TestSlowQueryDeadline(t *testing.T) {
	ctx, cancel := context.WithTimeout(context.Background(), 5*time.Millisecond)
	defer cancel()
	_, err := SlowQuery(ctx, time.Second)
	if !errors.Is(err, context.DeadlineExceeded) {
		t.Fatalf("got %v", err)
	}
}

func TestFirstSuccess(t *testing.T) {
	v, err := FirstSuccess(context.Background(),
		func(ctx context.Context) (string, error) { return "", errors.New("a") },
		func(ctx context.Context) (string, error) { return "b", nil },
	)
	if err != nil || v != "b" {
		t.Fatal(v, err)
	}
	_, err = FirstSuccess(context.Background(),
		func(ctx context.Context) (string, error) { return "", errors.New("x") },
	)
	if err == nil {
		t.Fatal("all failed but no error")
	}
}
