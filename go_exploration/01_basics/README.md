# 01 · Basics: variables, types, control flow

```bash
go run ./01_basics
go test ./01_basics
```

## Declarations

| Form | Where | Example |
|---|---|---|
| `var name T` | anywhere | `var count int` → zero value `0` |
| `var name = v` | anywhere | type inferred |
| `name := v` | inside functions only | most common form |
| `const` | anywhere | compile-time value; can be *untyped* |

**Every type has a zero value**, so there is no "uninitialised" variable:
`0`, `""`, `false`, and `nil` for pointers, slices, maps, channels,
functions, and interfaces. Idiomatic Go leans on this. A zero-value
`sync.Mutex` or `bytes.Buffer` is ready to use.

Unused local variables and unused imports are **compile errors**, not warnings.

## Types worth knowing

- `int`, `int64`, `uint8` (= `byte`), `int32` (= `rune`), `float64`, `bool`, `string`
- **No implicit numeric conversion.** `float64(i)` is required, even for `int` → `int64`.
- Integer overflow wraps silently (`int8(127)+1 == -128`).
- `string` is an immutable sequence of **bytes**, not characters.
  `len(s)` counts bytes, and `for _, r := range s` iterates **runes**
  (Unicode code points), decoding UTF-8 as it goes.

## Constants and `iota`

```go
type Weekday int
const (
    Sunday Weekday = iota // 0
    Monday                // 1
)
```

Go has no `enum` keyword. A named type plus `iota` gives you one.

## Control flow

- **`for` is the only loop**: `for i := 0; i < n; i++`, `for cond {}`, `for {}`,
  `for i, v := range xs`, and since 1.22 `for i := range 10`.
- **`if` and `switch` take an init statement**: `if err := f(); err != nil { ... }`.
  The variable is scoped to that block. This pattern shows up everywhere.
- **`switch` does not fall through.** Cases can list several values, and a
  tagless `switch { case x > 0: ... }` replaces if/else-if chains.
- **Labeled `break`/`continue`** escape nested loops.

## Visibility

A capitalised name (`FizzBuzz`) is **exported**, meaning it's visible
outside the package. A lowercase name is package-private. There are no
`public`/`private` keywords.

## Try it

1. Change `small++` to use `int16` and predict the output.
2. Iterate `"世界"` with a classic `for i := 0; i < len(s); i++` loop and print `s[i]`. Why is it garbage?
