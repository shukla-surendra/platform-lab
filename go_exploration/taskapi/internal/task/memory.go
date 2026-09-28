package task

import (
	"cmp"
	"context"
	"slices"
	"sync"
	"time"
)

// MemoryRepository is an in-memory Repository. It's the fake used by unit
// tests across packages (service, HTTP handlers) so they run in milliseconds
// with no database. It must behave like PostgresRepository -- the shared
// contract test in repository_test.go runs against both.
type MemoryRepository struct {
	mu     sync.Mutex
	nextID int64
	tasks  map[int64]Task
	now    func() time.Time
}

func NewMemoryRepository() *MemoryRepository {
	return &MemoryRepository{nextID: 1, tasks: map[int64]Task{}, now: time.Now}
}

var _ Repository = (*MemoryRepository)(nil)

func (m *MemoryRepository) Create(_ context.Context, in CreateInput) (Task, error) {
	m.mu.Lock()
	defer m.mu.Unlock()
	now := m.now().UTC()
	t := Task{
		ID: m.nextID, Title: in.Title, Description: in.Description,
		Status: StatusTodo, Priority: in.Priority, DueAt: in.DueAt,
		CreatedAt: now, UpdatedAt: now,
	}
	m.tasks[t.ID] = t
	m.nextID++
	return t, nil
}

func (m *MemoryRepository) Get(_ context.Context, id int64) (Task, error) {
	m.mu.Lock()
	defer m.mu.Unlock()
	t, ok := m.tasks[id]
	if !ok {
		return Task{}, ErrNotFound
	}
	return t, nil
}

func (m *MemoryRepository) List(_ context.Context, f ListFilter) ([]Task, int, error) {
	m.mu.Lock()
	defer m.mu.Unlock()
	var all []Task
	for _, t := range m.tasks {
		if f.Status == nil || t.Status == *f.Status {
			all = append(all, t)
		}
	}
	// Same order as the SQL: created_at DESC, id DESC.
	slices.SortFunc(all, func(a, b Task) int {
		if c := b.CreatedAt.Compare(a.CreatedAt); c != 0 {
			return c
		}
		return cmp.Compare(b.ID, a.ID)
	})
	total := len(all)
	start := min(f.Offset, total)
	end := min(start+f.Limit, total)
	return all[start:end], total, nil
}

func (m *MemoryRepository) Update(_ context.Context, id int64, in UpdateInput) (Task, error) {
	m.mu.Lock()
	defer m.mu.Unlock()
	t, ok := m.tasks[id]
	if !ok {
		return Task{}, ErrNotFound
	}
	if in.Title != nil {
		t.Title = *in.Title
	}
	if in.Description != nil {
		t.Description = *in.Description
	}
	if in.Status != nil {
		t.Status = *in.Status
	}
	if in.Priority != nil {
		t.Priority = *in.Priority
	}
	if in.DueAt != nil {
		t.DueAt = in.DueAt
	}
	t.UpdatedAt = m.now().UTC()
	m.tasks[id] = t
	return t, nil
}

func (m *MemoryRepository) Delete(_ context.Context, id int64) error {
	m.mu.Lock()
	defer m.mu.Unlock()
	if _, ok := m.tasks[id]; !ok {
		return ErrNotFound
	}
	delete(m.tasks, id)
	return nil
}
