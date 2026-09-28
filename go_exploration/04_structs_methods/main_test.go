package main

import (
	"encoding/json"
	"strings"
	"testing"
	"time"
)

func TestPointerReceiverMutates(t *testing.T) {
	p := NewPod("ns", "a")
	p.Restart()
	p.Restart()
	if p.Restarts != 2 {
		t.Fatalf("restarts = %d", p.Restarts)
	}
}

func TestJSONSkipsUnexported(t *testing.T) {
	p := Pod{Name: "x", Namespace: "y", internal: "secret"}
	b, _ := json.Marshal(p)
	if strings.Contains(string(b), "secret") || strings.Contains(string(b), "labels") {
		t.Fatalf("unexpected json %s", b)
	}
}

func TestEmbeddingPromotesMethods(t *testing.T) {
	now := time.Now()
	d := Deployment{Metadata: Metadata{CreatedAt: now.Add(-time.Hour)}}
	if d.Age(now) != time.Hour {
		t.Fatal("promoted Age() wrong")
	}
	if err := d.Scale(-1); err == nil {
		t.Fatal("negative scale should fail")
	}
}
