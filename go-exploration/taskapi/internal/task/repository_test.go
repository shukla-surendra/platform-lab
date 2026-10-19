package task

import (
	"context"
	"errors"
	"testing"
	"time"
)

// runRepositoryContract is ONE test suite that every Repository
// implementation must pass. Running it against both MemoryRepository and
// PostgresRepository guarantees the fake used in unit tests behaves like the
// real thing.
func runRepositoryContract(t *testing.T, newRepo func(t *testing.T) Repository) {
	ctx := context.Background()
	ptr := func(s string) *string { return &s }

	t.Run("create sets defaults and timestamps", func(t *testing.T) {
		r := newRepo(t)
		due := time.Now().Add(48 * time.Hour).UTC().Truncate(time.Microsecond)
		got, err := r.Create(ctx, CreateInput{Title: "write tests", Priority: 2, DueAt: &due})
		if err != nil {
			t.Fatal(err)
		}
		if got.ID == 0 || got.Status != StatusTodo || got.Priority != 2 || got.CreatedAt.IsZero() {
			t.Fatalf("unexpected task: %+v", got)
		}
		if got.DueAt == nil || !got.DueAt.Equal(due) {
			t.Fatalf("due_at = %v want %v", got.DueAt, due)
		}
	})

	t.Run("get missing returns ErrNotFound", func(t *testing.T) {
		if _, err := newRepo(t).Get(ctx, 999999); !errors.Is(err, ErrNotFound) {
			t.Fatalf("err = %v", err)
		}
	})

	t.Run("list filters, orders newest first, paginates", func(t *testing.T) {
		r := newRepo(t)
		var ids []int64
		for _, title := range []string{"a", "b", "c", "d"} {
			tk, err := r.Create(ctx, CreateInput{Title: title, Priority: 3})
			if err != nil {
				t.Fatal(err)
			}
			ids = append(ids, tk.ID)
		}
		done := StatusDone
		if _, err := r.Update(ctx, ids[1], UpdateInput{Status: &done}); err != nil {
			t.Fatal(err)
		}

		items, total, err := r.List(ctx, ListFilter{Limit: 2, Offset: 0})
		if err != nil {
			t.Fatal(err)
		}
		if total != 4 || len(items) != 2 || items[0].Title != "d" || items[1].Title != "c" {
			t.Fatalf("page 1: total=%d items=%+v", total, items)
		}

		items, _, _ = r.List(ctx, ListFilter{Limit: 2, Offset: 2})
		if len(items) != 2 || items[0].Title != "b" {
			t.Fatalf("page 2: %+v", items)
		}

		items, total, _ = r.List(ctx, ListFilter{Status: &done, Limit: 10})
		if total != 1 || len(items) != 1 || items[0].ID != ids[1] {
			t.Fatalf("status filter: total=%d %+v", total, items)
		}
	})

	t.Run("update is partial", func(t *testing.T) {
		r := newRepo(t)
		orig, _ := r.Create(ctx, CreateInput{Title: "orig", Description: "keep me", Priority: 4})
		got, err := r.Update(ctx, orig.ID, UpdateInput{Title: ptr("renamed")})
		if err != nil {
			t.Fatal(err)
		}
		if got.Title != "renamed" || got.Description != "keep me" || got.Priority != 4 || got.Status != StatusTodo {
			t.Fatalf("partial update clobbered fields: %+v", got)
		}
		if !got.UpdatedAt.After(orig.UpdatedAt) && !got.UpdatedAt.Equal(orig.UpdatedAt) {
			t.Fatalf("updated_at went backwards")
		}
	})

	t.Run("update and delete missing return ErrNotFound", func(t *testing.T) {
		r := newRepo(t)
		if _, err := r.Update(ctx, 999999, UpdateInput{Title: ptr("x")}); !errors.Is(err, ErrNotFound) {
			t.Fatalf("update: %v", err)
		}
		if err := r.Delete(ctx, 999999); !errors.Is(err, ErrNotFound) {
			t.Fatalf("delete: %v", err)
		}
	})

	t.Run("delete removes", func(t *testing.T) {
		r := newRepo(t)
		tk, _ := r.Create(ctx, CreateInput{Title: "temp", Priority: 3})
		if err := r.Delete(ctx, tk.ID); err != nil {
			t.Fatal(err)
		}
		if _, err := r.Get(ctx, tk.ID); !errors.Is(err, ErrNotFound) {
			t.Fatalf("still there: %v", err)
		}
	})
}

func TestMemoryRepository(t *testing.T) {
	runRepositoryContract(t, func(*testing.T) Repository { return NewMemoryRepository() })
}
