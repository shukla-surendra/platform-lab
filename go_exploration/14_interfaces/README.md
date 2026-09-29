# Lesson 14: Interfaces

**You will learn:** how to write code that works with **many different types**, as long as they can do the same job.

```bash
go run ./14_interfaces
```

---

## The idea (real life)

A job advert says: *"Wanted: someone who can **drive**."*

It doesn't care if you are Asha or Ravi, a student or a chef.
If you can **drive**, you get the job.

An **interface** is that job advert. It's a **list of methods**.
Any type that has those methods "gets the job" automatically.

## The problem

We have two shapes:

```go
type Rectangle struct{ Width, Height float64 }
type Circle struct{ Radius float64 }

func (r Rectangle) Area() float64 { return r.Width * r.Height }
func (c Circle) Area() float64    { return 3.14 * c.Radius * c.Radius }
```

We want **one** function that prints the area of **any** shape.
But a function's input needs one type. Is it `Rectangle` or `Circle`?

## The solution: an interface

```go
type Shape interface {
	Area() float64
}
```

Read it as: *"A `Shape` is **anything** that has an `Area() float64` method."*

Now:

```go
func printArea(s Shape) {
	fmt.Printf("Area: %.2f\n", s.Area())
}

printArea(Rectangle{Width: 3, Height: 4})   // Area: 12.00
printArea(Circle{Radius: 2})                // Area: 12.56
```

Both work because **both have an `Area()` method**.

## The magic: you never write "implements"

In Java you would write `class Circle implements Shape`.
In Go you **don't write anything**. If `Circle` has `Area() float64`, then it **is** a `Shape`. That's it.

## A list of different things

```go
shapes := []Shape{
	Rectangle{Width: 3, Height: 4},
	Circle{Radius: 2},
	Rectangle{Width: 1, Height: 1},
}

total := 0.0
for _, s := range shapes {
	total += s.Area()
}
```

One list, different types, one loop. That's the power of interfaces.

## An interface you'll see everywhere: Stringer

The `fmt` package has this interface:

```go
type Stringer interface {
	String() string
}
```

If your type has a `String()` method, `fmt.Println` **uses it automatically**:

```go
type Student struct{ Name string; Marks int }

func (s Student) String() string {
	return fmt.Sprintf("%s (%d marks)", s.Name, s.Marks)
}

fmt.Println(Student{"Asha", 90})   // Asha (90 marks)
```

## `any`: the "accept anything" interface

`any` is an interface with **no methods**. Every type has "no methods" at least, so **every value fits**:

```go
func show(x any) {
	fmt.Println("Got:", x)
}

show(42)
show("hello")
show(true)
```

`fmt.Println` itself uses `any`. That's why it can print anything.

Use `any` rarely. You lose Go's type checking.

## Finding out the real type: type switch

Sometimes you have an `any` or a `Shape` and want to know what's really inside:

```go
func describe(x any) {
	switch v := x.(type) {
	case int:
		fmt.Println("an int, double is", v*2)
	case string:
		fmt.Println("a string of length", len(v))
	default:
		fmt.Println("something else")
	}
}
```

## Tips

- Keep interfaces **small**: 1 or 2 methods is best.
- Interface names often end in **-er**: `Reader`, `Writer`, `Stringer`, `Shape` is fine too.

## Practice

1. Add a `Triangle` type (`Base`, `Height`, area = `0.5 * Base * Height`). Put it in the `shapes` list. No other change should be needed!
2. Make an interface `Speaker` with `Speak() string`. Make `Dog` ("Woof") and `Cat` ("Meow") types. Loop over a `[]Speaker` and print what each says.
3. Add a `String()` method to `Rectangle` so `fmt.Println(rect)` prints `Rectangle 3 x 4`.

<details>
<summary>Answers</summary>

```go
type Triangle struct{ Base, Height float64 }

func (t Triangle) Area() float64 { return 0.5 * t.Base * t.Height }

type Speaker interface {
	Speak() string
}
type Dog struct{}
type Cat struct{}

func (Dog) Speak() string { return "Woof" }
func (Cat) Speak() string { return "Meow" }

for _, s := range []Speaker{Dog{}, Cat{}} {
	fmt.Println(s.Speak())
}

func (r Rectangle) String() string {
	return fmt.Sprintf("Rectangle %v x %v", r.Width, r.Height)
}
```
</details>

---

**Next:** [Lesson 15: Errors](../15_errors/)
