package main

import (
	"bytes"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"
	"time"
)

// fakeBackends spins up local servers so tests never touch the internet.
func fakeBackends(t *testing.T) (ok, broken, slow string) {
	t.Helper()
	mk := func(h http.HandlerFunc) string {
		s := httptest.NewServer(h)
		t.Cleanup(s.Close)
		return s.URL
	}
	ok = mk(func(w http.ResponseWriter, r *http.Request) { w.WriteHeader(200) })
	broken = mk(func(w http.ResponseWriter, r *http.Request) { w.WriteHeader(503) })
	slow = mk(func(w http.ResponseWriter, r *http.Request) {
		select {
		case <-time.After(time.Second):
		case <-r.Context().Done():
		}
	})
	return
}

func TestRunAllHealthy(t *testing.T) {
	ok, _, _ := fakeBackends(t)
	var out, errOut bytes.Buffer
	if code := run([]string{ok, ok}, &out, &errOut); code != 0 {
		t.Fatalf("exit %d, out:\n%s", code, out.String())
	}
	if strings.Count(out.String(), "UP") != 2 {
		t.Fatalf("table:\n%s", out.String())
	}
}

func TestRunDetectsFailuresAndTimeouts(t *testing.T) {
	ok, broken, slow := fakeBackends(t)
	var out, errOut bytes.Buffer
	code := run([]string{"-json", "-timeout", "100ms", ok, broken, slow}, &out, &errOut)
	if code != 1 {
		t.Fatalf("exit %d want 1", code)
	}
	var res []Result
	if err := json.Unmarshal(out.Bytes(), &res); err != nil {
		t.Fatal(err, out.String())
	}
	if !res[0].Healthy || res[1].Healthy || res[1].Status != 503 {
		t.Fatalf("results: %+v", res)
	}
	if res[2].Healthy || !strings.Contains(res[2].Error, "deadline exceeded") {
		t.Fatalf("slow result: %+v", res[2])
	}
}

func TestRunUsageErrors(t *testing.T) {
	var out, errOut bytes.Buffer
	if code := run(nil, &out, &errOut); code != 2 || !strings.Contains(errOut.String(), "usage") {
		t.Fatalf("no args: exit %d stderr=%q", code, errOut.String())
	}
	if code := run([]string{"-bogus"}, &out, &errOut); code != 2 {
		t.Fatalf("bad flag: exit %d", code)
	}
}
