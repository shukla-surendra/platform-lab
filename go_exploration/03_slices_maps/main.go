// Chapter 03 -- arrays, slices (and their sharing gotcha), maps.
//
//	go run ./03_slices_maps
package main

import (
	"fmt"
	"maps"
	"slices"
	"sort"
	"strings"
)

func main() {
	// Arrays: fixed size, part of the type, copied on assignment.
	arr := [3]int{1, 2, 3}
	arrCopy := arr
	arrCopy[0] = 99
	fmt.Println("array is a value:", arr, arrCopy)

	// Slices: a view (pointer, len, cap) onto an underlying array.
	s := make([]int, 3, 5) // len 3, cap 5
	fmt.Printf("make: %v len=%d cap=%d\n", s, len(s), cap(s))

	// append grows; when cap is exceeded it allocates a NEW backing array.
	var grow []int // nil slice: len 0, still usable with append
	for i := range 6 {
		grow = append(grow, i)
		fmt.Printf("  len=%d cap=%d\n", len(grow), cap(grow))
	}

	// GOTCHA: sub-slices share the backing array.
	base := []int{1, 2, 3, 4, 5}
	view := base[1:3] // [2 3], cap 4 (runs to end of base)
	view[0] = 20
	view = append(view, 40) // still within cap -> overwrites base[3]!
	fmt.Println("shared backing:", base, view)

	// Fix: full slice expression caps it, or clone.
	safe := slices.Clone(base[1:3])
	safe = append(safe, 999)
	fmt.Println("after clone+append base unchanged:", base, safe)

	// slices package (1.21+)
	xs := []int{5, 2, 8, 2, 9}
	slices.Sort(xs)
	idx, found := slices.BinarySearch(xs, 8)
	fmt.Println("sorted:", xs, "8 at", idx, found, "| contains 7?", slices.Contains(xs, 7))
	fmt.Println("compact:", slices.Compact(xs))

	// 2D slice
	grid := make([][]rune, 2)
	for i := range grid {
		grid[i] = []rune(strings.Repeat(".", 3))
	}
	grid[1][2] = '#'
	for _, row := range grid {
		fmt.Println(string(row))
	}

	// Maps: hash tables. Zero value is nil -- reading OK, writing panics.
	ages := map[string]int{"alice": 31, "bob": 25}
	ages["carol"] = 40
	delete(ages, "bob")
	v, ok := ages["bob"] // comma-ok distinguishes "missing" from zero value
	fmt.Println("bob:", v, ok, "| len:", len(ages))

	// Iteration order is RANDOMISED on purpose -- sort the keys for stable output.
	keys := slices.Sorted(maps.Keys(ages))
	for _, k := range keys {
		fmt.Printf("  %s=%d\n", k, ages[k])
	}

	fmt.Println(TopWords("the cat and the hat and the bat", 2))
}

// WordCount counts words case-insensitively.
func WordCount(text string) map[string]int {
	counts := make(map[string]int)
	for _, w := range strings.Fields(strings.ToLower(text)) {
		counts[w]++ // missing key reads as 0
	}
	return counts
}

// TopWords returns the n most frequent words, ties broken alphabetically.
func TopWords(text string, n int) []string {
	counts := WordCount(text)
	words := slices.Collect(maps.Keys(counts))
	sort.Slice(words, func(i, j int) bool {
		if counts[words[i]] != counts[words[j]] {
			return counts[words[i]] > counts[words[j]]
		}
		return words[i] < words[j]
	})
	return words[:min(n, len(words))]
}
