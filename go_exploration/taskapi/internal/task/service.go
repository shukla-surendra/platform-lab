package task

import (
	"context"
	"strings"
	"time"
)

const (
	DefaultLimit    = 20
	MaxLimit        = 100
	DefaultPriority = 3
)

// Service holds business rules. Handlers call the Service; the Service calls
// the Repository. Keeping rules here (not in SQL, not in HTTP handlers) means
// they're unit-testable without a database or a server.
type Service struct {
	repo Repository
	now  func() time.Time // injectable clock for deterministic tests
}

func NewService(repo Repository) *Service {
	return &Service{repo: repo, now: time.Now}
}

func (s *Service) Create(ctx context.Context, in CreateInput) (Task, error) {
	in.Title = strings.TrimSpace(in.Title)
	if err := in.validate(s.now()); err != nil {
		return Task{}, err
	}
	if in.Priority == 0 {
		in.Priority = DefaultPriority
	}
	return s.repo.Create(ctx, in)
}

func (s *Service) Get(ctx context.Context, id int64) (Task, error) {
	return s.repo.Get(ctx, id)
}

func (s *Service) List(ctx context.Context, f ListFilter) (Page, error) {
	v := validator{}
	v.check(f.Status == nil || f.Status.Valid(), "status", "unknown status")
	v.check(f.Limit >= 0, "limit", "must be >= 0")
	v.check(f.Offset >= 0, "offset", "must be >= 0")
	if err := v.err(); err != nil {
		return Page{}, err
	}
	if f.Limit == 0 {
		f.Limit = DefaultLimit
	}
	f.Limit = min(f.Limit, MaxLimit)

	items, total, err := s.repo.List(ctx, f)
	if err != nil {
		return Page{}, err
	}
	if items == nil {
		items = []Task{} // JSON [] instead of null
	}
	return Page{Items: items, Total: total, Limit: f.Limit, Offset: f.Offset}, nil
}

func (s *Service) Update(ctx context.Context, id int64, in UpdateInput) (Task, error) {
	if in.Title != nil {
		t := strings.TrimSpace(*in.Title)
		in.Title = &t
	}
	if err := in.validate(); err != nil {
		return Task{}, err
	}
	return s.repo.Update(ctx, id, in)
}

func (s *Service) Delete(ctx context.Context, id int64) error {
	return s.repo.Delete(ctx, id)
}
