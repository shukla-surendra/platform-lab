# Lesson 22: Testing

**You will learn:** how to write code that **checks your code** automatically.

```bash
go run ./22_testing        # run the program
go test ./22_testing       # run the tests
go test -v ./22_testing    # run the tests and show each one
```

---

## Why test?

You wrote a function `Grade(marks)`. You tried it once by hand and it worked.
A month later you change it. **Does it still work for every case?** Checking by hand every time is slow and boring.

A **test** is a small piece of code that calls your function and checks the answer.
Go runs **all** your tests in one second with one command.

**When to write tests:** when you build a real application. Write tests for the important logic, the things that would hurt if they broke.
While you are *learning the language* (Lessons 1–21), you don't need them.

## The files in this folder

```
22_testing/
├── main.go         <- the code: Add, Grade, Discount
└── main_test.go    <- the tests for that code
```

**Rule:** test files **must end in `_test.go`**. Go only runs them with `go test`, never with `go run` or `go build`.

## Your first test

```go
package main

import "testing"

func TestAdd(t *testing.T) {
	got := Add(2, 3)
	want := 5

	if got != want {
		t.Errorf("Add(2, 3) = %d, want %d", got, want)
	}
}
```

Just 3 rules:

1. The function name **starts with `Test`**: `TestAdd`, `TestGrade`, …
2. It takes **`t *testing.T`**. `t` is your tool to report problems.
3. If the answer is wrong, call **`t.Errorf(...)`**. That marks the test as failed.

There's no special "assert" library. A normal `if` is enough.

## Run it

```bash
go test ./22_testing
```

```
ok  	platformlab/go_exploration/22_testing	0.002s
```

`ok` = all tests passed.

## What a failure looks like

Break `Add` on purpose (change `a + b` to `a - b`) and run again:

```
--- FAIL: TestAdd (0.00s)
    main_test.go:11: Add(2, 3) = -1, want 5
FAIL
```

It tells you **which test**, **which line**, and **what was wrong**. That's why a clear message in `t.Errorf` matters.
(Change it back afterwards!)

## Testing many cases: a table test

Instead of writing 5 almost-same tests, make a **list of cases** and loop over it:

```go
func TestGrade(t *testing.T) {
	tests := []struct {
		marks int
		want  string
	}{
		{95, "A"},
		{75, "B"},
		{55, "C"},
		{30, "Fail"},
	}

	for _, tc := range tests {
		got := Grade(tc.marks)
		if got != tc.want {
			t.Errorf("Grade(%d) = %q, want %q", tc.marks, got, tc.want)
		}
	}
}
```

`[]struct{ ... }{ ... }` is a slice of structs made on the spot, with no type name. It's just a table: one row per case.
To test a new case, **add one line** to the table. Go programmers use this pattern everywhere.

## Testing errors

```go
func TestDiscountError(t *testing.T) {
	_, err := Discount(100, 150)   // 150% makes no sense
	if err == nil {
		t.Error("expected an error for 150%, got nil")
	}
}
```

Test the **bad** inputs too, not just the happy path.

## Useful commands

| Command | What it does |
|---|---|
| `go test ./22_testing` | run the tests in one folder |
| `go test ./...` | run **all** tests in the project |
| `go test -v ./22_testing` | show every test name and result |
| `go test -run TestGrade ./22_testing` | run only tests whose name matches |
| `go test -cover ./22_testing` | show how much of your code the tests cover |
| `go test -race ./...` | also check for race conditions (Lesson 20) |

## `t.Errorf` vs `t.Fatalf`

- `t.Errorf`: mark it failed, **keep going** (so you see all the bad cases).
- `t.Fatalf`: mark it failed and **stop this test now** (use it when the rest of the test can't work, for example the setup failed).

## Practice

1. Add a case `{90, "A"}` to the Grade table. Does it pass? What about `{89, "B"}`?
2. Write `IsEven(n int) bool` in `main.go` and a table test for it in `main_test.go`.
3. Run `go test -cover ./22_testing`. Then add a test for something that isn't tested yet and see the number go up.

## Where to go from here

The [`taskapi/`](../taskapi/) project shows testing in a real application: testing a web API with `httptest`, a fake database for fast tests, and tests against a real Postgres.

---

**Next:** [Lesson 23: Web server](../23_web_server/)
