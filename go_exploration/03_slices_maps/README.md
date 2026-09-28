# 03 · Arrays, slices, maps

```bash
go run ./03_slices_maps
go test ./03_slices_maps
```

## Arrays vs slices

| | Array `[3]int` | Slice `[]int` |
|---|---|---|
| Size | fixed, part of the type | dynamic |
| Assignment | **copies** all elements | copies the 3-word header (shares data) |
| Used | rarely directly | everywhere |

## What a slice actually is

```
slice header ──▶ ┌─────┬─────┬─────┬─────┬─────┐
 ptr ───────────▶│  1  │  2  │  3  │  4  │  5  │  backing array
 len = 3         └─────┴─────┴─────┴─────┴─────┘
 cap = 5
```

- `make([]T, len, cap)` preallocates. `var s []T` is a **nil slice**, and
  it's fine to `append` to, `range` over, and `len()`.
- `append` writes in place if `len < cap`. Otherwise it allocates a bigger
  array (roughly doubling) and copies. **Always use the return value:**
  `s = append(s, x)`.

### The sharing gotcha

```go
base := []int{1, 2, 3, 4, 5}
view := base[1:3]           // [2 3], but cap reaches to base's end
view = append(view, 40)     // fits in cap → overwrites base[3]!
// base == [1 2 3 40 5]
```

Fixes: `slices.Clone(...)`, or a full slice expression `base[1:3:3]`
(cap = 2), which forces `append` to reallocate.

## `slices` and `maps` packages (Go 1.21+)

`slices.Sort`, `Contains`, `Index`, `BinarySearch`, `Compact`, `Equal`,
`Clone`, `Reverse`, and `maps.Keys`/`Values` (iterators), `slices.Sorted`,
`slices.Collect`. Reach for these before you write a loop.

## Maps

```go
m := map[string]int{"a": 1}
m["b"]++                 // missing key reads as zero value
v, ok := m["zzz"]        // comma-ok: ok == false
delete(m, "a")
```

- A **nil map** can be read but panics on write. Create one with `make` or a literal.
- **Iteration order is deliberately randomised.** If you need stable output, sort the keys.
- Maps are **not safe for concurrent writes**. Use a mutex (chapter 09) or `sync.Map`.
- Keys must be comparable (no slices, maps, or funcs as keys). Structs of comparable fields work.

## Try it

1. Change `base[1:3]` to `base[1:3:3]` and rerun. What happens to `base`?
2. Implement `Reverse(s []int)` in place using two indices, then compare with `slices.Reverse`.
