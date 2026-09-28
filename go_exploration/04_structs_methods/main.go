// Chapter 04 -- structs, methods, pointer vs value receivers, embedding.
//
//	go run ./04_structs_methods
package main

import (
	"encoding/json"
	"fmt"
	"time"
)

// Struct tags drive encoding/json (and yaml, db, validate, ...).
type Pod struct {
	Name      string            `json:"name"`
	Namespace string            `json:"namespace"`
	Labels    map[string]string `json:"labels,omitempty"`
	Restarts  int               `json:"restarts"`
	internal  string            // lowercase: invisible to json (and other packages)
}

// Value receiver: works on a COPY. Fine for reading.
func (p Pod) FullName() string { return p.Namespace + "/" + p.Name }

// Pointer receiver: can mutate, and avoids copying large structs.
func (p *Pod) Restart() { p.Restarts++ }

// Constructor convention: NewX returns a ready-to-use value.
func NewPod(ns, name string) *Pod {
	return &Pod{Name: name, Namespace: ns, Labels: map[string]string{}}
}

// --- Embedding: composition, not inheritance --------------------------------

type Metadata struct {
	CreatedAt time.Time
	Owner     string
}

func (m Metadata) Age(now time.Time) time.Duration { return now.Sub(m.CreatedAt) }

type Deployment struct {
	Metadata // embedded: fields and methods are PROMOTED
	Name     string
	Replicas int
}

// Scale is on *Deployment; the `Metadata` inside is reached as d.Owner or d.Metadata.Owner.
func (d *Deployment) Scale(n int) error {
	if n < 0 {
		return fmt.Errorf("replicas must be >= 0, got %d", n)
	}
	d.Replicas = n
	return nil
}

func main() {
	p := Pod{Name: "web-1", Namespace: "prod"} // unset fields get zero values
	p.Restart()                                // Go auto-takes &p for pointer methods
	fmt.Println(p.FullName(), "restarts:", p.Restarts)

	// Value copy vs pointer alias
	cp := p
	cp.Name = "copy"
	ptr := &p
	ptr.Name = "via-pointer"
	fmt.Println("p:", p.Name, "| cp:", cp.Name)

	// Anonymous struct -- handy for one-off data / test tables
	point := struct{ X, Y int }{1, 2}
	fmt.Printf("%+v\n", point)

	// Structs of comparable fields are comparable
	type Key struct{ NS, Name string }
	seen := map[Key]bool{{"prod", "web"}: true}
	fmt.Println("struct as map key:", seen[Key{"prod", "web"}])

	// JSON round trip using the struct tags
	np := NewPod("dev", "api-0")
	np.Labels["app"] = "api"
	np.internal = "hidden"
	b, _ := json.Marshal(np)
	fmt.Println("json:", string(b))
	var back Pod
	_ = json.Unmarshal([]byte(`{"name":"db-0","namespace":"data","restarts":3}`), &back)
	fmt.Printf("decoded: %+v\n", back)

	// Embedding
	d := Deployment{
		Metadata: Metadata{CreatedAt: time.Now().Add(-90 * time.Minute), Owner: "platform"},
		Name:     "checkout",
	}
	_ = d.Scale(3)
	fmt.Printf("%s owner=%s replicas=%d age=%s\n",
		d.Name, d.Owner, d.Replicas, d.Age(time.Now()).Round(time.Minute))
	fmt.Println("scale error:", d.Scale(-1))
}
