package task

import (
	"context"
	"io"
	"log/slog"
	"os"
	"testing"

	"platformlab/taskapi/internal/database"
)

// Integration test: runs the same contract against a real Postgres.
// Skipped unless TEST_DATABASE_URL is set -- `make test-integration` sets it.
func TestPostgresRepository(t *testing.T) {
	url := os.Getenv("TEST_DATABASE_URL")
	if url == "" {
		t.Skip("TEST_DATABASE_URL not set; run `make test-integration`")
	}
	ctx := context.Background()
	pool, err := database.Connect(ctx, url, slog.New(slog.NewTextHandler(io.Discard, nil)))
	if err != nil {
		t.Fatal(err)
	}
	t.Cleanup(pool.Close)
	if err := database.Migrate(ctx, pool); err != nil {
		t.Fatal(err)
	}

	runRepositoryContract(t, func(t *testing.T) Repository {
		// Each subtest starts from an empty table.
		if _, err := pool.Exec(ctx, `TRUNCATE tasks RESTART IDENTITY`); err != nil {
			t.Fatal(err)
		}
		return NewPostgresRepository(pool)
	})
}
