package main

import (
	"fmt"

	// module name (from THIS folder's go.mod) + folder path of the package
	"smollproject/smoll_utils"
)

func main() {
	fmt.Println("Hello, Go!")
	fmt.Println(smoll_utils.Greet("Surendra"))
}
