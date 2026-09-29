# Lesson 08: Functions

**You will learn:** how to put code in a named block so you can reuse it again and again.

```bash
go run ./08_functions
```

---

## What is a function?

A function is a **small machine**. You put something in, it does some work, and it gives something back.

```
   input  ──►  [ function ]  ──►  output
     3     ──►  [  double  ]  ──►    6
```

You already use functions: `fmt.Println(...)`, `strings.ToUpper(...)`, and `main()` itself.
Now you'll make your own.

## 1. A function with no input and no output

```go
func sayHello() {
	fmt.Println("Hello!")
}

func main() {
	sayHello()   // call (run) the function
	sayHello()   // call it again
}
```

## 2. A function with input (parameters)

```go
func greet(name string) {
	fmt.Println("Hello,", name)
}

greet("Asha")   // Hello, Asha
greet("Ravi")   // Hello, Ravi
```

`name string` means: *"This function needs one input called `name`, and it must be a string."*

Several inputs:

```go
func introduce(name string, age int) {
	fmt.Printf("%s is %d years old\n", name, age)
}
```

## 3. A function that gives back a value (return)

```go
func double(n int) int {
	return n * 2
}

result := double(3)   // result is 6
```

Read the first line like this: *"`double` takes an `int` called `n` and gives back an `int`."*

```
func double(n int) int {
     ──┬──  ──┬──  ─┬─
     name   input  output type
```

`return` sends the answer back and **ends** the function.

## 4. Returning two values

A Go function can give back **more than one** value. This is used a lot.

```go
func divide(a, b int) (int, int) {
	quotient := a / b
	remainder := a % b
	return quotient, remainder
}

q, r := divide(17, 5)
fmt.Println(q, r)   // 3 2
```

Remember `strconv.Atoi` from Lesson 04? It returns 2 values: the number and an error. Now you know how that works.

If you don't need one of the values, use `_` (underscore):

```go
q, _ := divide(17, 5)   // I only want the quotient
```

## 5. Why use functions?

- **No copy-paste.** Write the code once and call it many times.
- **Easier to read.** `calculateTax(salary)` explains itself.
- **Easier to fix.** A bug is fixed in one place.

## 6. Bonus: defer ("do this at the end")

`defer` runs a line **when the function finishes**, even though you wrote it at the top:

```go
func work() {
	defer fmt.Println("3. Cleaning up (deferred)")
	fmt.Println("1. Starting work")
	fmt.Println("2. Doing work")
}
```

Output:

```
1. Starting work
2. Doing work
3. Cleaning up (deferred)
```

You'll use `defer` later to close files and network connections, so you don't forget.

## Practice

1. Write `func square(n int) int` that returns `n * n`. Print `square(4)` (should be 16).
2. Write `func isAdult(age int) bool` that returns `true` if age is 18 or more.
3. Write `func minMax(a, b int) (int, int)` that returns the smaller number first, then the bigger one.

<details>
<summary>Answers</summary>

```go
func square(n int) int {
	return n * n
}

func isAdult(age int) bool {
	return age >= 18
}

func minMax(a, b int) (int, int) {
	if a < b {
		return a, b
	}
	return b, a
}
```
</details>

---

**Next:** [Lesson 09: Arrays and slices (lists)](../09_arrays_and_slices/)
