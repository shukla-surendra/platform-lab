// Lesson 07: switch
//
// Run it with:  go run ./07_switch
package main

import "fmt"

func main() {
	// --- switch on a value ---
	day := "Sat"
	switch day {
	case "Mon":
		fmt.Println("Start of week")
	case "Fri":
		fmt.Println("Almost weekend")
	case "Sat", "Sun": // either value matches
		fmt.Println("Weekend!")
	default: // no case matched
		fmt.Println("Normal day")
	}

	// --- switch with conditions (no value after switch) ---
	marks := 72
	switch {
	case marks >= 90:
		fmt.Println("Grade A")
	case marks >= 70:
		fmt.Println("Grade B")
	case marks >= 50:
		fmt.Println("Grade C")
	default:
		fmt.Println("Fail")
	}

	// --- Seasons example ---
	for month := 1; month <= 12; month++ {
		season := ""
		switch month {
		case 12, 1, 2:
			season = "Winter"
		case 3, 4, 5:
			season = "Summer"
		case 6, 7, 8, 9:
			season = "Monsoon"
		default:
			season = "Autumn"
		}
		fmt.Printf("Month %2d -> %s\n", month, season)
	}
}
