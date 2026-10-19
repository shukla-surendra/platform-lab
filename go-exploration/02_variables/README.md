# Lesson 02: Variables

**You will learn:** how to store values (like a name or a number) so you can use them later.

```bash
go run ./02_variables
```

---

## What is a variable?

A variable is a **box with a name on it**. You put a value inside the box.
Later you use the name to get the value back.

```go
var name string = "Asha"
```

Read it like this: *"Make a box called `name`. It holds a `string` (text). Put `"Asha"` in it."*

## The 4 basic types

Every box in Go has a **type**. The type says what kind of value can go inside.

| Type | Holds | Example |
|---|---|---|
| `string` | text | `"Hello"` |
| `int` | whole numbers | `42`, `-7` |
| `float64` | numbers with a decimal point | `3.14`, `99.5` |
| `bool` | true or false | `true`, `false` |

```go
var city string = "Pune"
var age int = 25
var price float64 = 99.50
var isStudent bool = true
```

## Three ways to make a variable

```go
// 1. Full form: name + type + value
var age int = 25

// 2. Let Go guess the type from the value
var age = 25          // Go sees 25 and knows it is an int

// 3. Short form (most common). Only works inside a function.
age := 25
```

**Tip:** Most Go code uses the short form `:=`. Use it inside functions.

## Changing a value

Use `=` (without the colon) to put a new value in a box that already exists:

```go
score := 10    // make the box
score = 20     // change what's inside
```

`:=` **makes** a new box. `=` **changes** an existing box.

## A box can't change its type

```go
age := 25
age = "twenty-five"   // ERROR: age is an int, you can't put text in it
```

## Empty boxes get a "zero value"

If you make a box but don't put anything in it, Go fills it with a default value:

```go
var count int      // 0
var name string    // "" (empty text)
var ok bool        // false
var price float64  // 0
```

## Constants: values that never change

```go
const pi = 3.14159
const appName = "My Go App"
```

If you try `pi = 3`, Go gives an error. Use `const` for fixed values.

## Naming style

Go uses **camelCase** for names: the first word is lowercase, and each new word starts with a capital letter.

```go
firstName := "Ravi"     // good (Go style)
first_name := "Ravi"    // works, but it's not Go style
```

So `number_1` is better written as `number1`.

## Practice

1. Make variables for your name, your age, and your city. Print them.
2. Make a variable `score := 50`, then change it to `75` and print it.
3. Make `var total int` without a value and print it. What do you see?

<details>
<summary>Answer for 1</summary>

```go
name := "Surendra"
age := 30
city := "Bengaluru"
fmt.Println(name, age, city)
```
</details>

---

**Next:** [Lesson 03: Printing](../03_printing/)
