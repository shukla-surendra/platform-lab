# Lesson 24: Final Project: Website Checker

**You will build:** a command-line tool that checks many websites **at the same time** and prints which ones are up or down.

```bash
go run ./24_final_project
go run ./24_final_project https://go.dev https://github.com https://this-site-does-not-exist.xyz
go run ./24_final_project -timeout 1s https://go.dev
```

Example output:

```
Checking 3 websites (timeout 5s)...

STATUS  TIME     URL
UP      312ms    https://go.dev
UP      420ms    https://github.com
DOWN    15ms     https://this-site-does-not-exist.xyz  (no such host)

2 up, 1 down
```

---

## Every lesson in one program

| Part of the program | Lesson |
|---|---|
| `Result` struct | 11 Structs |
| `checkURL` returns a result, handles errors | 08 Functions, 15 Errors |
| check all sites **at the same time** | 18 Goroutines |
| send results back on a channel | 19 Channels |
| a time limit for each request | 21 Context |
| sort results, count up/down | 09 Slices, 17 Generics (`slices.SortFunc`) |
| `-timeout` flag, exit code | new (see below) |

## Read the code in this order

Open `main.go`. It's split into small, numbered steps:

1. **`Result`**: what we want to know about each website.
2. **`checkURL`**: checks **one** website and returns a `Result`.
3. **`checkAll`**: runs `checkURL` for **every** website at the same time and collects the results.
4. **`printReport`**: prints the table.
5. **`main`**: reads the command-line input and connects everything.

This is how real programs are built: **small functions, each doing one job**, and `main` connects them.

## New thing 1: command-line flags

The `flag` package reads options like `-timeout 2s`:

```go
timeout := flag.Duration("timeout", 5*time.Second, "time limit for each website")
flag.Parse()

// *timeout is the value (it's a pointer, see Lesson 12)
// flag.Args() gives the rest: the list of URLs
```

You get `-help` for free:

```bash
go run ./24_final_project -help
```

## New thing 2: exit codes

When a program finishes, it gives the terminal a number:

- `0` = success
- anything else = something failed

```go
os.Exit(1)   // "some websites were down"
```

Scripts and CI pipelines use this to decide whether something failed. Try:

```bash
go run ./24_final_project https://go.dev; echo "exit code: $?"
```

## New thing 3: building a real program file

```bash
go build -o sitecheck ./24_final_project
./sitecheck https://go.dev
```

Build it for another operating system (Go makes this very easy):

```bash
GOOS=windows GOARCH=amd64 go build -o sitecheck.exe ./24_final_project
GOOS=darwin  GOARCH=arm64 go build -o sitecheck-mac ./24_final_project
```

## Make it your own (challenges)

Go from easy to hard:

1. **Easy:** Print the HTTP status code (200, 404, …) in the table.
2. **Easy:** Count how many are "SLOW" (took more than 1 second) and show it in the summary.
3. **Medium:** Add a `-file urls.txt` flag that reads URLs from a file, one per line. (Hint: `os.ReadFile` + `strings.Split`.)
4. **Medium:** Add a `-watch 30s` flag that repeats the check every 30 seconds. (Hint: `time.NewTicker`.)
5. **Hard:** Limit the program to **3 checks at a time**, even with 100 URLs. (Hint: a buffered channel with 3 slots works as a "ticket counter".)
6. **Hard:** Turn it into a web server (Lesson 23): `GET /check?url=https://go.dev` returns the result as JSON. Then write tests for it (Lesson 22).

---

## 🎉 You finished the course!

**What's next?**

- Study [`taskapi/`](../taskapi/). It's a real-world API with a database, a clean folder layout, tests, and Docker.
- Build something small that **you** need: a to-do CLI, a file organiser, a Slack bot, a Kubernetes helper.
- Read [Effective Go](https://go.dev/doc/effective_go) and try [Go by Example](https://gobyexample.com) for quick recipes.
