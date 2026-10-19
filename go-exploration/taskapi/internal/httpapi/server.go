// Package httpapi is the HTTP transport: routing, JSON in/out, status codes,
// middleware. Business rules live in package task, not here.
package httpapi

import (
	"context"
	"log/slog"
	"net/http"
	"strconv"
	"time"

	"platformlab/taskapi/internal/task"
)

// TaskService is defined HERE, by the consumer, listing only what handlers
// need. *task.Service satisfies it implicitly; tests could pass a stub.
type TaskService interface {
	Create(ctx context.Context, in task.CreateInput) (task.Task, error)
	Get(ctx context.Context, id int64) (task.Task, error)
	List(ctx context.Context, f task.ListFilter) (task.Page, error)
	Update(ctx context.Context, id int64, in task.UpdateInput) (task.Task, error)
	Delete(ctx context.Context, id int64) error
}

// Pinger lets /readyz check the database without importing pgx here.
type Pinger interface {
	Ping(ctx context.Context) error
}

type API struct {
	tasks TaskService
	db    Pinger
	log   *slog.Logger
}

func New(tasks TaskService, db Pinger, log *slog.Logger) *API {
	return &API{tasks: tasks, db: db, log: log}
}

// Handler builds the router and wraps it in middleware (outermost first).
func (a *API) Handler() http.Handler {
	mux := http.NewServeMux()

	mux.HandleFunc("GET /healthz", a.healthz) // liveness: process is up
	mux.HandleFunc("GET /readyz", a.readyz)   // readiness: can serve traffic (DB reachable)

	mux.HandleFunc("POST /v1/tasks", a.createTask)
	mux.HandleFunc("GET /v1/tasks", a.listTasks)
	mux.HandleFunc("GET /v1/tasks/{id}", a.getTask)
	mux.HandleFunc("PATCH /v1/tasks/{id}", a.updateTask)
	mux.HandleFunc("DELETE /v1/tasks/{id}", a.deleteTask)

	var h http.Handler = mux
	h = recoverPanics(a.log)(h)
	h = logRequests(a.log)(h)
	h = requestID(h)
	return h
}

func (a *API) healthz(w http.ResponseWriter, r *http.Request) {
	writeJSON(w, http.StatusOK, map[string]string{"status": "ok"})
}

func (a *API) readyz(w http.ResponseWriter, r *http.Request) {
	ctx, cancel := context.WithTimeout(r.Context(), 2*time.Second)
	defer cancel()
	if err := a.db.Ping(ctx); err != nil {
		a.log.WarnContext(r.Context(), "readiness check failed", "err", err)
		writeJSON(w, http.StatusServiceUnavailable, map[string]string{"status": "database unavailable"})
		return
	}
	writeJSON(w, http.StatusOK, map[string]string{"status": "ready"})
}

func (a *API) createTask(w http.ResponseWriter, r *http.Request) {
	var in task.CreateInput
	if err := decodeJSON(w, r, &in); err != nil {
		writeError(w, r, a.log, err)
		return
	}
	t, err := a.tasks.Create(r.Context(), in)
	if err != nil {
		writeError(w, r, a.log, err)
		return
	}
	w.Header().Set("Location", "/v1/tasks/"+strconv.FormatInt(t.ID, 10))
	writeJSON(w, http.StatusCreated, t)
}

func (a *API) listTasks(w http.ResponseWriter, r *http.Request) {
	q := r.URL.Query()
	var f task.ListFilter
	if s := q.Get("status"); s != "" {
		st := task.Status(s)
		f.Status = &st
	}
	var err error
	if f.Limit, err = intParam(q.Get("limit")); err != nil {
		writeError(w, r, a.log, badRequest("limit must be an integer"))
		return
	}
	if f.Offset, err = intParam(q.Get("offset")); err != nil {
		writeError(w, r, a.log, badRequest("offset must be an integer"))
		return
	}
	page, err := a.tasks.List(r.Context(), f)
	if err != nil {
		writeError(w, r, a.log, err)
		return
	}
	writeJSON(w, http.StatusOK, page)
}

func (a *API) getTask(w http.ResponseWriter, r *http.Request) {
	id, err := pathID(r)
	if err != nil {
		writeError(w, r, a.log, err)
		return
	}
	t, err := a.tasks.Get(r.Context(), id)
	if err != nil {
		writeError(w, r, a.log, err)
		return
	}
	writeJSON(w, http.StatusOK, t)
}

func (a *API) updateTask(w http.ResponseWriter, r *http.Request) {
	id, err := pathID(r)
	if err != nil {
		writeError(w, r, a.log, err)
		return
	}
	var in task.UpdateInput
	if err := decodeJSON(w, r, &in); err != nil {
		writeError(w, r, a.log, err)
		return
	}
	t, err := a.tasks.Update(r.Context(), id, in)
	if err != nil {
		writeError(w, r, a.log, err)
		return
	}
	writeJSON(w, http.StatusOK, t)
}

func (a *API) deleteTask(w http.ResponseWriter, r *http.Request) {
	id, err := pathID(r)
	if err != nil {
		writeError(w, r, a.log, err)
		return
	}
	if err := a.tasks.Delete(r.Context(), id); err != nil {
		writeError(w, r, a.log, err)
		return
	}
	w.WriteHeader(http.StatusNoContent)
}

func pathID(r *http.Request) (int64, error) {
	id, err := strconv.ParseInt(r.PathValue("id"), 10, 64)
	if err != nil || id < 1 {
		return 0, badRequest("id must be a positive integer")
	}
	return id, nil
}

func intParam(s string) (int, error) {
	if s == "" {
		return 0, nil
	}
	return strconv.Atoi(s)
}
