# Lesson 17: Generics

**You will learn:** how to write **one** function that works for many types, without copy-pasting.

```bash
go run ./17_generics
```

---

## The problem: copy-paste code

```go
func SumInts(nums []int) int {
	total := 0
	for _, n := range nums {
		total += n
	}
	return total
}

func SumFloats(nums []float64) float64 {
	total := 0.0
	for _, n := range nums {
		total += n
	}
	return total
}
```

The two functions are the **same code**. Only the type is different.

## The solution: a type placeholder

```go
func Sum[T int | float64](nums []T) T {
	var total T
	for _, n := range nums {
		total += n
	}
	return total
}
```

The new part is `[T int | float64]`. Read it as:

> *"`T` is a **placeholder** for a type. `T` can be `int` **or** `float64`."*

Then use `T` wherever you would write the type.

```go
Sum([]int{1, 2, 3})           // 6    (Go sets T = int)
Sum([]float64{1.5, 2.5})      // 4    (Go sets T = float64)
```

Go figures out `T` by itself from the values you pass in.

## Think of it like a form with a blank

```
func Sum[T ...](nums []T) T
            ▲          ▲   ▲
            └──────────┴───┴── fill in the same type everywhere
```

## Common "allowed types" (constraints)

The part after `T` says **which types are allowed**:

| Constraint | Allowed types | Use it when you need… |
|---|---|---|
| `any` | every type | just to store or pass values around |
| `comparable` | types you can compare with `==` | to check equality or use as a map key |
| `int \| float64` | only those listed | math (`+`, `<`) |
| `cmp.Ordered` | numbers and strings | `<` and `>` (sorting, min, max) |

### Example with `comparable`

```go
func Contains[T comparable](items []T, target T) bool {
	for _, item := range items {
		if item == target {    // == needs comparable
			return true
		}
	}
	return false
}

Contains([]string{"a", "b"}, "b")   // true
Contains([]int{1, 2, 3}, 5)         // false
```

## Generic types: a box that holds any type

You can also make **structs** with a type placeholder. Here is a **Stack** (like a pile of plates: last in, first out):

```go
type Stack[T any] struct {
	items []T
}

func (s *Stack[T]) Push(item T) {
	s.items = append(s.items, item)
}

func (s *Stack[T]) Pop() T {
	last := s.items[len(s.items)-1]
	s.items = s.items[:len(s.items)-1]
	return last
}

nums := Stack[int]{}        // a stack of ints
nums.Push(1)
nums.Push(2)
nums.Pop()                  // 2

words := Stack[string]{}    // a stack of strings, same code!
```

## When should I use generics?

- ✅ The **same logic** for different types (Sum, Contains, Stack, Map, Filter).
- ❌ Don't use generics "just because". If a normal function or an interface works, use that.

**Good news:** Go's standard library already has many generic helpers: `slices.Contains`, `slices.Max`, `maps.Keys`, and more.
You've been using generics since Lesson 09 without knowing it!

## Practice

1. Write `func Max[T cmp.Ordered](a, b T) T` (import `"cmp"`). Test it with ints and strings.
2. Write `func Filter[T any](items []T, keep func(T) bool) []T` that returns only the items where `keep` returns true. Use it to get even numbers.
3. Add a `Len() int` method to `Stack[T]`.

<details>
<summary>Answers</summary>

```go
func Max[T cmp.Ordered](a, b T) T {
	if a > b {
		return a
	}
	return b
}

func Filter[T any](items []T, keep func(T) bool) []T {
	var result []T
	for _, item := range items {
		if keep(item) {
			result = append(result, item)
		}
	}
	return result
}

evens := Filter([]int{1, 2, 3, 4}, func(n int) bool { return n%2 == 0 })

func (s *Stack[T]) Len() int {
	return len(s.items)
}
```

(In `Filter`, `keep func(T) bool` means "a function that takes a T and returns a bool". Yes, you can pass functions around like values!)
</details>

---

🎉 **Part 2 done!** You now know the whole core of the Go language.

**Next:** [Lesson 18: Goroutines](../18_goroutines/): doing many things at the same time.
