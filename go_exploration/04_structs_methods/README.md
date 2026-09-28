# 04 · Structs and methods

```bash
go run ./04_structs_methods
go test ./04_structs_methods
```

Go has no classes. You define a **struct** for the data and attach
**methods** to the type.

```go
type Pod struct {
    Name     string `json:"name"`
    Restarts int    `json:"restarts"`
}
func (p Pod)  FullName() string { ... } // value receiver
func (p *Pod) Restart()         { ... } // pointer receiver
```

## Value vs pointer receiver: how to choose

| Use a **pointer** receiver `*T` when… | A **value** receiver `T` is fine when… |
|---|---|
| the method mutates the receiver | it only reads |
| the struct is large (avoid copying) | the type is small and immutable-ish (`time.Time`) |
| the struct holds a `sync.Mutex` (must not be copied) | |

**Rule of thumb:** if any method needs a pointer, make them *all* pointers
for consistency. Go automatically takes `&p` when you call a pointer method
on an addressable value.

## Construction

There are no constructors. Use a composite literal `Pod{Name: "x"}` (unset
fields get their zero values), or by convention a `NewPod(...) *Pod`
function when setup is needed, for example to initialise a map.

## Struct tags

The backtick strings are metadata that libraries read through reflection:
`json:"name,omitempty"`, `yaml:"..."`, `db:"..."`. **Only exported
(capitalised) fields** get encoded. Lowercase fields are invisible to
`encoding/json`.

## Embedding: composition, not inheritance

```go
type Deployment struct {
    Metadata          // no field name → embedded
    Name string
}
d.Owner       // promoted field  (= d.Metadata.Owner)
d.Age(now)    // promoted method
```

A `Deployment` is **not** a `Metadata`. You can't pass it where a
`Metadata` is expected. What you can do is satisfy *interfaces* through
promoted methods, which is the subject of the next chapter.

## Try it

1. Change `Restart` to a value receiver. Which test fails, and why?
2. Add `omitempty` to `Restarts` and marshal a fresh pod.
