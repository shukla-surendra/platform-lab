# 06 · Errors

```bash
go run ./06_errors
go test ./06_errors
```

Go has no exceptions for ordinary failures. A function that can fail
**returns an `error`** as its last value, and the caller handles it right there.

```go
name, err := FindUser(id)
if err != nil {
    return "", fmt.Errorf("lookup: %w", err)   // add context, pass it up
}
```

`error` is just an interface: `type error interface { Error() string }`.

## Three kinds of errors

| Kind | Define | Caller checks with |
|---|---|---|
| Ad-hoc | `errors.New("boom")`, `fmt.Errorf("...")` | only the message (don't match on strings!) |
| **Sentinel** | `var ErrNotFound = errors.New("not found")` | `errors.Is(err, ErrNotFound)` |
| **Custom type** | `type ValidationError struct{...}` + `Error()` | `errors.As(err, &ve)` then read fields |

## Wrapping: `%w`

```
"lookup: find user 42: not found"
   │            │            └── ErrNotFound (sentinel)
   │            └── wrapped by FindUser
   └── wrapped by LookupFromInput
```

`fmt.Errorf("...: %w", err)` builds a chain. `errors.Is` and `errors.As`
walk the chain, so wrapping adds context **without** hiding what the error
was. `%v` instead of `%w` flattens it to text, and the identity is lost.

Convention: messages are lowercase, have no trailing punctuation, and each
layer adds *its* context (`"parse config: open file: permission denied"`).

## Rules of thumb

- Handle an error **or** return it, not both. Logging it and then returning
  it produces duplicate log lines.
- Don't `panic` for expected failures (bad input, missing file, network down).
- `errors.Join(e1, e2)` bundles several errors, which is useful for validation.
- The stdlib uses these same tools: `errors.Is(err, fs.ErrNotExist)`,
  `errors.Is(err, context.DeadlineExceeded)`.

## Try it

1. Add `ErrPermission` and make user id 2 return it. Map it to "403" in `Classify`.
2. Replace `%w` with `%v` in `FindUser` and run the tests. Which one fails?
