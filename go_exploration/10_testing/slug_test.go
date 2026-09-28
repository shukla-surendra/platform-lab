package textutil

import (
	"fmt"
	"os"
	"path/filepath"
	"strings"
	"testing"
	"unicode"
)

// 1. Table-driven test with subtests -- THE idiomatic Go test shape.
func TestSlugify(t *testing.T) {
	tests := []struct {
		name, in, want string
	}{
		{"simple", "Hello World", "hello-world"},
		{"punctuation", "Hello, World!", "hello-world"},
		{"collapse separators", "a  --  b", "a-b"},
		{"trim edges", "  --go--  ", "go"},
		{"digits", "Go 1.27 Release", "go-1-27-release"},
		{"unicode letters", "Café Olé", "café-olé"},
		{"empty", "", ""},
	}
	for _, tc := range tests {
		t.Run(tc.name, func(t *testing.T) { // go test -run 'TestSlugify/digits'
			t.Parallel() // subtests run concurrently
			if got := Slugify(tc.in); got != tc.want {
				t.Errorf("Slugify(%q) = %q, want %q", tc.in, got, tc.want)
			}
		})
	}
}

// 2. Helpers: t.Helper() makes failures point at the caller's line.
func writeFile(t *testing.T, content string) string {
	t.Helper()
	p := filepath.Join(t.TempDir(), "in.txt") // auto-deleted after the test
	if err := os.WriteFile(p, []byte(content), 0o644); err != nil {
		t.Fatal(err)
	}
	return p
}

func TestCountWordsInFile(t *testing.T) {
	p := writeFile(t, "one two\nthree")
	n, err := CountWordsInFile(p)
	if err != nil || n != 3 {
		t.Fatalf("got %d, %v", n, err)
	}

	if _, err := CountWordsInFile(filepath.Join(t.TempDir(), "missing")); err == nil {
		t.Fatal("expected error for missing file")
	}
}

// 3. Benchmark: go test -bench=. -benchmem ./10_testing
func BenchmarkSlugify(b *testing.B) {
	in := strings.Repeat("Hello, World! ", 20)
	for b.Loop() { // Go 1.24+: replaces `for i := 0; i < b.N; i++`
		Slugify(in)
	}
}

// 4. Example: compiled, run, and its output checked -- also shows up in `go doc`.
func ExampleSlugify() {
	fmt.Println(Slugify("Platform Lab: Go Edition"))
	// Output: platform-lab-go-edition
}

// 5. Fuzz test: go test -fuzz=FuzzSlugify -fuzztime=10s ./10_testing
// Without -fuzz it just runs the seed corpus like a normal test.
func FuzzSlugify(f *testing.F) {
	for _, seed := range []string{"Hello World", "--", "Ünïcödé 123", ""} {
		f.Add(seed)
	}
	f.Fuzz(func(t *testing.T, in string) {
		out := Slugify(in)
		// Properties that must hold for ANY input:
		if strings.HasPrefix(out, "-") || strings.HasSuffix(out, "-") {
			t.Errorf("edge dash: %q -> %q", in, out)
		}
		if strings.Contains(out, "--") {
			t.Errorf("double dash: %q -> %q", in, out)
		}
		for _, r := range out {
			if r != '-' && !unicode.IsLetter(r) && !unicode.IsDigit(r) {
				t.Errorf("bad rune %q in %q", r, out)
			}
		}
		if Slugify(out) != out {
			t.Errorf("not idempotent: %q -> %q -> %q", in, out, Slugify(out))
		}
	})
}
