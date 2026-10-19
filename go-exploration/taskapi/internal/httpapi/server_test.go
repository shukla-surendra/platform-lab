package httpapi

import (
	"context"
	"encoding/json"
	"errors"
	"io"
	"log/slog"
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"

	"platformlab/taskapi/internal/task"
)

type fakePinger struct{ err error }

func (f fakePinger) Ping(context.Context) error { return f.err }

func quietLogger() *slog.Logger { return slog.New(slog.NewTextHandler(io.Discard, nil)) }

// newTestAPI wires the REAL service to the in-memory repository: handlers,
// validation and error mapping are all exercised; only Postgres is swapped out.
func newTestAPI(t *testing.T) http.Handler {
	t.Helper()
	svc := task.NewService(task.NewMemoryRepository())
	return New(svc, fakePinger{}, quietLogger()).Handler()
}

type response struct {
	code int
	body map[string]any
	raw  string
	hdr  http.Header
}

func call(t *testing.T, h http.Handler, method, path, body string) response {
	t.Helper()
	req := httptest.NewRequest(method, path, strings.NewReader(body))
	rec := httptest.NewRecorder()
	h.ServeHTTP(rec, req)
	res := response{code: rec.Code, raw: rec.Body.String(), hdr: rec.Header()}
	_ = json.Unmarshal(rec.Body.Bytes(), &res.body)
	return res
}

func TestTaskCRUD(t *testing.T) {
	h := newTestAPI(t)

	res := call(t, h, "POST", "/v1/tasks", `{"title":"learn go","priority":1}`)
	if res.code != http.StatusCreated || res.hdr.Get("Location") != "/v1/tasks/1" {
		t.Fatalf("create: %d %s loc=%q", res.code, res.raw, res.hdr.Get("Location"))
	}
	if res.body["status"] != "todo" || res.body["priority"] != 1.0 {
		t.Fatalf("create body: %s", res.raw)
	}

	if res := call(t, h, "GET", "/v1/tasks/1", ""); res.code != 200 || res.body["title"] != "learn go" {
		t.Fatalf("get: %d %s", res.code, res.raw)
	}

	res = call(t, h, "PATCH", "/v1/tasks/1", `{"status":"done"}`)
	if res.code != 200 || res.body["status"] != "done" || res.body["title"] != "learn go" {
		t.Fatalf("patch: %d %s", res.code, res.raw)
	}

	res = call(t, h, "GET", "/v1/tasks?status=done", "")
	if res.code != 200 || res.body["total"] != 1.0 {
		t.Fatalf("list: %d %s", res.code, res.raw)
	}

	if res := call(t, h, "DELETE", "/v1/tasks/1", ""); res.code != http.StatusNoContent {
		t.Fatalf("delete: %d", res.code)
	}
	if res := call(t, h, "GET", "/v1/tasks/1", ""); res.code != http.StatusNotFound {
		t.Fatalf("get after delete: %d", res.code)
	}
}

func TestErrorResponses(t *testing.T) {
	h := newTestAPI(t)
	tests := []struct {
		name, method, path, body string
		wantCode                 int
		wantInBody               string
	}{
		{"empty body", "POST", "/v1/tasks", ``, 400, "empty"},
		{"malformed json", "POST", "/v1/tasks", `{"title":`, 400, "invalid JSON"},
		{"unknown field", "POST", "/v1/tasks", `{"titel":"x"}`, 400, "unknown field"},
		{"two objects", "POST", "/v1/tasks", `{"title":"a"}{"title":"b"}`, 400, "single JSON object"},
		{"validation", "POST", "/v1/tasks", `{"title":"","priority":9}`, 422, `"priority"`},
		{"bad id", "GET", "/v1/tasks/abc", ``, 400, "positive integer"},
		{"zero id", "GET", "/v1/tasks/0", ``, 400, "positive integer"},
		{"not found", "GET", "/v1/tasks/42", ``, 404, "not found"},
		{"bad limit", "GET", "/v1/tasks?limit=ten", ``, 400, "limit"},
		{"bad status filter", "GET", "/v1/tasks?status=archived", ``, 422, "status"},
		{"empty patch", "PATCH", "/v1/tasks/1", `{}`, 422, "body"},
		{"method not allowed", "PUT", "/v1/tasks/1", ``, 405, ""},
	}
	for _, tc := range tests {
		t.Run(tc.name, func(t *testing.T) {
			res := call(t, h, tc.method, tc.path, tc.body)
			if res.code != tc.wantCode || !strings.Contains(res.raw, tc.wantInBody) {
				t.Fatalf("got %d %s; want %d containing %q", res.code, res.raw, tc.wantCode, tc.wantInBody)
			}
		})
	}
}

func TestRequestIDPropagation(t *testing.T) {
	h := newTestAPI(t)

	res := call(t, h, "GET", "/v1/tasks/99", "")
	id := res.hdr.Get("X-Request-ID")
	if id == "" || res.body["request_id"] != id {
		t.Fatalf("generated id %q not in body %s", id, res.raw)
	}

	req := httptest.NewRequest("GET", "/healthz", nil)
	req.Header.Set("X-Request-ID", "from-ingress-123")
	rec := httptest.NewRecorder()
	h.ServeHTTP(rec, req)
	if rec.Header().Get("X-Request-ID") != "from-ingress-123" {
		t.Fatal("incoming request id not reused")
	}
}

func TestReadyz(t *testing.T) {
	svc := task.NewService(task.NewMemoryRepository())
	up := New(svc, fakePinger{}, quietLogger()).Handler()
	down := New(svc, fakePinger{err: errors.New("conn refused")}, quietLogger()).Handler()

	if res := call(t, up, "GET", "/readyz", ""); res.code != 200 {
		t.Fatalf("up: %d", res.code)
	}
	if res := call(t, down, "GET", "/readyz", ""); res.code != http.StatusServiceUnavailable {
		t.Fatalf("down: %d", res.code)
	}
}

// panickingService embeds the interface (nil) and overrides one method --
// a quick way to stub only what a test needs.
type panickingService struct{ TaskService }

func (panickingService) Get(context.Context, int64) (task.Task, error) { panic("boom") }

type failingService struct{ TaskService }

func (failingService) Get(context.Context, int64) (task.Task, error) {
	return task.Task{}, errors.New("pq: connection reset by peer")
}

func TestInternalErrorsAreHidden(t *testing.T) {
	for name, svc := range map[string]TaskService{"panic": panickingService{}, "error": failingService{}} {
		t.Run(name, func(t *testing.T) {
			h := New(svc, fakePinger{}, quietLogger()).Handler()
			res := call(t, h, "GET", "/v1/tasks/1", "")
			if res.code != 500 || strings.Contains(res.raw, "boom") || strings.Contains(res.raw, "pq:") {
				t.Fatalf("leaked internals or wrong code: %d %s", res.code, res.raw)
			}
		})
	}
}
