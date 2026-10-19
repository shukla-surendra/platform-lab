// Command api is the task API server. main.go is the "composition root":
// it reads config, builds every dependency, wires them together, and owns
// the process lifecycle. No business logic lives here.
package main

import (
	"context"
	"errors"
	"fmt"
	"log/slog"
	"net"
	"net/http"
	"os"
	"os/signal"
	"syscall"
	"time"

	"platformlab/taskapi/internal/config"
	"platformlab/taskapi/internal/database"
	"platformlab/taskapi/internal/httpapi"
	"platformlab/taskapi/internal/task"
)

// Set at build time: go build -ldflags "-X main.version=$(git describe --always)"
var version = "dev"

func main() {
	if err := run(); err != nil {
		fmt.Fprintln(os.Stderr, "fatal:", err)
		os.Exit(1)
	}
}

func run() error {
	// Cancelled on Ctrl-C or SIGTERM (what `docker stop` and Kubernetes send).
	ctx, stop := signal.NotifyContext(context.Background(), os.Interrupt, syscall.SIGTERM)
	defer stop()

	cfg, err := config.FromEnv()
	if err != nil {
		return err
	}
	log := slog.New(slog.NewJSONHandler(os.Stdout, &slog.HandlerOptions{Level: cfg.LogLevel}))
	log.Info("starting", "version", version, "port", cfg.Port)

	// --- Dependencies, innermost first ---------------------------------------
	pool, err := database.Connect(ctx, cfg.DatabaseURL, log)
	if err != nil {
		return err
	}
	defer pool.Close()

	if err := database.Migrate(ctx, pool); err != nil {
		return err
	}
	log.Info("migrations applied")

	repo := task.NewPostgresRepository(pool)
	svc := task.NewService(repo)
	api := httpapi.New(svc, pool, log)

	srv := &http.Server{
		Addr:              net.JoinHostPort("", cfg.Port),
		Handler:           api.Handler(),
		ReadHeaderTimeout: 5 * time.Second,
		ReadTimeout:       15 * time.Second,
		WriteTimeout:      15 * time.Second,
		IdleTimeout:       60 * time.Second,
		// Every request context derives from ctx, so shutdown cancels in-flight DB queries.
		BaseContext: func(net.Listener) context.Context { return ctx },
	}

	// --- Serve until signalled -------------------------------------------------
	errCh := make(chan error, 1)
	go func() {
		log.Info("listening", "addr", srv.Addr)
		errCh <- srv.ListenAndServe()
	}()

	select {
	case err := <-errCh:
		if !errors.Is(err, http.ErrServerClosed) {
			return fmt.Errorf("server: %w", err)
		}
	case <-ctx.Done():
		log.Info("shutdown signal received, draining connections", "timeout", cfg.ShutdownTimeout.String())
	}

	shutdownCtx, cancel := context.WithTimeout(context.Background(), cfg.ShutdownTimeout)
	defer cancel()
	if err := srv.Shutdown(shutdownCtx); err != nil {
		return fmt.Errorf("shutdown: %w", err)
	}
	log.Info("stopped cleanly")
	return nil
}
