package main

import (
	"encoding/json"
	"io"
	"log/slog"
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"
)

func newTestServer(t *testing.T) *httptest.Server {
	t.Helper()
	s := &Server{store: NewStore(), log: slog.New(slog.NewTextHandler(io.Discard, nil))}
	ts := httptest.NewServer(s.Routes()) // real HTTP server on a random port
	t.Cleanup(ts.Close)
	return ts
}

func do(t *testing.T, method, url, body string) (*http.Response, string) {
	t.Helper()
	req, _ := http.NewRequest(method, url, strings.NewReader(body))
	resp, err := http.DefaultClient.Do(req)
	if err != nil {
		t.Fatal(err)
	}
	defer resp.Body.Close()
	b, _ := io.ReadAll(resp.Body)
	return resp, string(b)
}

func TestTodoLifecycle(t *testing.T) {
	ts := newTestServer(t)

	resp, body := do(t, "POST", ts.URL+"/todos", `{"title":"learn go"}`)
	if resp.StatusCode != http.StatusCreated {
		t.Fatalf("create: %d %s", resp.StatusCode, body)
	}
	var created Todo
	json.Unmarshal([]byte(body), &created)
	if created.ID != 1 || created.Title != "learn go" {
		t.Fatalf("created = %+v", created)
	}

	if resp, _ := do(t, "GET", ts.URL+"/todos/1", ""); resp.StatusCode != 200 {
		t.Fatalf("get: %d", resp.StatusCode)
	}
	if _, body := do(t, "GET", ts.URL+"/todos", ""); !strings.Contains(body, "learn go") {
		t.Fatalf("list: %s", body)
	}
	if resp, _ := do(t, "DELETE", ts.URL+"/todos/1", ""); resp.StatusCode != http.StatusNoContent {
		t.Fatalf("delete: %d", resp.StatusCode)
	}
	if resp, _ := do(t, "GET", ts.URL+"/todos/1", ""); resp.StatusCode != http.StatusNotFound {
		t.Fatalf("get after delete: %d", resp.StatusCode)
	}
}

func TestValidation(t *testing.T) {
	ts := newTestServer(t)
	tests := []struct {
		name, method, path, body string
		want                     int
	}{
		{"bad json", "POST", "/todos", `{`, http.StatusBadRequest},
		{"unknown field", "POST", "/todos", `{"titel":"x"}`, http.StatusBadRequest},
		{"empty title", "POST", "/todos", `{"title":""}`, http.StatusUnprocessableEntity},
		{"non-int id", "GET", "/todos/abc", "", http.StatusBadRequest},
		{"wrong method", "PUT", "/todos", "", http.StatusMethodNotAllowed},
	}
	for _, tc := range tests {
		t.Run(tc.name, func(t *testing.T) {
			if resp, body := do(t, tc.method, ts.URL+tc.path, tc.body); resp.StatusCode != tc.want {
				t.Errorf("got %d want %d (%s)", resp.StatusCode, tc.want, body)
			}
		})
	}
}

// Handlers can also be tested without a network at all.
func TestHealthzRecorder(t *testing.T) {
	s := &Server{store: NewStore(), log: slog.New(slog.NewTextHandler(io.Discard, nil))}
	rec := httptest.NewRecorder()
	s.Routes().ServeHTTP(rec, httptest.NewRequest("GET", "/healthz", nil))
	if rec.Code != 200 || !strings.Contains(rec.Body.String(), "ok") {
		t.Fatalf("%d %s", rec.Code, rec.Body)
	}
}
