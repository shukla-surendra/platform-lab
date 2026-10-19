# Lesson 10: Maps (dictionaries)

**You will learn:** how to store values that you look up by a **name** instead of a position.

```bash
go run ./10_maps
```

---

## The idea

A slice finds things by **position**: `fruits[0]`.
A map finds things by **key**, like a phone book: you look up a *name* and get a *number*.

```
   key        value
 ┌────────┬──────────┐
 │ "Asha" │ 98765... │
 │ "Ravi" │ 91234... │
 └────────┴──────────┘
```

## Making a map

```go
ages := map[string]int{
	"Asha": 25,
	"Ravi": 30,
}
```

`map[string]int` means: *"keys are strings, values are ints"*.

**Note:** in Go, the last line inside `{ }` needs a comma too: `"Ravi": 30,`

## Using a map

```go
ages["Meena"] = 28          // add a new entry
ages["Asha"] = 26           // change an existing one
fmt.Println(ages["Ravi"])   // read: 30
delete(ages, "Ravi")        // remove
len(ages)                   // how many entries
```

## Is a key there? (the "comma ok" check)

If a key doesn't exist, Go gives you the **zero value**, not an error:

```go
fmt.Println(ages["Nobody"])   // 0
```

But what if someone really is 0 years old? Use the **comma ok** form to check:

```go
age, ok := ages["Nobody"]
if ok {
	fmt.Println("Found, age is", age)
} else {
	fmt.Println("Not found")
}
```

`ok` is `true` if the key exists and `false` if it doesn't.

## Looping over a map

```go
for name, age := range ages {
	fmt.Println(name, "is", age)
}
```

**Important:** the order is **random**. It can be different every time you run the program.
If you need order, get the keys, sort them, and loop over the sorted keys (see `main.go`).

## Starting with an empty map

```go
counts := map[string]int{}   // empty but ready to use
counts["go"]++               // counts["go"] is now 1
```

**Watch out:** `var m map[string]int` makes a **nil** map. Reading from it is fine, but **writing to it crashes**.
Always use `map[string]int{}` or `make(map[string]int)` when you plan to add things.

## A real example: counting words

```go
text := "go is fun and go is fast"
counts := map[string]int{}
for _, word := range strings.Fields(text) {   // Fields splits by spaces
	counts[word]++
}
// counts: go=2 is=2 fun=1 and=1 fast=1
```

## Slice or map?

| Use a **slice** when… | Use a **map** when… |
|---|---|
| order matters | you look things up by a name or ID |
| you go through all items | you need "does this exist?" quickly |

## Practice

1. Make a map of 3 countries to their capitals. Print the capital of one country.
2. Check if `"Japan"` is in your map using comma ok.
3. Count how many times each letter appears in `"banana"`.

<details>
<summary>Answers</summary>

```go
capitals := map[string]string{
	"India":  "New Delhi",
	"France": "Paris",
	"Kenya":  "Nairobi",
}
fmt.Println(capitals["France"])

if capital, ok := capitals["Japan"]; ok {
	fmt.Println(capital)
} else {
	fmt.Println("Japan is not in the map")
}

letters := map[string]int{}
for _, ch := range "banana" {
	letters[string(ch)]++
}
fmt.Println(letters) // map[a:3 b:1 n:2]
```
</details>

---

**Next:** [Lesson 11: Structs](../11_structs/)
