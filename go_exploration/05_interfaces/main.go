// Chapter 05 -- interfaces: implicit satisfaction, type switches, io.Reader/Writer.
//
//	go run ./05_interfaces
package main

import (
	"bytes"
	"fmt"
	"io"
	"math"
	"os"
	"strings"
)

// Define interfaces where they are USED, keep them small.
type Shape interface {
	Area() float64
	Perimeter() float64
}

type Rect struct{ W, H float64 }
type Circle struct{ R float64 }

// No `implements` keyword: having the methods IS implementing.
func (r Rect) Area() float64        { return r.W * r.H }
func (r Rect) Perimeter() float64   { return 2 * (r.W + r.H) }
func (c Circle) Area() float64      { return math.Pi * c.R * c.R }
func (c Circle) Perimeter() float64 { return 2 * math.Pi * c.R }

// fmt.Stringer -- implement String() and fmt uses it automatically.
func (r Rect) String() string { return fmt.Sprintf("Rect(%gx%g)", r.W, r.H) }

// Compile-time assertion that a type satisfies an interface.
var _ Shape = Rect{}
var _ fmt.Stringer = Rect{}

func TotalArea(shapes ...Shape) float64 {
	total := 0.0
	for _, s := range shapes {
		total += s.Area()
	}
	return total
}

// Describe uses a type switch on `any` (alias for interface{}).
func Describe(v any) string {
	switch x := v.(type) {
	case nil:
		return "nil"
	case int:
		return fmt.Sprintf("int %d", x)
	case string:
		return fmt.Sprintf("string of len %d", len(x))
	case Shape:
		return fmt.Sprintf("shape with area %.2f", x.Area())
	case error:
		return "error: " + x.Error()
	default:
		return fmt.Sprintf("other %T", x)
	}
}

// --- The most important interfaces in the stdlib: io.Reader / io.Writer ----

// UpperWriter wraps any io.Writer and upper-cases what passes through it.
type UpperWriter struct{ W io.Writer }

func (u UpperWriter) Write(p []byte) (int, error) {
	return u.W.Write(bytes.ToUpper(p))
}

// CountLines works with a file, a network connection, a string, an HTTP body...
func CountLines(r io.Reader) (int, error) {
	data, err := io.ReadAll(r)
	if err != nil {
		return 0, err
	}
	return bytes.Count(data, []byte("\n")), nil
}

func main() {
	shapes := []Shape{Rect{3, 4}, Circle{1}}
	for _, s := range shapes {
		fmt.Printf("%v  area=%.2f  %T\n", s, s.Area(), s)
	}
	fmt.Printf("total area: %.2f\n", TotalArea(shapes...))

	// Type assertion with comma-ok
	var s Shape = Circle{2}
	if c, ok := s.(Circle); ok {
		fmt.Println("it's a circle with radius", c.R)
	}
	_, isRect := s.(Rect)
	fmt.Println("is rect?", isRect)

	for _, v := range []any{42, "hello", Rect{1, 1}, fmt.Errorf("boom"), 3.5, nil} {
		fmt.Println(" ", Describe(v))
	}

	// Composition of readers and writers
	n, _ := CountLines(strings.NewReader("a\nb\nc\n"))
	fmt.Println("lines:", n)
	fmt.Fprintln(UpperWriter{os.Stdout}, "written through UpperWriter")
	var buf bytes.Buffer
	io.Copy(io.MultiWriter(&buf, UpperWriter{os.Stdout}), strings.NewReader("tee to two writers\n"))
	fmt.Print("buffer got: ", buf.String())

	// GOTCHA: an interface holding a nil pointer is NOT nil.
	var rp *Rect
	var sh Shape = rp
	fmt.Println("nil *Rect in Shape == nil?", sh == nil)
}
