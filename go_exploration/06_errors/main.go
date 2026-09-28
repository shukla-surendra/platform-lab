// Chapter 06 -- errors are values: sentinel errors, wrapping, errors.Is / errors.As.
//
//	go run ./06_errors
package main

import (
	"errors"
	"fmt"
	"io/fs"
	"os"
	"strconv"
)

// Sentinel error: a package-level value callers compare against with errors.Is.
var ErrNotFound = errors.New("not found")

// Custom error type: carries structured data; callers extract it with errors.As.
type ValidationError struct {
	Field string
	Value any
}

func (e *ValidationError) Error() string {
	return fmt.Sprintf("invalid %s: %v", e.Field, e.Value)
}

var users = map[int]string{1: "alice", 2: "bob"}

func FindUser(id int) (string, error) {
	if id <= 0 {
		return "", &ValidationError{Field: "id", Value: id}
	}
	name, ok := users[id]
	if !ok {
		// %w WRAPS the sentinel: message gets context, identity is preserved.
		return "", fmt.Errorf("find user %d: %w", id, ErrNotFound)
	}
	return name, nil
}

// LookupFromInput adds another layer of context on top.
func LookupFromInput(raw string) (string, error) {
	id, err := strconv.Atoi(raw)
	if err != nil {
		return "", fmt.Errorf("parse id %q: %w", raw, err)
	}
	name, err := FindUser(id)
	if err != nil {
		return "", fmt.Errorf("lookup: %w", err)
	}
	return name, nil
}

// Classify shows how a caller reacts to different error kinds.
func Classify(err error) string {
	var ve *ValidationError
	var ne *strconv.NumError
	switch {
	case err == nil:
		return "ok"
	case errors.Is(err, ErrNotFound): // walks the wrap chain
		return "404"
	case errors.As(err, &ve): // finds the first *ValidationError in the chain
		return "400 field=" + ve.Field
	case errors.As(err, &ne):
		return "400 bad number"
	default:
		return "500"
	}
}

func main() {
	for _, in := range []string{"1", "7", "-3", "abc"} {
		name, err := LookupFromInput(in)
		fmt.Printf("%-5q -> name=%-6q class=%-15s err=%v\n", in, name, Classify(err), err)
	}

	// Stdlib uses the same pattern: os errors wrap fs.ErrNotExist.
	_, err := os.Open("/definitely/not/here")
	fmt.Println("os.Open:", err, "| is ErrNotExist?", errors.Is(err, fs.ErrNotExist))

	// errors.Join combines several errors (e.g. validating many fields).
	joined := errors.Join(&ValidationError{"name", ""}, &ValidationError{"age", -1})
	fmt.Printf("joined:\n%v\n", joined)
}
