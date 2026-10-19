package task

import (
	"context"
	"errors"
	"fmt"

	"github.com/jackc/pgx/v5"
	"github.com/jackc/pgx/v5/pgxpool"
)

// PostgresRepository implements Repository with plain SQL via pgx.
// No ORM: the queries are right here, easy to read and EXPLAIN.
type PostgresRepository struct {
	pool *pgxpool.Pool
}

func NewPostgresRepository(pool *pgxpool.Pool) *PostgresRepository {
	return &PostgresRepository{pool: pool}
}

// Compile-time check that we satisfy the interface.
var _ Repository = (*PostgresRepository)(nil)

const columns = `id, title, description, status, priority, due_at, created_at, updated_at`

func (r *PostgresRepository) Create(ctx context.Context, in CreateInput) (Task, error) {
	rows, _ := r.pool.Query(ctx, `
		INSERT INTO tasks (title, description, priority, due_at)
		VALUES ($1, $2, $3, $4)
		RETURNING `+columns,
		in.Title, in.Description, in.Priority, in.DueAt)
	t, err := pgx.CollectExactlyOneRow(rows, pgx.RowToStructByName[Task])
	if err != nil {
		return Task{}, fmt.Errorf("insert task: %w", err)
	}
	return t, nil
}

func (r *PostgresRepository) Get(ctx context.Context, id int64) (Task, error) {
	rows, _ := r.pool.Query(ctx, `SELECT `+columns+` FROM tasks WHERE id = $1`, id)
	t, err := pgx.CollectExactlyOneRow(rows, pgx.RowToStructByName[Task])
	if errors.Is(err, pgx.ErrNoRows) {
		return Task{}, ErrNotFound // translate driver error -> domain error
	}
	if err != nil {
		return Task{}, fmt.Errorf("get task %d: %w", id, err)
	}
	return t, nil
}

func (r *PostgresRepository) List(ctx context.Context, f ListFilter) ([]Task, int, error) {
	// ($1::text IS NULL OR status = $1) makes the filter optional without
	// building SQL strings by hand (which is how SQL injection happens).
	var total int
	if err := r.pool.QueryRow(ctx,
		`SELECT count(*) FROM tasks WHERE ($1::text IS NULL OR status = $1)`, f.Status,
	).Scan(&total); err != nil {
		return nil, 0, fmt.Errorf("count tasks: %w", err)
	}

	rows, _ := r.pool.Query(ctx, `
		SELECT `+columns+` FROM tasks
		WHERE ($1::text IS NULL OR status = $1)
		ORDER BY created_at DESC, id DESC
		LIMIT $2 OFFSET $3`,
		f.Status, f.Limit, f.Offset)
	items, err := pgx.CollectRows(rows, pgx.RowToStructByName[Task])
	if err != nil {
		return nil, 0, fmt.Errorf("list tasks: %w", err)
	}
	return items, total, nil
}

func (r *PostgresRepository) Update(ctx context.Context, id int64, in UpdateInput) (Task, error) {
	// COALESCE(new, old): a nil pointer becomes SQL NULL and keeps the old value.
	rows, _ := r.pool.Query(ctx, `
		UPDATE tasks SET
			title       = COALESCE($2, title),
			description = COALESCE($3, description),
			status      = COALESCE($4, status),
			priority    = COALESCE($5, priority),
			due_at      = COALESCE($6, due_at),
			updated_at  = now()
		WHERE id = $1
		RETURNING `+columns,
		id, in.Title, in.Description, in.Status, in.Priority, in.DueAt)
	t, err := pgx.CollectExactlyOneRow(rows, pgx.RowToStructByName[Task])
	if errors.Is(err, pgx.ErrNoRows) {
		return Task{}, ErrNotFound
	}
	if err != nil {
		return Task{}, fmt.Errorf("update task %d: %w", id, err)
	}
	return t, nil
}

func (r *PostgresRepository) Delete(ctx context.Context, id int64) error {
	tag, err := r.pool.Exec(ctx, `DELETE FROM tasks WHERE id = $1`, id)
	if err != nil {
		return fmt.Errorf("delete task %d: %w", id, err)
	}
	if tag.RowsAffected() == 0 {
		return ErrNotFound
	}
	return nil
}
