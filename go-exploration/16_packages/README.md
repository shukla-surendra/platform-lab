# Lesson 16: Packages and Modules

**You will learn:** how to split your code into many files and folders, and how Go finds them.

```bash
go run ./16_packages
```

---

## Why split code?

A 5,000-line `main.go` is hard to read. So we split it:

- into **several files** (same folder)
- into **packages** (different folders)

## Words to know

| Word | Simple meaning |
|---|---|
| **package** | a **folder** of Go files that belong together |
| **module** | your whole **project**. It's the folder that has a `go.mod` file. |
| **import** | "I want to use that package here" |

## Look at this lesson's folder

```
16_packages/
├── main.go          package main   <- the program starts here
├── helpers.go       package main   <- same folder, same package
└── calc/
    └── calc.go      package calc   <- a different package (a toolbox)
```

## Rule 1: Files in the same folder share everything

`main.go` and `helpers.go` are both `package main`.
So `main.go` can call `printTitle()` from `helpers.go` **without importing anything**.
To Go, they are like one big file.

When a folder has more than one file, run the **folder**, not a single file:

```bash
go run ./16_packages        # correct: uses all files in the folder
go run 16_packages/main.go  # ERROR: can't find printTitle (helpers.go was left out)
```

## Rule 2: Capital letter = public, small letter = private

Inside `calc/calc.go`:

```go
package calc

func Add(a, b int) int { ... }      // Capital A -> other packages CAN use it
func secret() string { ... }        // small s  -> only the calc package can use it
```

That's all. Go has **no** `public` or `private` keywords. **The first letter decides.**
The same rule works for types, struct fields, constants and variables.

## Rule 3: Import a package by its full path

Open `go.mod` (in the `go_exploration` folder):

```
module platformlab/go_exploration
```

This is the **module name**. To import `calc`, write the module name + the folder path:

```go
import "platformlab/go_exploration/16_packages/calc"

calc.Add(2, 3)   // use it as packageName.Function
```

## Making a new project from scratch

When you start your own project in an empty folder:

```bash
mkdir myapp && cd myapp
go mod init myapp        # creates go.mod
# write main.go ...
go run .
```

The module name can be anything. For code you share on GitHub, people usually use the repo path, for example `github.com/yourname/myapp`.

## Using other people's packages

Go has a big standard library (`fmt`, `strings`, `net/http`, …). For anything else, download a package:

```bash
go get github.com/google/uuid     # download it and add it to go.mod
```

```go
import "github.com/google/uuid"

id := uuid.New()
```

Useful commands:

```bash
go mod tidy     # add missing packages, remove unused ones (run it often)
```

You'll see a `go.sum` file appear. It stores checksums (a kind of fingerprint) of the downloaded packages. Commit both `go.mod` and `go.sum` to git.

## Summary

- A **folder** = a **package**.
- All files in a folder use the same `package name` line.
- **Capital** first letter = usable outside the package.
- `go.mod` = your project's name and its dependencies.
- Import path = module name + folder path.

## Practice

1. Add a `Multiply(a, b int) int` function to `calc/calc.go` and call it from `main.go`.
2. Rename `Add` to `add` (small letter). Run it. What error do you get? Change it back.
3. Create a new package `16_packages/greet` with a function `Hello(name string) string`. Import it in `main.go` and use it.

---

**Next:** [Lesson 17: Generics](../17_generics/)
