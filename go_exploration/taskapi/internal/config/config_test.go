package config

import (
	"log/slog"
	"testing"
	"time"
)

func env(m map[string]string) func(string) string {
	return func(k string) string { return m[k] }
}

func TestLoadDefaults(t *testing.T) {
	cfg, err := Load(env(map[string]string{"DATABASE_URL": "postgres://x"}))
	if err != nil {
		t.Fatal(err)
	}
	if cfg.Port != "8080" || cfg.LogLevel != slog.LevelInfo || cfg.ShutdownTimeout != 10*time.Second {
		t.Fatalf("unexpected defaults: %+v", cfg)
	}
}

func TestLoadErrors(t *testing.T) {
	tests := map[string]map[string]string{
		"missing db url":   {},
		"bad log level":    {"DATABASE_URL": "x", "LOG_LEVEL": "loud"},
		"bad shutdown dur": {"DATABASE_URL": "x", "SHUTDOWN_TIMEOUT": "soon"},
	}
	for name, e := range tests {
		t.Run(name, func(t *testing.T) {
			if _, err := Load(env(e)); err == nil {
				t.Fatal("expected error")
			}
		})
	}
}
