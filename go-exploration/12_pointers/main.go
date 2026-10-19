// Lesson 12: Pointers
//
// Run it with:  go run ./12_pointers
package main

import "fmt"

type Student struct {
	Name  string
	Marks int
}

// Gets a COPY: the original won't change.
func birthdayCopy(age int) {
	age = age + 1
}

// Gets an ADDRESS: the original will change.
func birthday(age *int) {
	*age = *age + 1
}

func addBonus(s *Student) {
	s.Marks += 5 // same as (*s).Marks += 5
}

func swap(a, b *int) {
	*a, *b = *b, *a
}

func main() {
	// --- The problem ---
	myAge := 25
	birthdayCopy(myAge)
	fmt.Println("after birthdayCopy:", myAge, "(unchanged)")

	// --- The fix ---
	birthday(&myAge)
	fmt.Println("after birthday:    ", myAge, "(changed!)")

	// --- & and * ---
	age := 25
	p := &age
	fmt.Println("p (the address):  ", p)
	fmt.Println("*p (the value):   ", *p)
	*p = 30
	fmt.Println("age after *p = 30:", age)
	fmt.Printf("type of p: %T\n", p)

	// --- Pointers to structs ---
	st := Student{Name: "Asha", Marks: 80}
	addBonus(&st)
	fmt.Printf("after bonus: %+v\n", st)

	// --- Swap ---
	x, y := 1, 2
	swap(&x, &y)
	fmt.Println("after swap: x =", x, "y =", y)

	// --- nil ---
	var empty *int
	fmt.Println("empty pointer is nil?", empty == nil)
	if empty != nil {
		fmt.Println(*empty) // safe: we only get here if it's not nil
	}
}
