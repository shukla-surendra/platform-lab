# 02 · Functions

```bash
go run ./02_functions
go test ./02_functions
```

## Multiple return values

```go
func Divide(a, b int) (int, error)
q, err := Divide(10, 3)
```

This is the foundation of Go error handling (chapter 06). The last return
value is an `error`, and the caller checks it right away. Use `_` to discard
a value you don't need.

**Named results** `(lo, hi int)` are pre-declared variables, and a bare `return`
sends them back. Use them for short functions or when a `defer` has to change
the result (see below). Avoid them elsewhere.

## Variadic functions

`func MinMax(xs ...int)` receives a `[]int`. Call it with `MinMax(1, 2, 3)`, or
spread an existing slice with `MinMax(nums...)`.

## Functions are values, closures capture variables

```go
func Counter() func() int {
    n := 0
    return func() int { n++; return n }
}
```

The inner function captures the **variable** `n`, not a copy of it, so
each `Counter()` call gets its own `n`. Since Go 1.22, each loop iteration
creates a fresh loop variable, so `for i := ...` closures no longer all see
the final value.

## `defer`

- Runs when the surrounding function **returns** (normally or by panic).
- Multiple defers run **LIFO**.
- The deferred call's arguments are evaluated at the `defer` statement. The
  call itself happens later.
- Main use is cleanup placed right next to acquisition:
  ```go
  f, err := os.Open(p)
  if err != nil { return err }
  defer f.Close()
  ```

## `panic` / `recover`

`panic` is for programmer bugs and impossible states, **not** normal errors.
`recover()` stops a panic, but only when it's called inside a deferred
function. Servers use it at the request boundary so one bad request doesn't
crash the process. `net/http` already does this for you.

## Try it

1. Predict the output of `for i := range 3 { defer fmt.Println(i) }`.
2. Make `Counter` accept a `step int` parameter.
