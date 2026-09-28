// Package textutil is chapter 10's code under test. It's a library package
// (no main) -- run it with `go test`, not `go run`.
package textutil

import (
	"os"
	"strings"
	"unicode"
)

// Slugify turns "Hello, World!" into "hello-world": lowercase letters and
// digits, single dashes between words, no leading/trailing dash.
func Slugify(s string) string {
	var b strings.Builder
	dash := false
	for _, r := range strings.ToLower(s) {
		switch {
		case unicode.IsLetter(r) || unicode.IsDigit(r):
			if dash && b.Len() > 0 {
				b.WriteByte('-')
			}
			b.WriteRune(r)
			dash = false
		default:
			dash = true
		}
	}
	return b.String()
}

// CountWordsInFile reads a file and returns its whitespace-separated word count.
func CountWordsInFile(path string) (int, error) {
	data, err := os.ReadFile(path)
	if err != nil {
		return 0, err
	}
	return len(strings.Fields(string(data))), nil
}
