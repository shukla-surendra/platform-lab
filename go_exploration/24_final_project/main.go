// Lesson 24: Final Project: Website Checker
//
// Run it with:
//
//	go run ./24_final_project
//	go run ./24_final_project https://go.dev https://github.com
//	go run ./24_final_project -timeout 1s https://go.dev
package main

import (
	"context"
	"errors"
	"flag"
	"fmt"
	"net"
	"net/http"
	"os"
	"slices"
	"strings"
	"sync"
	"time"
)

// ---------------------------------------------------------------
// Step 1: What we want to know about each website
// ---------------------------------------------------------------

type Result struct {
	URL      string
	Up       bool
	Duration time.Duration
	Problem  string // why it's down (empty when it's up)
}

// ---------------------------------------------------------------
// Step 2: Check ONE website
// ---------------------------------------------------------------

func checkURL(ctx context.Context, url string, timeout time.Duration) Result {
	start := time.Now()

	// Give this one request a time limit.
	ctx, cancel := context.WithTimeout(ctx, timeout)
	defer cancel()

	req, err := http.NewRequestWithContext(ctx, http.MethodGet, url, nil)
	if err != nil {
		return Result{URL: url, Problem: "bad URL"}
	}

	resp, err := http.DefaultClient.Do(req)
	elapsed := time.Since(start)
	if err != nil {
		return Result{URL: url, Duration: elapsed, Problem: explain(err)}
	}
	defer resp.Body.Close() // always close the body when you're done

	if resp.StatusCode >= 400 {
		return Result{URL: url, Duration: elapsed, Problem: resp.Status}
	}
	return Result{URL: url, Up: true, Duration: elapsed}
}

// explain turns a long technical error into a short, friendly message.
//
// errors.Is checks "is it THIS error?" (Lesson 15).
// errors.As checks "is it this KIND of error?" and, if yes, fills dnsErr.
func explain(err error) string {
	var dnsErr *net.DNSError
	switch {
	case errors.Is(err, context.DeadlineExceeded):
		return "timeout"
	case errors.As(err, &dnsErr):
		return "no such host"
	default:
		return err.Error()
	}
}

// ---------------------------------------------------------------
// Step 3: Check ALL websites at the same time
// ---------------------------------------------------------------

func checkAll(urls []string, timeout time.Duration) []Result {
	ctx := context.Background()
	results := make(chan Result, len(urls)) // room for every result

	var wg sync.WaitGroup
	for _, url := range urls {
		wg.Go(func() {
			results <- checkURL(ctx, url, timeout)
		})
	}

	wg.Wait()      // wait for every check to finish
	close(results) // then say "no more results"

	var all []Result
	for r := range results {
		all = append(all, r)
	}
	return all
}

// ---------------------------------------------------------------
// Step 4: Print a nice report
// ---------------------------------------------------------------

// (up, down int) gives the return values names. They start at 0,
// and a plain "return" at the end sends them back.
func printReport(results []Result) (up, down int) {
	// Sort: down sites first, then by URL.
	slices.SortFunc(results, func(a, b Result) int {
		if a.Up != b.Up {
			if !a.Up {
				return -1
			}
			return 1
		}
		return strings.Compare(a.URL, b.URL)
	})

	fmt.Printf("%-7s %-8s %s\n", "STATUS", "TIME", "URL")
	for _, r := range results {
		status := "UP"
		extra := ""
		if r.Up {
			up++
		} else {
			status = "DOWN"
			extra = "  (" + r.Problem + ")"
			down++
		}
		fmt.Printf("%-7s %-8s %s%s\n", status, r.Duration.Round(time.Millisecond), r.URL, extra)
	}
	return
}

// ---------------------------------------------------------------
// Step 5: main connects everything
// ---------------------------------------------------------------

func main() {
	timeout := flag.Duration("timeout", 5*time.Second, "time limit for each website")
	flag.Parse()

	urls := flag.Args()
	if len(urls) == 0 {
		urls = []string{"https://go.dev", "https://github.com", "https://this-site-does-not-exist.xyz"}
		fmt.Println("No URLs given, so using some examples.")
	}

	fmt.Printf("Checking %d websites (timeout %s)...\n\n", len(urls), *timeout)

	results := checkAll(urls, *timeout)
	up, down := printReport(results)

	fmt.Printf("\n%d up, %d down\n", up, down)

	if down > 0 {
		os.Exit(1) // tell the terminal (or CI) that something failed
	}
}
