# 10 · Testing

```bash
go test ./10_testing                                   # unit + example tests
go test -v -run 'TestSlugify/digits' ./10_testing      # one subtest
go test -bench=. -benchmem ./10_testing                # benchmarks
go test -fuzz=FuzzSlugify -fuzztime=10s ./10_testing   # fuzzing
go test -cover ./...                                   # coverage %
go test -coverprofile=c.out ./10_testing && go tool cover -html=c.out
```

This chapter is a **library package** (`package textutil`, no `main`).
The package name doesn't have to match the folder name.

Testing is built into the toolchain. There's no framework to install.

- Test files end in `_test.go` and are excluded from normal builds.
- `func TestXxx(t *testing.T)` for tests, `BenchmarkXxx(b *testing.B)` for
  benchmarks, `FuzzXxx(f *testing.F)` for fuzz tests, and `ExampleXxx()`
  for runnable docs.
- Tests in the same package (`package textutil`) can see unexported names.
  Use `package textutil_test` to test only the public API.

## The five tools in `slug_test.go`

1. **Table-driven tests + `t.Run` subtests.** One loop covers many cases.
   Each case has a name so you can `-run` it on its own. `t.Parallel()`
   runs the subtests concurrently.
2. **Helpers.** `t.Helper()` makes failure line numbers point at the caller.
   `t.TempDir()` and `t.Cleanup()` handle teardown automatically.
3. **Benchmarks.** `for b.Loop() { ... }`. `-benchmem` shows allocations per op.
4. **Examples.** The `// Output:` comment is **asserted**, and the example
   appears in `go doc` as documentation.
5. **Fuzzing.** The fuzzer mutates seed inputs looking for property
   violations. Any failing input is saved under `testdata/fuzz/` and becomes
   a permanent regression test.

## `t.Error` vs `t.Fatal`

`t.Errorf` records a failure and **keeps going**, so you see every bad case
in a table. `t.Fatalf` stops the current test. Use it when later lines
would be meaningless, for example after a failed setup.

## No assertion library needed

Plain `if got != want { t.Errorf(...) }` is idiomatic. For deep comparisons,
use `slices.Equal`, `maps.Equal`, or `reflect.DeepEqual`, or the popular
third-party `github.com/google/go-cmp` (`cmp.Diff`), which prints readable
diffs.

HTTP handlers get their own test helpers in `net/http/httptest`. See chapter 11.

## Try it

1. Break `Slugify` (remove the `b.Len() > 0` check), then run the tests and the fuzzer.
2. Run the benchmark, change `strings.Builder` to string concatenation `+=`, and compare `-benchmem`.
