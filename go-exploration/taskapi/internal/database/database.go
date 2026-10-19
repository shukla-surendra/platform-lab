// Package database owns the Postgres connection pool and schema migrations.
package database

import (
	"context"
	"embed"
	"fmt"
	"log/slog"
	"time"

	"github.com/jackc/pgx/v5/pgxpool"
	"github.com/jackc/pgx/v5/stdlib"
	"github.com/pressly/goose/v3"
)

// The SQL files are compiled INTO the binary -- no need to ship them
// separately or mount them into the container.
//
//go:embed migrations/*.sql
var migrationsFS embed.FS

// Connect opens a pool and waits (with backoff) until Postgres answers.
// Retrying matters in docker compose / k8s, where the API often starts
// before the database is ready.
func Connect(ctx context.Context, url string, log *slog.Logger) (*pgxpool.Pool, error) {
	cfg, err := pgxpool.ParseConfig(url)
	if err != nil {
		return nil, fmt.Errorf("parse database url: %w", err)
	}
	cfg.MaxConns = 10
	cfg.MaxConnIdleTime = 5 * time.Minute

	pool, err := pgxpool.NewWithConfig(ctx, cfg)
	if err != nil {
		return nil, fmt.Errorf("create pool: %w", err)
	}

	backoff := 200 * time.Millisecond
	for attempt := 1; ; attempt++ {
		pingCtx, cancel := context.WithTimeout(ctx, 2*time.Second)
		err = pool.Ping(pingCtx)
		cancel()
		if err == nil {
			return pool, nil
		}
		if attempt == 8 {
			pool.Close()
			return nil, fmt.Errorf("database not reachable after %d attempts: %w", attempt, err)
		}
		log.Warn("database not ready, retrying", "attempt", attempt, "in", backoff, "err", err)
		select {
		case <-time.After(backoff):
			backoff = min(backoff*2, 5*time.Second)
		case <-ctx.Done():
			pool.Close()
			return nil, ctx.Err()
		}
	}
}

// Migrate applies any pending migrations. goose records applied versions in
// the goose_db_version table, so this is safe to run on every start.
func Migrate(ctx context.Context, pool *pgxpool.Pool) error {
	db := stdlib.OpenDBFromPool(pool) // goose wants database/sql
	defer db.Close()

	goose.SetBaseFS(migrationsFS)
	goose.SetLogger(goose.NopLogger())
	if err := goose.SetDialect("postgres"); err != nil {
		return err
	}
	if err := goose.UpContext(ctx, db, "migrations"); err != nil {
		return fmt.Errorf("migrate: %w", err)
	}
	return nil
}
