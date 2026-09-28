# 12 · Capstone: a concurrent health-check CLI

```bash
go run ./12_cli_tool https://go.dev https://example.com https://httpbin.org/status/503
go run ./12_cli_tool -json -timeout 500ms https://go.dev
echo $?                                   # 0 = all healthy, 1 = something down, 2 = usage error

go build -o bin/healthcheck ./12_cli_tool
./bin/healthcheck -h
go test ./12_cli_tool                     # no internet needed: uses httptest fakes
```

This chapter pulls together everything from earlier chapters:

| Concept | Where in `main.go` | Chapter |
|---|---|---|
| struct + JSON tags | `Result` | 04 |
| error values → message field | `Check` | 06 |
| goroutines + WaitGroup + semaphore | `CheckAll` | 08 |
| per-request `context.WithTimeout` | `Check` | 09 |
| table tests + `httptest` fakes | `main_test.go` | 10, 11 |
| `io.Writer` for output | `run(args, stdout, stderr)` | 05 |

## The `run()` pattern

```go
func main() { os.Exit(run(os.Args[1:], os.Stdout, os.Stderr)) }
```

Keep `main` down to one line. Put everything in `run`, which takes args
and writers and **returns** an exit code. Tests can then call `run` with
fake args and `bytes.Buffer`s and assert on output and exit codes, without
spawning a process or calling `os.Exit` inside a test.

## Why no lock on `results`?

Each goroutine writes to **its own index** `results[i]`. Different elements
of a slice are different memory locations, so there's no data race.
`wg.Wait()` guarantees every write is visible before we read. Verify it with
`go test -race`.

## Flags

The stdlib `flag` package handles `-timeout 500ms` (parsed straight into a
`time.Duration`), `-json`, and `-h`. For git-style subcommands
(`tool get pods`), most Go CLIs use `github.com/spf13/cobra`, the library
behind `kubectl`, `helm`, and `gh`.

## Distribute

```bash
GOOS=linux  GOARCH=amd64 go build -o bin/healthcheck-linux   ./12_cli_tool
GOOS=darwin GOARCH=arm64 go build -o bin/healthcheck-mac     ./12_cli_tool
GOOS=windows GOARCH=amd64 go build -o bin/healthcheck.exe    ./12_cli_tool
```

Cross-compiling is just two environment variables, and the output is a
single binary with no runtime to install.

## Try it

1. Add `-retries N` with exponential backoff (`time.Sleep(100ms << attempt)`).
2. Read URLs from stdin when no args are given: `cat urls.txt | healthcheck`.
3. Add `-watch 10s` to re-check on a ticker until Ctrl-C (`signal.NotifyContext`, from chapter 11).
