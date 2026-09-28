# 05 · Interfaces

```bash
go run ./05_interfaces
go test ./05_interfaces
```

An interface is a **set of method signatures**. A type satisfies it
**implicitly**, just by having those methods. There is no `implements`
keyword.

```go
type Shape interface { Area() float64; Perimeter() float64 }
type Rect struct{ W, H float64 }
func (r Rect) Area() float64      { ... }
func (r Rect) Perimeter() float64 { ... }
// Rect is now a Shape. Rect's package never mentions Shape.
```

Because satisfaction is implicit, you can **define an interface in the
consumer package** to describe only what you need, even for a type from a
library you don't control. That makes tests easy: accept an interface,
then pass a fake.

> "Accept interfaces, return structs." Keep interfaces small: 1–3 methods.

Force a compile-time check with `var _ Shape = Rect{}`.

## The interfaces you'll use constantly

| Interface | Method | Implemented by |
|---|---|---|
| `io.Reader` | `Read(p []byte) (n int, err error)` | files, network conns, HTTP bodies, `strings.Reader`, gzip… |
| `io.Writer` | `Write(p []byte) (n int, err error)` | files, `os.Stdout`, `bytes.Buffer`, HTTP responses, hashes… |
| `fmt.Stringer` | `String() string` | anything you want `fmt` to print nicely |
| `error` | `Error() string` | every error |

Since everything speaks `Reader`/`Writer`, pieces compose. For example,
`io.Copy(io.MultiWriter(file, hash), gzip.NewReader(resp.Body))`.

## Getting the concrete type back

```go
c, ok := s.(Circle)        // type assertion; without ok it panics on mismatch
switch x := v.(type) {     // type switch
case int:    ...
case Shape:  ...           // cases can be interfaces too
}
```

`any` is an alias for `interface{}`, the empty interface that everything
satisfies. Use it sparingly. Generics (chapter 07) usually fit better.

## Gotcha: the nil interface

An interface value is a pair **(type, value)**. It's `nil` only when **both**
parts are nil.

```go
var rp *Rect           // nil pointer
var sh Shape = rp      // (type=*Rect, value=nil)
sh == nil              // false!
```

This usually bites when a function returns a typed-nil `*MyError` as an
`error`. Return a literal `nil` instead.

## Try it

1. Add a `Triangle` and pass it to `TotalArea` without touching `TotalArea`.
2. Write a `LineCounter` that implements `io.Writer` and counts newlines written to it.
