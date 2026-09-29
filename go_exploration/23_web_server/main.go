// Lesson 23: A Web Server
//
// Run it with:  go run ./23_web_server
// Then, in another terminal:
//
//	curl localhost:8080/hello
//	curl -X POST localhost:8080/notes -d '{"text":"buy milk"}'
//	curl localhost:8080/notes
//
// Press Ctrl+C to stop the server.
package main

import (
	"encoding/json"
	"fmt"
	"log"
	"net/http"
	"strconv"
	"sync"
)

// Note is what we store. The `json:"..."` tags name the JSON fields.
type Note struct {
	ID   int    `json:"id"`
	Text string `json:"text"`
}

// NoteStore keeps notes in memory. The mutex keeps it safe,
// because every request runs in its own goroutine.
type NoteStore struct {
	mu     sync.Mutex
	notes  []Note
	nextID int
}

func (s *NoteStore) Add(text string) Note {
	s.mu.Lock()
	defer s.mu.Unlock()
	s.nextID++
	note := Note{ID: s.nextID, Text: text}
	s.notes = append(s.notes, note)
	return note
}

func (s *NoteStore) All() []Note {
	s.mu.Lock()
	defer s.mu.Unlock()
	result := make([]Note, len(s.notes)) // give back a copy, not our own slice
	copy(result, s.notes)
	return result
}

func (s *NoteStore) Get(id int) (Note, bool) {
	s.mu.Lock()
	defer s.mu.Unlock()
	for _, n := range s.notes {
		if n.ID == id {
			return n, true
		}
	}
	return Note{}, false
}

// writeJSON sends any value as JSON with a status code.
func writeJSON(w http.ResponseWriter, status int, value any) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(status)
	json.NewEncoder(w).Encode(value)
}

func main() {
	store := &NoteStore{}

	// GET /hello -> plain text
	http.HandleFunc("GET /hello", func(w http.ResponseWriter, r *http.Request) {
		fmt.Fprintln(w, "Hello from Go!")
	})

	// GET /hello/{name} -> a value from the path
	http.HandleFunc("GET /hello/{name}", func(w http.ResponseWriter, r *http.Request) {
		name := r.PathValue("name")
		fmt.Fprintf(w, "Hello, %s!\n", name)
	})

	// GET /notes -> list all notes as JSON
	http.HandleFunc("GET /notes", func(w http.ResponseWriter, r *http.Request) {
		writeJSON(w, http.StatusOK, store.All())
	})

	// GET /notes/{id} -> one note, or 404
	http.HandleFunc("GET /notes/{id}", func(w http.ResponseWriter, r *http.Request) {
		id, err := strconv.Atoi(r.PathValue("id"))
		if err != nil {
			http.Error(w, "id must be a number", http.StatusBadRequest)
			return
		}
		note, found := store.Get(id)
		if !found {
			http.Error(w, "note not found", http.StatusNotFound)
			return
		}
		writeJSON(w, http.StatusOK, note)
	})

	// POST /notes -> read JSON, create a note
	http.HandleFunc("POST /notes", func(w http.ResponseWriter, r *http.Request) {
		var input Note
		if err := json.NewDecoder(r.Body).Decode(&input); err != nil {
			http.Error(w, "bad JSON", http.StatusBadRequest)
			return
		}
		note := store.Add(input.Text)
		writeJSON(w, http.StatusCreated, note)
	})

	fmt.Println("Server running on http://localhost:8080  (Ctrl+C to stop)")
	fmt.Println("Try:  curl localhost:8080/hello")
	// ListenAndServe runs forever. If it can't start (for example, the port is
	// already in use), it returns an error and log.Fatal prints it and exits.
	log.Fatal(http.ListenAndServe(":8080", nil))
}
