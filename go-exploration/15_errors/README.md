# Lesson 15: Errors

**You will learn:** how Go tells you something went wrong, and how you should handle it.

```bash
go run ./15_errors
```

---

## Go's approach: errors are just values

Many languages use `try / catch` (exceptions). **Go doesn't.**

In Go, a function that can fail gives back **2 things**:

1. the result
2. an `error` (which is `nil` if everything went fine)

You already saw this in Lesson 04:

```go
n, err := strconv.Atoi("42")      // n = 42,  err = nil        (OK)
n, err := strconv.Atoi("hello")   // n = 0,   err = "invalid syntax" (failed)
```

## The pattern you will write 1000 times

```go
n, err := strconv.Atoi(text)
if err != nil {
	fmt.Println("Something went wrong:", err)
	return
}
// if we get here, n is safe to use
fmt.Println("Number is", n)
```

Read it as: *"Try it. **If there is an error**, deal with it and stop. Otherwise, continue."*

`nil` means "nothing", so `err != nil` means "there **is** an error".

## Making your own errors

```go
import "errors"

func divide(a, b float64) (float64, error) {
	if b == 0 {
		return 0, errors.New("cannot divide by zero")
	}
	return a / b, nil    // nil = no error
}
```

Using it:

```go
result, err := divide(10, 0)
if err != nil {
	fmt.Println("Error:", err)   // Error: cannot divide by zero
	return
}
fmt.Println(result)
```

**Rules:**
- `error` is always the **last** return value.
- When there's an error, the other values are usually zero (`0`, `""`, `nil`). Don't use them.
- Error messages start with a **small letter** and have **no full stop**.

## Errors with details: fmt.Errorf

```go
func checkAge(age int) error {
	if age < 0 {
		return fmt.Errorf("age %d is not valid", age)
	}
	return nil
}
```

## Adding context as errors go up: %w

In a real app, one function calls another, which calls another. When an error comes back up,
each level can **add a note** about what it was doing:

```go
func loadUser(id string) error {
	err := readFile("users.txt")
	if err != nil {
		return fmt.Errorf("loading user %s: %w", id, err)
	}
	return nil
}
```

The final message reads like a story:

```
loading user 42: reading users.txt: file not found
```

`%w` means **wrap**: put the old error inside the new one, so you can still check it later.

## Checking for a specific error: errors.Is

```go
var ErrNotFound = errors.New("not found")   // a named error others can check for

func findUser(name string) error {
	return ErrNotFound
}

err := findUser("Ravi")
if errors.Is(err, ErrNotFound) {
	fmt.Println("No such user. Maybe create one?")
}
```

`errors.Is` also looks **inside** wrapped errors (the ones made with `%w`).

## panic: for bugs only

`panic` **crashes** the program right away:

```go
panic("this should never happen")
```

Don't use `panic` for normal problems like a wrong input or a missing file. Return an `error`.
`panic` is for real bugs, for example "the program is in an impossible state".

## Summary

| Situation | What to do |
|---|---|
| function can fail | return `(result, error)` |
| calling such a function | `if err != nil { ... }` right after |
| simple error | `errors.New("message")` |
| error with values | `fmt.Errorf("bad age %d", age)` |
| add context to an error | `fmt.Errorf("doing X: %w", err)` |
| check which error | `errors.Is(err, ErrSomething)` |

## Practice

1. Write `func sqrt(n float64) (float64, error)` that returns an error for negative numbers (use `math.Sqrt` for the answer).
2. Write `func withdraw(balance, amount float64) (float64, error)`. Return an error `"not enough balance"` if amount > balance.
3. Make `var ErrEmpty = errors.New("empty name")`. Write `func greet(name string) error` that returns it when name is `""`. In `main`, check it with `errors.Is`.

<details>
<summary>Answers</summary>

```go
func sqrt(n float64) (float64, error) {
	if n < 0 {
		return 0, fmt.Errorf("cannot take sqrt of negative number %v", n)
	}
	return math.Sqrt(n), nil
}

func withdraw(balance, amount float64) (float64, error) {
	if amount > balance {
		return balance, errors.New("not enough balance")
	}
	return balance - amount, nil
}

var ErrEmpty = errors.New("empty name")

func greet(name string) error {
	if name == "" {
		return ErrEmpty
	}
	fmt.Println("Hello,", name)
	return nil
}

// in main:
if err := greet(""); errors.Is(err, ErrEmpty) {
	fmt.Println("Please give a name")
}
```
</details>

---

**Next:** [Lesson 16: Packages and modules](../16_packages/)
