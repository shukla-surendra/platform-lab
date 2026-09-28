// Chapter 12 -- a real CLI: concurrent HTTP health checker.
// Pulls together flags, goroutines, context timeouts, errors, and exit codes.
//
//	go run ./12_cli_tool https://go.dev https://example.com https://httpbin.org/status/503
//	go run ./12_cli_tool -timeout 500ms -concurrency 2 -json https://go.dev
//	go build -o healthcheck ./12_cli_tool && ./healthcheck -h
package main

import (
	"context"
	"encoding/json"
	"flag"
	"fmt"
	"io"
	"net/http"
	"os"
	"sync"
	"text/tabwriter"
	"time"
)

type Result struct {
	URL     string        `json:"url"`
	Status  int           `json:"status"`
	Latency time.Duration `json:"latency_ns"`
	Healthy bool          `json:"healthy"`
	Error   string        `json:"error,omitempty"`
}

// Check makes one GET with a per-request timeout derived from ctx.
func Check(ctx context.Context, client *http.Client, url string, timeout time.Duration) Result {
	ctx, cancel := context.WithTimeout(ctx, timeout)
	defer cancel()

	res := Result{URL: url}
	req, err := http.NewRequestWithContext(ctx, http.MethodGet, url, nil)
	if err != nil {
		res.Error = err.Error()
		return res
	}
	start := time.Now()
	resp, err := client.Do(req)
	res.Latency = time.Since(start)
	if err != nil {
		res.Error = err.Error()
		return res
	}
	defer resp.Body.Close()
	io.Copy(io.Discard, resp.Body) // drain so the connection can be reused

	res.Status = resp.StatusCode
	res.Healthy = resp.StatusCode >= 200 && resp.StatusCode < 400
	return res
}

// CheckAll runs checks with bounded concurrency; results keep input order.
func CheckAll(ctx context.Context, urls []string, concurrency int, timeout time.Duration) []Result {
	client := &http.Client{}
	results := make([]Result, len(urls))
	sem := make(chan struct{}, concurrency)
	var wg sync.WaitGroup
	for i, u := range urls {
		wg.Go(func() {
			sem <- struct{}{}
			defer func() { <-sem }()
			results[i] = Check(ctx, client, u, timeout) // each goroutine owns one index: no lock needed
		})
	}
	wg.Wait()
	return results
}

func printTable(w io.Writer, results []Result) {
	tw := tabwriter.NewWriter(w, 0, 0, 2, ' ', 0)
	fmt.Fprintln(tw, "STATUS\tCODE\tLATENCY\tURL\tERROR")
	for _, r := range results {
		state := "UP"
		if !r.Healthy {
			state = "DOWN"
		}
		fmt.Fprintf(tw, "%s\t%d\t%s\t%s\t%s\n", state, r.Status, r.Latency.Round(time.Millisecond), r.URL, r.Error)
	}
	tw.Flush()
}

// run is main() minus os.Exit -- testable, returns the exit code.
func run(args []string, stdout, stderr io.Writer) int {
	fs := flag.NewFlagSet("healthcheck", flag.ContinueOnError)
	fs.SetOutput(stderr)
	timeout := fs.Duration("timeout", 3*time.Second, "per-request timeout")
	concurrency := fs.Int("concurrency", 4, "max parallel requests")
	asJSON := fs.Bool("json", false, "output JSON instead of a table")
	fs.Usage = func() {
		fmt.Fprintln(stderr, "usage: healthcheck [flags] URL...")
		fs.PrintDefaults()
	}
	if err := fs.Parse(args); err != nil {
		return 2
	}
	if fs.NArg() == 0 || *concurrency < 1 {
		fs.Usage()
		return 2
	}

	results := CheckAll(context.Background(), fs.Args(), *concurrency, *timeout)

	if *asJSON {
		enc := json.NewEncoder(stdout)
		enc.SetIndent("", "  ")
		enc.Encode(results)
	} else {
		printTable(stdout, results)
	}

	for _, r := range results {
		if !r.Healthy {
			return 1 // non-zero exit so scripts / CI can react
		}
	}
	return 0
}

func main() {
	os.Exit(run(os.Args[1:], os.Stdout, os.Stderr))
}
