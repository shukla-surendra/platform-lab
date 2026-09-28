// Chapter 09 -- shared state (Mutex, atomic, Once) and context (cancel, timeout, values).
//
//	go run -race ./09_sync_context
package main

import (
	"context"
	"errors"
	"fmt"
	"sync"
	"sync/atomic"
	"time"
)

// --- Mutex-protected map: the classic safe cache ------------------------------

type Cache struct {
	mu   sync.RWMutex // zero value is ready; must not be copied after use
	data map[string]string
	hits atomic.Int64 // lock-free counter
}

func NewCache() *Cache { return &Cache{data: make(map[string]string)} }

func (c *Cache) Get(k string) (string, bool) {
	c.mu.RLock() // many readers at once
	defer c.mu.RUnlock()
	v, ok := c.data[k]
	if ok {
		c.hits.Add(1)
	}
	return v, ok
}

func (c *Cache) Set(k, v string) {
	c.mu.Lock() // exclusive
	defer c.mu.Unlock()
	c.data[k] = v
}

// --- sync.Once: lazy, thread-safe init ---------------------------------------

var (
	configOnce sync.Once
	config     map[string]string
	loads      atomic.Int32
)

func Config() map[string]string {
	configOnce.Do(func() {
		loads.Add(1)
		config = map[string]string{"region": "centralindia"}
	})
	return config
}

// --- context: cancellation that flows down the call tree ---------------------

// SlowQuery pretends to be a DB call that honours cancellation.
func SlowQuery(ctx context.Context, d time.Duration) (string, error) {
	select {
	case <-time.After(d):
		return "rows", nil
	case <-ctx.Done():
		return "", fmt.Errorf("slow query: %w", ctx.Err()) // Canceled or DeadlineExceeded
	}
}

type ctxKey string

const requestIDKey ctxKey = "request-id" // private key type avoids collisions

func handle(ctx context.Context) string {
	id, _ := ctx.Value(requestIDKey).(string)
	res, err := SlowQuery(ctx, 50*time.Millisecond)
	if err != nil {
		return fmt.Sprintf("[%s] failed: %v", id, err)
	}
	return fmt.Sprintf("[%s] got %s", id, res)
}

// FirstSuccess runs all fns concurrently and returns the first result,
// cancelling the rest.
func FirstSuccess(ctx context.Context, fns ...func(context.Context) (string, error)) (string, error) {
	ctx, cancel := context.WithCancel(ctx)
	defer cancel() // ALWAYS call cancel to release resources

	type res struct {
		v   string
		err error
	}
	ch := make(chan res, len(fns))
	for _, fn := range fns {
		go func() {
			v, err := fn(ctx)
			ch <- res{v, err}
		}()
	}
	var errs []error
	for range fns {
		r := <-ch
		if r.err == nil {
			return r.v, nil // deferred cancel() stops the losers
		}
		errs = append(errs, r.err)
	}
	return "", errors.Join(errs...)
}

func main() {
	c := NewCache()
	var wg sync.WaitGroup
	for i := range 100 {
		wg.Go(func() {
			key := fmt.Sprint("k", i%10)
			c.Set(key, "v")
			c.Get(key)
		})
	}
	wg.Wait()
	fmt.Println("cache size:", len(c.data), "hits:", c.hits.Load())

	for range 5 {
		wg.Go(func() { Config() })
	}
	wg.Wait()
	fmt.Println("config loaded", loads.Load(), "time(s):", Config())

	base := context.WithValue(context.Background(), requestIDKey, "req-42")

	ctx, cancel := context.WithTimeout(base, 200*time.Millisecond)
	fmt.Println(handle(ctx))
	cancel()

	ctx, cancel = context.WithTimeout(base, 10*time.Millisecond)
	fmt.Println(handle(ctx))
	cancel()

	ctx, cancel = context.WithCancel(base)
	cancel() // cancelled before we even start
	fmt.Println(handle(ctx))

	winner, err := FirstSuccess(context.Background(),
		func(ctx context.Context) (string, error) { return SlowQuery(ctx, 80*time.Millisecond) },
		func(ctx context.Context) (string, error) { time.Sleep(10 * time.Millisecond); return "replica-2", nil },
		func(ctx context.Context) (string, error) { return "", errors.New("replica-3 down") },
	)
	fmt.Println("first success:", winner, err)
}
