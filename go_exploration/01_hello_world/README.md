# Lesson 01: Hello, World

**You will learn:** how to write your first Go program and run it.

---

## Step 1: Check that Go is installed

Open a terminal and type:

```bash
go version
```

You should see something like `go version go1.27.1 linux/amd64`.
If you see "command not found", install Go from https://go.dev/dl/ first.

## Step 2: Look at the program

Open `main.go` in this folder. It looks like this:

```go
package main

import "fmt"

func main() {
	fmt.Println("Hello, World!")
}
```

Here is what each line means:

| Line | Meaning in simple words |
|---|---|
| `package main` | "This file is a program you can run." Every runnable Go program starts with this. |
| `import "fmt"` | "I want to use the `fmt` toolbox." `fmt` (say "format") has tools for printing text. |
| `func main() { ... }` | "Start here." When you run the program, Go runs the code inside `main`. |
| `fmt.Println("Hello, World!")` | "Print this text on the screen, then go to a new line." |

## Step 3: Run it

From the `go_exploration` folder, run:

```bash
go run ./01_hello_world
```

Output:

```
Hello, World!
I am learning Go.
Go is simple.
```

**Done! You just ran your first Go program.**

## Two ways to run a program

| Command | What it does |
|---|---|
| `go run ./01_hello_world` | Builds and runs the program in one step. Use this while learning. |
| `go build -o hello ./01_hello_world` then `./hello` | Makes a program file called `hello` that you can run again and again, or copy to another computer. |

## Go is strict (and that is a good thing)

Go will **refuse to run** your program if:

- You `import` something and don't use it.
- You make a variable and don't use it.

At first this feels annoying. But it keeps your code clean.

## Practice

1. Change the text to print your own name.
2. Add one more `fmt.Println` line that prints your favourite food.
3. Delete the line `fmt.Println("Hello, World!")` and all the other `Println` lines. Run it. What error do you get? (Hint: `fmt` is imported but not used.)

---

**Next:** [Lesson 02: Variables](../02_variables/)
