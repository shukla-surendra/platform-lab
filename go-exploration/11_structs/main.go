// Lesson 11: Structs
//
// Run it with:  go run ./11_structs
package main

import "fmt"

// Step 1: describe the form
type Student struct {
	Name  string
	Age   int
	Marks float64
}

type Address struct {
	City    string
	Pincode string
}

type Person struct {
	Name    string
	Address Address // a struct inside a struct
}

func describe(s Student) string {
	return fmt.Sprintf("%s (%d years)", s.Name, s.Age)
}

func main() {
	// Step 2: fill in the form
	s := Student{
		Name:  "Asha",
		Age:   20,
		Marks: 88.5,
	}

	// Step 3: read and change fields
	fmt.Println("Name:", s.Name)
	s.Marks = 91
	fmt.Println(s)
	fmt.Printf("%+v\n", s) // with field names

	// Missing fields get zero values
	s2 := Student{Name: "Ravi"}
	fmt.Printf("%+v\n", s2)

	// A list of structs = a table
	students := []Student{
		{Name: "Asha", Age: 20, Marks: 88.5},
		{Name: "Ravi", Age: 21, Marks: 72},
		{Name: "Meena", Age: 19, Marks: 95},
	}
	fmt.Println("--- students ---")
	for _, st := range students {
		fmt.Printf("%-6s scored %.1f\n", st.Name, st.Marks)
	}

	// Find the top student
	best := students[0]
	for _, st := range students {
		if st.Marks > best.Marks {
			best = st
		}
	}
	fmt.Println("Top student:", best.Name)

	// Nested struct
	p := Person{
		Name:    "Asha",
		Address: Address{City: "Pune", Pincode: "411001"},
	}
	fmt.Println(p.Name, "lives in", p.Address.City)

	// Passing to a function
	fmt.Println(describe(s))
}
