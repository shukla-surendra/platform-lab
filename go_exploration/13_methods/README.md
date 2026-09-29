# Lesson 13: Methods

**You will learn:** how to attach functions to your own types, so a type can *do things*, not just hold data.

```bash
go run ./13_methods
```

---

## Function vs method

In Lesson 11 we wrote a function that takes a struct:

```go
func area(r Rectangle) float64 {
	return r.Width * r.Height
}

area(rect)
```

A **method** is the same thing, but it **belongs to the type**:

```go
func (r Rectangle) Area() float64 {
	return r.Width * r.Height
}

rect.Area()    // call it with a dot, like rect.Width
```

The only new part is `(r Rectangle)` **before** the function name.
It's called the **receiver**. It means: *"This method belongs to `Rectangle`. Inside it, call the rectangle `r`."*

```
func (r Rectangle) Area() float64 {
     ─────┬─────   ─┬─    ───┬───
     belongs to    name   returns
```

Why is this nicer? `rect.Area()` reads like English: "rectangle's area".
You can also see all the things a type can do in one place.

## A full example

```go
type Rectangle struct {
	Width  float64
	Height float64
}

func (r Rectangle) Area() float64 {
	return r.Width * r.Height
}

func (r Rectangle) Perimeter() float64 {
	return 2 * (r.Width + r.Height)
}

func main() {
	rect := Rectangle{Width: 10, Height: 5}
	fmt.Println(rect.Area())       // 50
	fmt.Println(rect.Perimeter())  // 30
}
```

## Methods that change the value: pointer receiver

Remember Lesson 12: functions get a **copy**. The same is true for methods.
To **change** the original, use a pointer receiver `(a *Account)`:

```go
type Account struct {
	Owner   string
	Balance float64
}

// Only reads, so a normal receiver is fine
func (a Account) Show() {
	fmt.Printf("%s has %.2f\n", a.Owner, a.Balance)
}

// Changes the balance, so it needs a pointer receiver (*)
func (a *Account) Deposit(amount float64) {
	a.Balance += amount
}

acc := Account{Owner: "Asha", Balance: 100}
acc.Deposit(50)    // Go automatically passes &acc for you
acc.Show()         // Asha has 150.00
```

If you forget the `*` in `Deposit`, the deposit changes a copy and **your money disappears!** Try it in `main.go`.

### Simple rule

- The method **changes** the struct → use `*` (pointer receiver).
- The method only **reads** → either works. Many Go programmers use `*` for all methods of a type, to keep it consistent.

## A "constructor" function

Go has no special constructor. People write a normal function whose name starts with `New`:

```go
func NewAccount(owner string) *Account {
	return &Account{Owner: owner, Balance: 0}
}

acc := NewAccount("Ravi")
acc.Deposit(200)
```

## Methods on any type you define

Methods are not just for structs:

```go
type Celsius float64

func (c Celsius) ToFahrenheit() float64 {
	return float64(c)*9/5 + 32
}

temp := Celsius(30)
fmt.Println(temp.ToFahrenheit())   // 86
```

## Practice

1. Make a `Circle` struct with `Radius`. Add an `Area()` method (use `3.14 * r * r`).
2. Add a `Withdraw(amount float64)` method to `Account`. If there isn't enough money, print "Not enough balance" and don't change anything.
3. Make a `Counter` struct with a `Value int` field and an `Increment()` method. Call it 3 times and print the value (should be 3).

<details>
<summary>Answers</summary>

```go
type Circle struct {
	Radius float64
}

func (c Circle) Area() float64 {
	return 3.14 * c.Radius * c.Radius
}

func (a *Account) Withdraw(amount float64) {
	if amount > a.Balance {
		fmt.Println("Not enough balance")
		return
	}
	a.Balance -= amount
}

type Counter struct {
	Value int
}

func (c *Counter) Increment() {
	c.Value++
}
```
</details>

---

**Next:** [Lesson 14: Interfaces](../14_interfaces/)
