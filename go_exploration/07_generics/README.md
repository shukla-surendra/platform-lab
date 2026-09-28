# 07 · Generics

```bash
go run ./07_generics
go test ./07_generics
```

Generics have been in Go since 1.18. Functions and types can take
**type parameters** in square brackets.

```go
func Map[T, U any](xs []T, fn func(T) U) []U
squares := Map(nums, func(n int) int { return n * n }) // T, U inferred
```

## Constraints

A type parameter's **constraint** is an interface that says what the code
may do with `T`:

| Constraint | Allows |
|---|---|
| `any` | nothing type-specific. You can store, pass, and return it |
| `comparable` | `==`, `!=`, and using `T` as a map key |
| `cmp.Ordered` | `<`, `>`, and so on: integers, floats, strings |
| custom union `~int \| ~float64` | the operators all listed types share (`+`, …) |

`~int` means "any type whose **underlying** type is `int`", so
`type Celsius int` is accepted. Without the `~`, only `int` itself is.

## Generic types

```go
type Stack[T any] struct{ items []T }
func (s *Stack[T]) Push(v T) { ... }
var s Stack[string]
```

`var zero T` gives you the zero value of any `T`. It's useful for "not
found" returns.

## When to use generics, and when not to

**Use** them for container types (stack, set, cache) and algorithms that
are the same for every type (map/filter, min/max, uniq). The stdlib's
`slices` and `maps` packages are the canonical examples.

**Don't use** them when an interface already works. If you only need to
*call methods* on a value, `func F(r io.Reader)` is simpler than
`func F[R io.Reader](r R)`. Go culture is "write concrete code first,
generalise when you see the duplication."

Limitations: methods can't declare their own type parameters (only the
type can), and there's no specialisation.

## Try it

1. Write `GroupBy[T any, K comparable](xs []T, key func(T) K) map[K][]T`.
2. Write a generic `Set[T comparable]` with `Add`, `Has`, and `Len`.
