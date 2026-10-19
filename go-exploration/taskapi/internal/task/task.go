// Package task is the domain: what a task is, what's valid, and the
// operations on it. It knows nothing about HTTP; it knows about storage only
// through the Repository interface.
package task

import (
	"context"
	"errors"
	"fmt"
	"maps"
	"slices"
	"strings"
	"time"
)

type Status string

const (
	StatusTodo       Status = "todo"
	StatusInProgress Status = "in_progress"
	StatusDone       Status = "done"
)

func (s Status) Valid() bool {
	return s == StatusTodo || s == StatusInProgress || s == StatusDone
}

// Task is the entity. `db` tags map columns for pgx.RowToStructByName,
// `json` tags shape the API response.
type Task struct {
	ID          int64      `json:"id"          db:"id"`
	Title       string     `json:"title"       db:"title"`
	Description string     `json:"description" db:"description"`
	Status      Status     `json:"status"      db:"status"`
	Priority    int        `json:"priority"    db:"priority"`
	DueAt       *time.Time `json:"due_at"      db:"due_at"` // pointer = nullable
	CreatedAt   time.Time  `json:"created_at"  db:"created_at"`
	UpdatedAt   time.Time  `json:"updated_at"  db:"updated_at"`
}

type CreateInput struct {
	Title       string     `json:"title"`
	Description string     `json:"description"`
	Priority    int        `json:"priority"` // 0 = use default (3)
	DueAt       *time.Time `json:"due_at"`
}

// UpdateInput is a PATCH: nil pointer = "field not sent, leave it alone".
// This is THE standard Go trick for partial updates.
type UpdateInput struct {
	Title       *string    `json:"title"`
	Description *string    `json:"description"`
	Status      *Status    `json:"status"`
	Priority    *int       `json:"priority"`
	DueAt       *time.Time `json:"due_at"`
}

type ListFilter struct {
	Status *Status
	Limit  int
	Offset int
}

type Page struct {
	Items  []Task `json:"items"`
	Total  int    `json:"total"`
	Limit  int    `json:"limit"`
	Offset int    `json:"offset"`
}

// Repository is what the domain needs from storage. The Postgres
// implementation lives in postgres.go; tests use MemoryRepository.
type Repository interface {
	Create(ctx context.Context, in CreateInput) (Task, error)
	Get(ctx context.Context, id int64) (Task, error)
	List(ctx context.Context, f ListFilter) ([]Task, int, error)
	Update(ctx context.Context, id int64, in UpdateInput) (Task, error)
	Delete(ctx context.Context, id int64) error
}

// ErrNotFound is returned by every Repository when the id doesn't exist.
var ErrNotFound = errors.New("task not found")

// ValidationError lists every bad field at once so clients can fix them all.
type ValidationError struct {
	Fields map[string]string `json:"fields"`
}

func (e *ValidationError) Error() string {
	parts := make([]string, 0, len(e.Fields))
	for _, k := range slices.Sorted(maps.Keys(e.Fields)) {
		parts = append(parts, k+": "+e.Fields[k])
	}
	return "validation failed: " + strings.Join(parts, "; ")
}

// validator accumulates field errors.
type validator map[string]string

func (v validator) check(ok bool, field, msg string) {
	if !ok {
		if _, exists := v[field]; !exists {
			v[field] = msg
		}
	}
}

func (v validator) err() error {
	if len(v) == 0 {
		return nil
	}
	return &ValidationError{Fields: v}
}

func validTitle(s string) bool {
	s = strings.TrimSpace(s)
	return s != "" && len(s) <= 200
}

func (in CreateInput) validate(now time.Time) error {
	v := validator{}
	v.check(validTitle(in.Title), "title", "must be 1-200 characters")
	v.check(in.Priority == 0 || (in.Priority >= 1 && in.Priority <= 5), "priority", "must be between 1 and 5")
	v.check(in.DueAt == nil || in.DueAt.After(now), "due_at", "must be in the future")
	return v.err()
}

func (in UpdateInput) validate() error {
	v := validator{}
	v.check(in.Title == nil || validTitle(*in.Title), "title", "must be 1-200 characters")
	v.check(in.Status == nil || in.Status.Valid(), "status", fmt.Sprintf("must be one of %s, %s, %s", StatusTodo, StatusInProgress, StatusDone))
	v.check(in.Priority == nil || (*in.Priority >= 1 && *in.Priority <= 5), "priority", "must be between 1 and 5")
	v.check(in.Title != nil || in.Description != nil || in.Status != nil || in.Priority != nil || in.DueAt != nil,
		"body", "at least one field is required")
	return v.err()
}
