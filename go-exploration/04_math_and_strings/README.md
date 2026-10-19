# Lesson 04: Math and Text

**You will learn:** how to do math, how to work with text, and how to change one type into another.

```bash
go run ./04_math_and_strings
```

---

## Part A: Math

| Symbol | Meaning | Example | Result |
|---|---|---|---|
| `+` | add | `7 + 2` | `9` |
| `-` | subtract | `7 - 2` | `5` |
| `*` | multiply | `7 * 2` | `14` |
| `/` | divide | `7 / 2` | `3` (see below) |
| `%` | remainder | `7 % 2` | `1` |

### Watch out: int / int gives an int

```go
fmt.Println(7 / 2)     // 3    (the .5 is thrown away)
fmt.Println(7.0 / 2.0) // 3.5
```

When both numbers are `int`, Go gives back an `int`. The decimal part is dropped.

### Shortcuts

```go
score := 10
score += 5   // same as: score = score + 5   -> 15
score -= 3   // same as: score = score - 3   -> 12
score++      // add 1                        -> 13
score--      // subtract 1                   -> 12
```

## Part B: Text (strings)

### Joining text

```go
first := "Ravi"
last := "Kumar"
full := first + " " + last   // "Ravi Kumar"
```

### Length

```go
len("hello")   // 5
```

### The `strings` toolbox

Add `import "strings"` to use these:

```go
strings.ToUpper("hello")                 // "HELLO"
strings.ToLower("HELLO")                 // "hello"
strings.Contains("hello world", "world") // true
strings.Replace("I like tea", "tea", "coffee", 1) // "I like coffee"
strings.TrimSpace("   hi   ")            // "hi"
strings.Split("a,b,c", ",")              // [a b c]
strings.Repeat("ha", 3)                  // "hahaha"
```

**Tip:** Run `go doc strings` in the terminal to see every tool in the box.

## Part C: Changing types (conversion)

Go **never** changes types for you. You must do it yourself.

### int ↔ float64

```go
apples := 7
half := float64(apples) / 2   // 3.5

price := 9.99
rounded := int(price)         // 9 (decimal part is cut off)
```

This fails:

```go
apples := 7
price := 2.5
total := apples * price  // ERROR: can't multiply int by float64
total := float64(apples) * price  // OK: 17.5
```

### Number ↔ text

Use the `strconv` toolbox ("string convert"):

```go
text := strconv.Itoa(42)        // int -> string: "42"

n, err := strconv.Atoi("42")    // string -> int: 42
```

`Atoi` gives back **two** values. The second one, `err`, tells you if something went wrong (for example `strconv.Atoi("hello")` can't work).
We will learn about errors in Lesson 15. For now, just know it's there.

### A trap: `string(number)` does not give you the digits

```go
n := 65
strconv.Itoa(n)    // "65"  <- this is what you usually want
string(rune(n))    // "A"   (65 is the code for the letter A)
```

If you write `string(n)`, you get `"A"`, not `"65"`. `go vet` warns you about this mistake.

## Practice

1. You have `total := 250` and `people := 4`. Print how much each person pays, as a decimal: `62.5`.
2. Take `"  Go Is Fun  "`, remove the spaces around it, and make it all lowercase.
3. Turn the text `"100"` into a number, add `50`, and print `150`.

<details>
<summary>Answers</summary>

```go
total := 250
people := 4
fmt.Println(float64(total) / float64(people)) // 62.5

s := "  Go Is Fun  "
fmt.Println(strings.ToLower(strings.TrimSpace(s))) // go is fun

n, _ := strconv.Atoi("100") // _ means "I don't need this value"
fmt.Println(n + 50)          // 150
```
</details>

---

**Next:** [Lesson 05: if / else](../05_if_else/)
