# Lesson 03: Printing

**You will learn:** the different ways to print, and when to use each one.

```bash
go run ./03_printing
```

---

## Println: print values with spaces between them

```go
name := "Asha"
age := 25
fmt.Println("Name:", name, "Age:", age)
```

Output:

```
Name: Asha Age: 25
```

`Println` puts a **space** between each value and a **new line** at the end.
It's the easiest way to print.

## Printf: print using a template

`Printf` lets you write a sentence with **blanks**, then fill in the blanks:

```go
fmt.Printf("My name is %s and I am %d years old.\n", name, age)
```

Output:

```
My name is Asha and I am 25 years old.
```

`%s` and `%d` are the blanks. They are filled **in order**: first `name`, then `age`.

### The most useful blanks ("verbs")

| Verb | Use it for | Example output |
|---|---|---|
| `%s` | string (text) | `Asha` |
| `%d` | int (whole number) | `25` |
| `%f` | float64 | `99.500000` |
| `%.2f` | float64 with 2 decimal places | `99.50` |
| `%t` | bool | `true` |
| `%v` | **any value** (when you're not sure, use this) | `25` |
| `%T` | the **type** of a value | `int` |

### Printf does NOT add a new line

You must add `\n` at the end yourself. `\n` means "new line".

```go
fmt.Printf("Hello")
fmt.Printf("World\n")
// prints: HelloWorld
```

## A common mistake: using %d in Println

This is a very common beginner mistake (it's in `00_exploration/00_basic.go` too):

```go
sum := 60
fmt.Println("Hello, Go!, %d", sum)
```

You might expect `Hello, Go!, 60`. But you get:

```
Hello, Go!, %d 60
```

**Why?** `Println` does not understand `%d`. It prints the text exactly as it is, then adds `sum` after a space.

**Rule:**
- If you use `%d`, `%s`, `%v`, use **`Printf`** (the "f" means "format").
- If you use **`Println`**, just list the values with commas.

```go
fmt.Printf("Hello, Go!, %d\n", sum) // correct
fmt.Println("Hello, Go!,", sum)     // also correct
```

**Tip:** The `go vet ./...` command finds this mistake for you.

## Sprintf: make text but don't print it

`Sprintf` works like `Printf`, but it **gives you back the text** instead of printing it:

```go
message := fmt.Sprintf("%s scored %d points", "Ravi", 90)
// message is now "Ravi scored 90 points"
```

This is useful when you want to save the text in a variable.

## Summary

| Function | Adds new line? | Understands `%d`, `%s`? | Prints? |
|---|---|---|---|
| `fmt.Println` | yes | no | yes |
| `fmt.Printf` | no (add `\n`) | yes | yes |
| `fmt.Sprintf` | no | yes | no, it returns the text |

## Practice

1. Use `Printf` to print: `Apple costs 40.50 rupees` where `40.5` is a float64 variable. (Hint: use `%.2f`.)
2. Print the type of `3.14`, `"hi"`, and `true` with `%T`.
3. Fix this line: `fmt.Println("Total: %d", 100)`

<details>
<summary>Answers</summary>

```go
price := 40.5
fmt.Printf("Apple costs %.2f rupees\n", price)

fmt.Printf("%T %T %T\n", 3.14, "hi", true) // float64 string bool

fmt.Printf("Total: %d\n", 100)
```
</details>

---

**Next:** [Lesson 04: Math and text](../04_math_and_strings/)
