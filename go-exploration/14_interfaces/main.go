// Lesson 14: Interfaces
//
// Run it with:  go run ./14_interfaces
package main

import "fmt"

// Shape is ANYTHING that has an Area() method.
type Shape interface {
	Area() float64
}

type Rectangle struct {
	Width, Height float64
}

type Circle struct {
	Radius float64
}

// Rectangle has Area(), so it is a Shape. No "implements" keyword needed.
func (r Rectangle) Area() float64 {
	return r.Width * r.Height
}

// Circle has Area(), so it is a Shape too.
func (c Circle) Area() float64 {
	return 3.14 * c.Radius * c.Radius
}

// Works with ANY Shape.
func printArea(s Shape) {
	fmt.Printf("Area: %.2f\n", s.Area())
}

// ----- Stringer -----

type Student struct {
	Name  string
	Marks int
}

// Because Student has String(), fmt.Println uses it.
func (s Student) String() string {
	return fmt.Sprintf("%s (%d marks)", s.Name, s.Marks)
}

// ----- any + type switch -----

func describe(x any) {
	switch v := x.(type) {
	case int:
		fmt.Println(v, "is an int, double is", v*2)
	case string:
		fmt.Printf("%q is a string of length %d\n", v, len(v))
	case Shape:
		fmt.Println("a Shape with area", v.Area())
	default:
		fmt.Printf("%v is something else (%T)\n", v, v)
	}
}

func main() {
	printArea(Rectangle{Width: 3, Height: 4})
	printArea(Circle{Radius: 2})

	// One list, different types
	shapes := []Shape{
		Rectangle{Width: 3, Height: 4},
		Circle{Radius: 2},
		Rectangle{Width: 1, Height: 1},
	}
	total := 0.0
	for _, s := range shapes {
		total += s.Area()
	}
	fmt.Printf("Total area of all shapes: %.2f\n", total)

	// Stringer
	fmt.Println(Student{Name: "Asha", Marks: 90})

	// any + type switch
	describe(42)
	describe("hello")
	describe(Circle{Radius: 1})
	describe(true)
}
