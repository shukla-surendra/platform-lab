package main

import (
	"fmt"
	"strings"
)

// printTitle is in a separate file, but it's the same package as main.go,
// so main.go can use it directly.
func printTitle(title string) {
	fmt.Println(title)
	fmt.Println(strings.Repeat("=", len(title)))
}
