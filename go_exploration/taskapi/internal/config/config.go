// Package config loads runtime configuration from environment variables
// (12-factor style): the same binary runs locally, in Docker, and in k8s.
package config

import (
	"errors"
	"fmt"
	"log/slog"
	"os"
	"time"
)

type Config struct {
	Port            string
	DatabaseURL     string
	LogLevel        slog.Level
	ShutdownTimeout time.Duration
}

// Load reads the environment. getenv is injected so tests don't touch the
// real process environment.
func Load(getenv func(string) string) (Config, error) {
	cfg := Config{
		Port:            valueOr(getenv("PORT"), "8080"),
		DatabaseURL:     getenv("DATABASE_URL"),
		ShutdownTimeout: 10 * time.Second,
	}
	if cfg.DatabaseURL == "" {
		return Config{}, errors.New("DATABASE_URL is required")
	}
	if err := cfg.LogLevel.UnmarshalText([]byte(valueOr(getenv("LOG_LEVEL"), "info"))); err != nil {
		return Config{}, fmt.Errorf("LOG_LEVEL: %w", err)
	}
	if v := getenv("SHUTDOWN_TIMEOUT"); v != "" {
		d, err := time.ParseDuration(v)
		if err != nil {
			return Config{}, fmt.Errorf("SHUTDOWN_TIMEOUT: %w", err)
		}
		cfg.ShutdownTimeout = d
	}
	return cfg, nil
}

// FromEnv is Load against the real environment.
func FromEnv() (Config, error) { return Load(os.Getenv) }

func valueOr(v, def string) string {
	if v == "" {
		return def
	}
	return v
}
