// Chapter 11 -- a small JSON REST API with only the standard library.
//
//	go run ./11_http_server             # listens on :8080 (PORT env overrides)
//	curl localhost:8080/healthz
//	curl -X POST localhost:8080/todos -d '{"title":"learn go"}'
//	curl localhost:8080/todos
//	curl localhost:8080/todos/1
//	curl -X DELETE localhost:8080/todos/1
package main

import (
	"context"
	"encoding/json"
	"errors"
	"log/slog"
	"net/http"
	"os"
	"os/signal"
	"strconv"
	"sync"
	"syscall"
	"time"
)

type Todo struct {
	ID    int    `json:"id"`
	Title string `json:"title"`
	Done  bool   `json:"done"`
}

// Store is an in-memory, concurrency-safe repository.
type Store struct {
	mu     sync.Mutex
	nextID int
	todos  map[int]Todo
}

func NewStore() *Store { return &Store{nextID: 1, todos: map[int]Todo{}} }

func (s *Store) Create(title string) Todo {
	s.mu.Lock()
	defer s.mu.Unlock()
	t := Todo{ID: s.nextID, Title: title}
	s.todos[t.ID] = t
	s.nextID++
	return t
}

func (s *Store) Get(id int) (Todo, bool) {
	s.mu.Lock()
	defer s.mu.Unlock()
	t, ok := s.todos[id]
	return t, ok
}

func (s *Store) List() []Todo {
	s.mu.Lock()
	defer s.mu.Unlock()
	out := make([]Todo, 0, len(s.todos))
	for id := 1; id < s.nextID; id++ { // ID order, not random map order
		if t, ok := s.todos[id]; ok {
			out = append(out, t)
		}
	}
	return out
}

func (s *Store) Delete(id int) bool {
	s.mu.Lock()
	defer s.mu.Unlock()
	_, ok := s.todos[id]
	delete(s.todos, id)
	return ok
}

// --- HTTP layer ---------------------------------------------------------------

type Server struct {
	store *Store
	log   *slog.Logger
}

// Routes uses Go 1.22+ ServeMux patterns: METHOD + path + {wildcards}.
func (s *Server) Routes() http.Handler {
	mux := http.NewServeMux()
	mux.HandleFunc("GET /healthz", func(w http.ResponseWriter, r *http.Request) {
		writeJSON(w, http.StatusOK, map[string]string{"status": "ok"})
	})
	mux.HandleFunc("GET /todos", s.listTodos)
	mux.HandleFunc("POST /todos", s.createTodo)
	mux.HandleFunc("GET /todos/{id}", s.getTodo)
	mux.HandleFunc("DELETE /todos/{id}", s.deleteTodo)
	return s.logging(mux)
}

func (s *Server) listTodos(w http.ResponseWriter, r *http.Request) {
	writeJSON(w, http.StatusOK, s.store.List())
}

func (s *Server) createTodo(w http.ResponseWriter, r *http.Request) {
	var in struct {
		Title string `json:"title"`
	}
	r.Body = http.MaxBytesReader(w, r.Body, 1<<20) // don't let clients send 10GB
	dec := json.NewDecoder(r.Body)
	dec.DisallowUnknownFields()
	if err := dec.Decode(&in); err != nil {
		writeError(w, http.StatusBadRequest, "invalid JSON: "+err.Error())
		return
	}
	if in.Title == "" {
		writeError(w, http.StatusUnprocessableEntity, "title is required")
		return
	}
	writeJSON(w, http.StatusCreated, s.store.Create(in.Title))
}

func (s *Server) getTodo(w http.ResponseWriter, r *http.Request) {
	id, err := strconv.Atoi(r.PathValue("id"))
	if err != nil {
		writeError(w, http.StatusBadRequest, "id must be an integer")
		return
	}
	t, ok := s.store.Get(id)
	if !ok {
		writeError(w, http.StatusNotFound, "todo not found")
		return
	}
	writeJSON(w, http.StatusOK, t)
}

func (s *Server) deleteTodo(w http.ResponseWriter, r *http.Request) {
	id, err := strconv.Atoi(r.PathValue("id"))
	if err != nil || !s.store.Delete(id) {
		writeError(w, http.StatusNotFound, "todo not found")
		return
	}
	w.WriteHeader(http.StatusNoContent)
}

// Middleware = a function that wraps a handler.
func (s *Server) logging(next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		start := time.Now()
		rec := &statusRecorder{ResponseWriter: w, status: http.StatusOK}
		next.ServeHTTP(rec, r)
		s.log.Info("request", "method", r.Method, "path", r.URL.Path,
			"status", rec.status, "dur", time.Since(start))
	})
}

type statusRecorder struct {
	http.ResponseWriter // embedded: all methods promoted, we override one
	status              int
}

func (r *statusRecorder) WriteHeader(code int) {
	r.status = code
	r.ResponseWriter.WriteHeader(code)
}

func writeJSON(w http.ResponseWriter, status int, v any) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(status)
	_ = json.NewEncoder(w).Encode(v)
}

func writeError(w http.ResponseWriter, status int, msg string) {
	writeJSON(w, status, map[string]string{"error": msg})
}

func main() {
	logger := slog.New(slog.NewJSONHandler(os.Stdout, nil))
	srv := &Server{store: NewStore(), log: logger}

	port := os.Getenv("PORT")
	if port == "" {
		port = "8080"
	}
	httpSrv := &http.Server{
		Addr:              ":" + port,
		Handler:           srv.Routes(),
		ReadHeaderTimeout: 5 * time.Second, // never run a server without timeouts
	}

	// Graceful shutdown on Ctrl-C / SIGTERM (what Kubernetes sends).
	ctx, stop := signal.NotifyContext(context.Background(), os.Interrupt, syscall.SIGTERM)
	defer stop()

	go func() {
		logger.Info("listening", "addr", httpSrv.Addr)
		if err := httpSrv.ListenAndServe(); err != nil && !errors.Is(err, http.ErrServerClosed) {
			logger.Error("server failed", "err", err)
			os.Exit(1)
		}
	}()

	<-ctx.Done()
	logger.Info("shutting down, draining in-flight requests")
	shutdownCtx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
	defer cancel()
	if err := httpSrv.Shutdown(shutdownCtx); err != nil {
		logger.Error("shutdown", "err", err)
	}
}
