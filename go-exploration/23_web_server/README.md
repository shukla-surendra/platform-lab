# Lesson 23: A Web Server

**You will learn:** how to build a small web API that other programs (or your browser) can talk to.

```bash
go run ./23_web_server
# Server stays running. Press Ctrl+C to stop it.
```

---

## How the web works (in 20 seconds)

```
  browser / curl  ──── request:  GET /hello ────►  your Go server
                  ◄─── response: "Hello!"    ────
```

- The **client** (browser, phone app, `curl`) sends a **request**: a method (`GET`, `POST`, …) and a path (`/hello`).
- The **server** (your Go program) sends back a **response**: some text or JSON, and a status code (`200` = OK, `404` = not found).

Go has everything built in, in the `net/http` package. You don't need to install a framework.

## Step 1: The smallest server

```go
package main

import (
	"fmt"
	"net/http"
)

func hello(w http.ResponseWriter, r *http.Request) {
	fmt.Fprintln(w, "Hello from Go!")
}

func main() {
	http.HandleFunc("GET /hello", hello)
	http.ListenAndServe(":8080", nil)
}
```

| Code | Meaning |
|---|---|
| `func hello(w, r)` | a **handler**: the function that runs for a request |
| `w http.ResponseWriter` | where you **write** your answer |
| `r *http.Request` | everything about the **request** (path, body, …) |
| `http.HandleFunc("GET /hello", hello)` | "when someone does GET /hello, run `hello`" |
| `http.ListenAndServe(":8080", nil)` | start the server on port 8080 and wait forever |

`fmt.Fprintln(w, ...)` is like `Println`, but it writes into `w` (the response) instead of the screen.

Try it: open http://localhost:8080/hello in your browser, or run:

```bash
curl localhost:8080/hello
```

## Step 2: Values in the path

```go
http.HandleFunc("GET /hello/{name}", func(w http.ResponseWriter, r *http.Request) {
	name := r.PathValue("name")
	fmt.Fprintf(w, "Hello, %s!\n", name)
})
```

```bash
curl localhost:8080/hello/Asha      # Hello, Asha!
```

## Step 3: Sending JSON

APIs usually talk in **JSON**, like this: `{"id": 1, "text": "buy milk"}`.

Go turns a struct into JSON for you. Add **tags** to name the JSON fields:

```go
type Note struct {
	ID   int    `json:"id"`
	Text string `json:"text"`
}
```

The `` `json:"id"` `` part is a **tag**. It means *"in JSON, call this field `id`"*.

Send it:

```go
w.Header().Set("Content-Type", "application/json")
json.NewEncoder(w).Encode(note)     // struct -> JSON
```

## Step 4: Receiving JSON (POST)

```go
var input Note
err := json.NewDecoder(r.Body).Decode(&input)    // JSON -> struct
if err != nil {
	http.Error(w, "bad JSON", http.StatusBadRequest)   // 400
	return
}
```

## Step 5: Keeping data safe

Go runs **each request in its own goroutine**. Many users can be adding notes at the same time.
So our list of notes needs a **mutex** (Lesson 20). You can see it in `main.go`.

## Try the full notes API

Start the server in one terminal:

```bash
go run ./23_web_server
```

In another terminal:

```bash
curl localhost:8080/hello
curl localhost:8080/hello/Ravi

curl -X POST localhost:8080/notes -d '{"text":"buy milk"}'
curl -X POST localhost:8080/notes -d '{"text":"learn go"}'

curl localhost:8080/notes             # list all notes
curl localhost:8080/notes/1           # get one note
curl -i localhost:8080/notes/99       # 404 Not Found (-i shows the status line)
curl -i -X POST localhost:8080/notes -d 'oops'   # 400 Bad Request
```

## Common status codes

| Code | Name | When |
|---|---|---|
| 200 | OK | everything fine |
| 201 | Created | a new thing was created (after POST) |
| 400 | Bad Request | the client sent wrong data |
| 404 | Not Found | that thing doesn't exist |
| 500 | Internal Server Error | a bug or problem on the server |

## Practice

1. Add `GET /time` that returns the current time (`time.Now()`).
2. Add `DELETE /notes/{id}` that removes a note. Return `204 No Content` (`w.WriteHeader(http.StatusNoContent)`).
3. Don't allow empty notes: if `text` is `""`, return `400` with the message `"text is required"`.

## Want to see a real, bigger API?

[`taskapi/`](../taskapi/) is a full project: a Postgres database, a clean folder layout, tests, Docker, and graceful shutdown.
Look at it **after** the final project (Lesson 24).

---

**Next:** [Lesson 24: Final project](../24_final_project/)
