// Package smoll_utils is a tiny package with one function, to practise
// splitting code into a separate file/package and importing it.
package smoll_utils

// Greet returns a greeting for the given name.
//
// It starts with a CAPITAL letter, so it is "exported": code in other
// packages (like main) can use it. A lowercase name (greet) would be private
// to this package.
func Greet(name string) string {
	return "Hello, " + name + "!"
}
