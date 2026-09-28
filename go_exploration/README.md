# go_exploration

A hands-on Go tutorial in 12 chapters. It goes from syntax to a production-shaped
HTTP API and a concurrent CLI. Each chapter is a folder with a
`README.md` (the tutorial text), a runnable `main.go` full of commented
examples, and tests you can break on purpose.

Standard library only: no third-party dependencies to install.

## Setup

```bash
brew install go        # tested with go1.27.1
cd go_exploration
go test ./...          # everything should pass
```

The whole folder is **one Go module** (`go.mod` → `platformlab/go_exploration`).
Each chapter is its own package, run by path:

```bash
go run ./01_basics
go test ./01_basics
go test -v -run TestSlugify ./10_testing
go test -race ./...    # use this for 08, 09, 11, 12
```

## Chapters

| # | Chapter | You'll learn |
|---|---|---|
| 01 | [Basics](01_basics/) | declarations, zero values, types, strings vs runes, `for`/`if`/`switch`, exported names |
| 02 | [Functions](02_functions/) | multiple returns, variadics, closures, `defer`, `panic`/`recover` |
| 03 | [Slices & maps](03_slices_maps/) | slice header/capacity, the shared-backing-array gotcha, `slices`/`maps` packages |
| 04 | [Structs & methods](04_structs_methods/) | value vs pointer receivers, constructors, JSON tags, embedding |
| 05 | [Interfaces](05_interfaces/) | implicit satisfaction, type switches, `io.Reader`/`io.Writer`, the nil-interface trap |
| 06 | [Errors](06_errors/) | sentinel vs custom errors, `%w` wrapping, `errors.Is`/`As`/`Join` |
| 07 | [Generics](07_generics/) | type parameters, constraints (`any`, `comparable`, `~int`), generic types |
| 08 | [Goroutines & channels](08_goroutines_channels/) | WaitGroup, pipelines, worker pool, `select` + timeouts, leaks |
| 09 | [sync & context](09_sync_context/) | Mutex/RWMutex, atomics, `Once`, cancellation, deadlines |
| 10 | [Testing](10_testing/) | table tests, subtests, helpers, benchmarks, examples, fuzzing |
| 11 | [HTTP server](11_http_server/) | 1.22 routing, JSON API, middleware, graceful shutdown, `httptest` |
| 12 | [Capstone CLI](12_cli_tool/) | concurrent health checker: flags, context, exit codes, cross-compiling |

**Then build something real:** [`taskapi/`](taskapi/) is a production-shaped REST API with
Postgres. It shows project layout, layering, migrations, a testing strategy,
Docker, and graceful shutdown. It's a separate Go module with its own `go.mod`.

Suggested path: 01 → 06 in order (the language), then 08 → 09 together
(concurrency), then 10 → 12 (building real things). 07 fits anywhere after 05.

Every chapter ends with **"Try it"** exercises. Change the code, predict
the output, and run the tests to check.

## Go in one screen (for Python/Rust people)

| Idea | Go's take |
|---|---|
| Classes | none. Structs + methods + interfaces |
| Inheritance | none. Embedding (composition) |
| Exceptions | none. `error` return values; `panic` only for bugs |
| Interfaces | implicit: having the methods is enough |
| Concurrency | goroutines + channels built into the language |
| Memory | garbage-collected; pointers exist, pointer arithmetic doesn't |
| Formatting | `gofmt`, one style, not configurable |
| Build output | one static binary; `GOOS=linux go build` cross-compiles |

## Toolchain cheat sheet

```bash
go mod init <path>     # start a module
go mod tidy            # add/remove deps to match imports
go fmt ./...           # format
go vet ./...           # catch suspicious code (copied locks, bad printf verbs, …)
go test -cover ./...   # tests + coverage
go build -o bin/x ./12_cli_tool
go doc strings.Fields  # stdlib docs in the terminal
```
