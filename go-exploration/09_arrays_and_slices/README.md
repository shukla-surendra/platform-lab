# Lesson 09: Arrays and Slices (lists)

**You will learn:** how to keep many values in one variable, like a shopping list.

```bash
go run ./09_arrays_and_slices
```

---

## Why do we need lists?

Without a list:

```go
fruit1 := "apple"
fruit2 := "banana"
fruit3 := "mango"
// What if you have 100 fruits?
```

With a list:

```go
fruits := []string{"apple", "banana", "mango"}
```

## Slices: the list you'll use 99% of the time

```go
fruits := []string{"apple", "banana", "mango"}
```

`[]string` means *"a list of strings"*.

### Getting an item by position (index)

Positions start at **0**:

```
 index:    0         1         2
       ┌─────────┬─────────┬─────────┐
       │ "apple" │"banana" │ "mango" │
       └─────────┴─────────┴─────────┘
```

```go
fruits[0]        // "apple"
fruits[2]        // "mango"
fruits[1] = "kiwi"   // change an item
len(fruits)      // 3 (how many items)
```

If you use `fruits[5]`, the program crashes with **"index out of range"**, because there is no item at position 5.

### Adding items: append

```go
fruits = append(fruits, "grapes")
```

**Important:** you must write `fruits = append(...)`. `append` gives back a **new** list, so you must save it.

### Looping over a list

```go
for index, fruit := range fruits {
	fmt.Println(index, fruit)
}
```

If you don't need the index, use `_`:

```go
for _, fruit := range fruits {
	fmt.Println(fruit)
}
```

### Starting with an empty list

```go
var names []string          // empty list, length 0
names = append(names, "Asha")
names = append(names, "Ravi")
```

### Taking a part of a list (slicing)

```go
nums := []int{10, 20, 30, 40, 50}
nums[1:3]   // [20 30]       from index 1, up to (not including) 3
nums[:2]    // [10 20]       from the start
nums[3:]    // [40 50]       to the end
```

**Careful:** a part shares memory with the original list. If you change `part[0]`, the original list changes too.
Use `slices.Clone(part)` when you need a separate copy.

## Handy tools: the `slices` package

```go
import "slices"

nums := []int{5, 2, 8, 1}
slices.Sort(nums)              // nums is now [1 2 5 8]
slices.Contains(nums, 8)       // true
slices.Index(nums, 5)          // 2 (position of 5)
slices.Max(nums)               // 8
```

## Arrays: fixed-size lists (rarely used)

```go
var days [7]string     // exactly 7 items, can never grow
```

An array has its **size written in the brackets**: `[7]string`.
A slice has **empty brackets**: `[]string`.
In real code, you'll almost always use slices.

## Practice

1. Make a slice of 5 numbers. Use a loop to find the **total** and the **average**.
2. Start with an empty `[]string`, append 3 city names, then print how many cities there are.
3. Make a slice of numbers, then make a **new** slice that has only the even numbers.

<details>
<summary>Answers</summary>

```go
nums := []int{10, 20, 30, 40, 50}
total := 0
for _, n := range nums {
	total += n
}
fmt.Println("Total:", total, "Average:", float64(total)/float64(len(nums)))

var cities []string
cities = append(cities, "Delhi")
cities = append(cities, "Mumbai")
cities = append(cities, "Chennai")
fmt.Println(len(cities))

all := []int{1, 2, 3, 4, 5, 6}
var evens []int
for _, n := range all {
	if n%2 == 0 {
		evens = append(evens, n)
	}
}
fmt.Println(evens) // [2 4 6]
```
</details>

---

**Next:** [Lesson 10: Maps](../10_maps/)
