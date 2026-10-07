# A very basic command-line tool in Go

A tiny program you run in the terminal. You type its name plus some options, and it prints a greeting. That's it. It exists so you can see, in the smallest possible example, how a Go command-line tool works.

Every output shown below was produced by running this exact program.

## What is a "command-line tool"?

You already use them: `ls`, `cd`, `git`. You type a name, maybe add some **options** (also called **flags**), press Enter, and something happens.

```
git commit -m "my message"
 ^    ^     ^  ^
 |    |     |  the value for that option
 |    |     an option (flag)
 |    a sub-word telling git what to do
 the program
```

Our tool is `greet`. Its options are `-name`, `-times` and `-shout`.

## What's in this folder

```
001_basic_cli_tool/
├── go.mod      the project's "ID card": its name (basiccli) and Go version
├── main.go     ALL the code (about 40 lines)
├── README.md   this file
└── .gitignore  tells git to ignore the built program (bin/)
```

## Run it

Open a terminal **inside this folder** (so `main.go` is right here), then:

```bash
go run .
```

`go run .` means "build the program in this folder and run it right now". The `.` means "this folder".

### Try the options

| You type | You get |
|---|---|
| `go run .` | `Hello, World!` |
| `go run . -name Sam` | `Hello, Sam!` |
| `go run . -name Sam -shout` | `HELLO, SAM!` |
| `go run . -name Sam -times 3` | `Hello, Sam!` three times |
| `go run . -help` | A list of all the options |

Real output:

```
$ go run . -name Sam -times 3
Hello, Sam!
Hello, Sam!
Hello, Sam!
```

### What happens with bad input?

```
$ go run . -times 0
error: -times must be 1 or more
```

```
$ go run . -times abc
invalid value "abc" for flag -times: parse error
Usage of ...:
  -name string
        who to greet (default "World")
  -shout
        print in UPPERCASE
  -times int
        how many times to print the greeting (default 1)
```

Go's `flag` package gives you the second message for free: it knows `-times` must be a number, so it complains and prints the help.

## Turn it into a real program (a file you can double-click or run anywhere)

`go run` builds the program in a hidden temporary place and throws it away afterwards. To keep an actual program file:

```bash
go build -o bin/greet .
./bin/greet -name Sam -shout
```

You now have a file called `bin/greet`. You can copy it to another computer with the same type of system and run it without Go installed.

## How the code works (read `main.go` next to this)

The program has **four steps**, marked 1 to 4 in the comments.

1. **Describe the options.** We tell Go what options our tool understands:

   ```go
   name := flag.String("name", "World", "who to greet")
   ```
   Read it as: "an option called `name`, holding text, with the default `World`, and this help text".
   `-times` is a whole number (`flag.Int`), `-shout` is a yes/no switch (`flag.Bool`).

2. **Read what the user typed.** `flag.Parse()`. Before this line the options are empty; after it they hold the user's values.

3. **Check the input.** If `-times` is less than 1, print an error and stop. `os.Exit(1)` stops the program and reports "something went wrong".

4. **Do the work.** Build the greeting (`makeGreeting`) and print it `times` times in a loop.

### The one strange thing: the `*`

`flag.String(...)` doesn't give you the text directly; it gives you **a note saying where the text is kept** (a "pointer"). The `*` in front (`*name`, `*times`, `*shout`) means "go and get the actual value from there". For now just remember: **when you read a flag's value, put a `*` in front.**

## Exit codes (how a program says "OK" or "problem")

Every program ends with a number, its **exit code**:

| Code | Meaning | When in our tool |
|---|---|---|
| `0` | Everything went fine | normal run |
| `1` | We hit a problem | `-times 0` (our own check) |
| `2` | You used the tool wrongly | `-times abc` (Go's `flag` package) |

You can see it yourself with the built program:

```bash
./bin/greet -times 0
echo $?          # prints 1  ($? means "exit code of the last command")
```

Other scripts and tools use this number to decide whether your tool succeeded. (With `go run`, the number you see can differ from the program's own, so check it with the built `bin/greet`.)

## Common beginner mistakes

| Mistake | What happens | Fix |
|---|---|---|
| Typing `go run main.go -name Sam` | Works here, but breaks as soon as you add a second file | Prefer `go run .` |
| Running from the wrong folder | `go: go.mod file not found` | `cd` into `001_basic_cli_tool` first |
| Forgetting the `*` (`fmt.Println(name)`) | Prints a strange address like `0xc000012345` | Use `*name` |
| Calling `flag.Parse()` before defining the flags | The options aren't recognised | Define flags first, parse second |
| Writing `--name Sam` vs `-name Sam` | Both work in Go's `flag` package | Use whichever you like |
| `-shout` with a value: `-shout false` | `false` is treated as a stray extra word | Write `-shout=false` for yes/no switches |

## Words to know

| Word | Simple meaning |
|---|---|
| **CLI** | Command-line interface: a program you use by typing |
| **flag / option** | Something extra you type after the program name, like `-name Sam` |
| **argument** | Any word you type after the program name |
| **default** | The value used when you don't type one |
| **build** | Turn your code into a program file |
| **pointer** | A note saying where a value is stored (that's why we use `*`) |
| **exit code** | The number a program ends with: 0 means OK |

## Try changing it (small exercises)

1. Add a flag `-punctuation` (text, default `!`) and use it instead of the fixed `!`.
2. Add a flag `-lower` that prints everything in lowercase (hint: `strings.ToLower`).
3. Make `-times` stop at 10 maximum and print an error if it's higher.
4. Move `makeGreeting` into its own package, as you did in `000_small_function_project`.

## What this tool deliberately does NOT do

No sub-commands (like `git commit`), no config files, no colours, no external libraries, no tests. Those are the next steps once this feels easy. Everything here uses only Go's built-in packages: `flag`, `fmt`, `os` and `strings`.
