# Lesson 11: Structs (your own types)

**You will learn:** how to group related values into one thing, like a form with fields.

```bash
go run ./11_structs
```

---

## The problem

Say you want to store a student. Without structs:

```go
studentName := "Asha"
studentAge := 20
studentMarks := 88.5
// And for a second student? name2, age2, marks2... messy!
```

## The solution: a struct

A struct is like a **form** with fields to fill in:

```
 ┌──────── Student ────────┐
 │ Name:   Asha            │
 │ Age:    20              │
 │ Marks:  88.5            │
 └─────────────────────────┘
```

### Step 1: Describe the form (define the type)

```go
type Student struct {
	Name  string
	Age   int
	Marks float64
}
```

This creates a **new type** called `Student`. Write it **outside** `main`, at the top of the file.

### Step 2: Fill in the form (create a value)

```go
s := Student{
	Name:  "Asha",
	Age:   20,
	Marks: 88.5,
}
```

### Step 3: Read and change fields using a dot `.`

```go
fmt.Println(s.Name)   // Asha
s.Marks = 91          // change a field
```

## Printing a struct

```go
fmt.Println(s)          // {Asha 20 91}
fmt.Printf("%+v\n", s)  // {Name:Asha Age:20 Marks:91}   <- shows field names
```

`%+v` is very handy for checking what's inside.

## Fields you leave out get zero values

```go
s2 := Student{Name: "Ravi"}
// s2.Age is 0, s2.Marks is 0
```

## A list of structs

This is very common: a slice of structs is like a **table**.

```go
students := []Student{
	{Name: "Asha", Age: 20, Marks: 88.5},
	{Name: "Ravi", Age: 21, Marks: 72},
	{Name: "Meena", Age: 19, Marks: 95},
}

for _, st := range students {
	fmt.Printf("%-6s scored %.1f\n", st.Name, st.Marks)
}
```

## A struct inside a struct

```go
type Address struct {
	City    string
	Pincode string
}

type Person struct {
	Name    string
	Address Address   // a field that is itself a struct
}

p := Person{
	Name:    "Asha",
	Address: Address{City: "Pune", Pincode: "411001"},
}
fmt.Println(p.Address.City)   // Pune
```

## Passing a struct to a function

```go
func describe(s Student) string {
	return fmt.Sprintf("%s (%d years)", s.Name, s.Age)
}
```

**Note:** the function gets a **copy** of the struct. If it changes `s.Age`, the original is **not** changed.
The next lesson (pointers) shows how to change the original.

## Capital letters matter

`Name` (capital N) can be used by **other packages**.
`name` (small n) can only be used inside **this package**.
For now, just use capital letters for struct fields. Lesson 16 explains this properly.

## Practice

1. Make a `Book` struct with `Title`, `Author`, and `Pages`. Create one book and print it with `%+v`.
2. Make a slice of 3 books. Print only the books with more than 300 pages.
3. Write `func totalPages(books []Book) int` that adds up all the pages.

<details>
<summary>Answers</summary>

```go
type Book struct {
	Title  string
	Author string
	Pages  int
}

func totalPages(books []Book) int {
	total := 0
	for _, b := range books {
		total += b.Pages
	}
	return total
}

func main() {
	b := Book{Title: "Go Basics", Author: "Asha", Pages: 250}
	fmt.Printf("%+v\n", b)

	books := []Book{
		{"Go Basics", "Asha", 250},
		{"Big Go", "Ravi", 520},
		{"Go Web", "Meena", 340},
	}
	for _, b := range books {
		if b.Pages > 300 {
			fmt.Println(b.Title)
		}
	}
	fmt.Println(totalPages(books))
}
```
</details>

---

**Next:** [Lesson 12: Pointers](../12_pointers/)
