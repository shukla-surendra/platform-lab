// A very small command-line tool: it prints a greeting.
//
// Try:
//
//	go run .
//	go run . -name Sam
//	go run . -name Sam -shout
//	go run . -name Sam -times 3
//	go run . -help
package main

import (
	"flag"    // reads options typed after the program name, like -name Sam
	"fmt"     // prints text to the screen
	"os"      // lets us stop the program with an error code
	"strings" // helpers for text, like making it UPPERCASE
)

// makeGreeting builds the text we are going to print.
func makeGreeting(name string, shout bool) string {
	message := "Hello, " + name + "!"
	if shout {
		message = strings.ToUpper(message)
	}
	return message
}

func main() {
	// 1. Describe the options our tool understands.
	//    Each line: flag.Type("option-name", default-value, "help text")
	name := flag.String("name", "World", "who to greet")
	times := flag.Int("times", 1, "how many times to print the greeting")
	shout := flag.Bool("shout", false, "print in UPPERCASE")

	// 2. Read what the user actually typed. Must come AFTER the lines above.
	flag.Parse()

	// 3. Check the input. If it makes no sense, say so and stop.
	if *times < 1 {
		fmt.Fprintln(os.Stderr, "error: -times must be 1 or more")
		os.Exit(1) // a non-zero number means "something went wrong"
	}

	// 4. Do the work. The * gets the value out of each option.
	message := makeGreeting(*name, *shout)
	for i := 0; i < *times; i++ {
		fmt.Println(message)
	}
}
