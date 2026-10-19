# Lesson 12: Pointers

**You will learn:** what a pointer is, and how to let a function change the original value instead of a copy.

```bash
go run ./12_pointers
```

---

## The problem

```go
func birthday(age int) {
	age = age + 1
}

func main() {
	myAge := 25
	birthday(myAge)
	fmt.Println(myAge)   // still 25! Why?
}
```

When you call `birthday(myAge)`, Go gives the function a **photocopy** of `myAge`.
The function changes the photocopy. Your original stays the same.

## The idea: a pointer is an address

Think of a house:

- The **house** is the value (`25`).
- The **address** of the house is the pointer ("12 MG Road").

If you give someone a **photocopy** of your house plan, they can't change your house.
If you give someone your **address**, they can go there and paint your walls.

A pointer is the **address** of a variable in memory.

## Two symbols to learn

| Symbol | Say it as | Meaning |
|---|---|---|
| `&x` | "address of x" | Get the address (pointer) of `x` |
| `*p` | "value at p" | Go to the address and use the value there |

```go
age := 25
p := &age          // p holds the address of age

fmt.Println(p)     // 0xc000012345  (some address)
fmt.Println(*p)    // 25            (the value at that address)

*p = 30            // go to the address and change the value
fmt.Println(age)   // 30  <- the original changed!
```

## The type of a pointer: `*int`

```go
var p *int    // p is "a pointer to an int"
```

- `int` is a number.
- `*int` is an **address** of a number.

## Fixing the birthday function

```go
func birthday(age *int) {   // take an address
	*age = *age + 1          // change the value at that address
}

func main() {
	myAge := 25
	birthday(&myAge)          // send the address
	fmt.Println(myAge)        // 26
}
```

## Pointers to structs (the most common use)

```go
type Student struct {
	Name  string
	Marks int
}

func addBonus(s *Student) {
	s.Marks += 5    // Go lets you write s.Marks instead of (*s).Marks
}

st := Student{Name: "Asha", Marks: 80}
addBonus(&st)
fmt.Println(st.Marks)   // 85
```

Nice: with structs, you **don't need** to write `*` to reach a field. `s.Marks` works.

## nil: a pointer to nothing

A pointer that points nowhere is `nil`:

```go
var p *int
fmt.Println(p == nil)   // true
fmt.Println(*p)         // CRASH: "nil pointer dereference"
```

Before you use `*p`, make sure `p` is not `nil`.

## When should I use a pointer?

| Use a pointer when… | Don't bother when… |
|---|---|
| a function must **change** the original | a function only **reads** the value |
| the struct is **big** (so copying is slow) | the value is small (int, string, small struct) |

Slices and maps already behave like they share their data, so you usually **don't** need pointers to them.

## Practice

1. Write `func reset(n *int)` that sets the number to 0. Test it.
2. Write `func swap(a, b *int)` that swaps two numbers. After `swap(&x, &y)`, x and y should be swapped.
3. Write `func rename(s *Student, newName string)` that changes a student's name.

<details>
<summary>Answers</summary>

```go
func reset(n *int) {
	*n = 0
}

func swap(a, b *int) {
	*a, *b = *b, *a
}

func rename(s *Student, newName string) {
	s.Name = newName
}
```
</details>

---

**Next:** [Lesson 13: Methods](../13_methods/)
