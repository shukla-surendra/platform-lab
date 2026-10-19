package task

import (
	"context"
	"errors"
	"strings"
	"testing"
	"time"
)

var fixedNow = time.Date(2026, 1, 15, 12, 0, 0, 0, time.UTC)

func newTestService() *Service {
	s := NewService(NewMemoryRepository())
	s.now = func() time.Time { return fixedNow }
	return s
}

// fieldErrors returns the ValidationError fields, failing the test if err isn't one.
func fieldErrors(t *testing.T, err error) map[string]string {
	t.Helper()
	var ve *ValidationError
	if !errors.As(err, &ve) {
		t.Fatalf("want *ValidationError, got %T: %v", err, err)
	}
	return ve.Fields
}

func TestCreateValidation(t *testing.T) {
	past := fixedNow.Add(-time.Hour)
	tests := []struct {
		name      string
		in        CreateInput
		wantField string
	}{
		{"empty title", CreateInput{Title: "   "}, "title"},
		{"title too long", CreateInput{Title: strings.Repeat("x", 201)}, "title"},
		{"priority too high", CreateInput{Title: "ok", Priority: 9}, "priority"},
		{"due in past", CreateInput{Title: "ok", DueAt: &past}, "due_at"},
	}
	for _, tc := range tests {
		t.Run(tc.name, func(t *testing.T) {
			_, err := newTestService().Create(context.Background(), tc.in)
			if _, ok := fieldErrors(t, err)[tc.wantField]; !ok {
				t.Fatalf("expected error on %q, got %v", tc.wantField, err)
			}
		})
	}
}

func TestCreateReportsAllFieldsAtOnce(t *testing.T) {
	_, err := newTestService().Create(context.Background(), CreateInput{Title: "", Priority: 7})
	if f := fieldErrors(t, err); len(f) != 2 {
		t.Fatalf("want 2 field errors, got %v", f)
	}
}

func TestCreateDefaultsAndTrims(t *testing.T) {
	got, err := newTestService().Create(context.Background(), CreateInput{Title: "  ship it  "})
	if err != nil {
		t.Fatal(err)
	}
	if got.Title != "ship it" || got.Priority != DefaultPriority {
		t.Fatalf("got %+v", got)
	}
}

func TestListPagination(t *testing.T) {
	s := newTestService()
	ctx := context.Background()

	page, err := s.List(ctx, ListFilter{})
	if err != nil {
		t.Fatal(err)
	}
	if page.Limit != DefaultLimit || page.Items == nil {
		t.Fatalf("defaults: %+v (items must be [] not nil)", page)
	}

	page, _ = s.List(ctx, ListFilter{Limit: 10_000})
	if page.Limit != MaxLimit {
		t.Fatalf("limit not clamped: %d", page.Limit)
	}

	bad := Status("archived")
	_, err = s.List(ctx, ListFilter{Status: &bad, Offset: -1})
	if f := fieldErrors(t, err); f["status"] == "" || f["offset"] == "" {
		t.Fatalf("got %v", f)
	}
}

func TestUpdateValidation(t *testing.T) {
	s := newTestService()
	ctx := context.Background()
	created, _ := s.Create(ctx, CreateInput{Title: "t"})

	_, err := s.Update(ctx, created.ID, UpdateInput{})
	if fieldErrors(t, err)["body"] == "" {
		t.Fatal("empty update should be rejected")
	}

	bad := Status("blocked")
	_, err = s.Update(ctx, created.ID, UpdateInput{Status: &bad})
	if fieldErrors(t, err)["status"] == "" {
		t.Fatal("invalid status should be rejected")
	}

	done := StatusDone
	got, err := s.Update(ctx, created.ID, UpdateInput{Status: &done})
	if err != nil || got.Status != StatusDone {
		t.Fatalf("got %+v, %v", got, err)
	}
}
