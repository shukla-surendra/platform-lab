# Learn Go, Step by Step

A beginner-friendly Go course: **24 small lessons**, from "Hello, World" to a real project.

- Each lesson teaches **one idea**, in simple words.
- Each lesson is **a little harder** than the one before.
- Each lesson has a **`README.md`** (read this first) and a **`main.go`** (run it and change it).
- Each lesson ends with **practice tasks**, and most have answers you can open.

You don't need to know any other programming language.

---

## Before you start

**1. Install Go** from https://go.dev/dl/ and check it works:

```bash
go version
```

**2. Open a terminal in this folder** (`go_exploration`).

**3. Run a lesson:**

```bash
go run ./01_hello_world
```

That's all the setup you need.

## How to study each lesson

1. Read the lesson's `README.md`.
2. Run it: `go run ./<lesson-folder>`
3. Open `main.go`, **change something**, and run it again. Break it on purpose and read the error.
4. Do the **Practice** tasks at the bottom of the README.

Don't rush. Typing the code yourself teaches more than reading it.

---

## Part 1: First steps

Start here if you've never written Go.

| # | Lesson | You will learn |
|---|---|---|
| 01 | [Hello, World](01_hello_world/) | write and run your first program |
| 02 | [Variables](02_variables/) | store values: text, numbers, true/false |
| 03 | [Printing](03_printing/) | `Println` vs `Printf`, and a very common mistake |
| 04 | [Math and text](04_math_and_strings/) | `+ - * /`, working with text, changing types |
| 05 | [if / else](05_if_else/) | making decisions |
| 06 | [Loops](06_loops/) | repeating things with `for` |
| 07 | [switch](07_switch/) | choosing between many options |

## Part 2: Organising code and data

| # | Lesson | You will learn |
|---|---|---|
| 08 | [Functions](08_functions/) | reusable blocks of code, returning values |
| 09 | [Arrays and slices](09_arrays_and_slices/) | lists of values |
| 10 | [Maps](10_maps/) | look things up by name (like a dictionary) |
| 11 | [Structs](11_structs/) | make your own types (like a form with fields) |
| 12 | [Pointers](12_pointers/) | change the original, not a copy |
| 13 | [Methods](13_methods/) | functions that belong to a type |
| 14 | [Interfaces](14_interfaces/) | one function that works with many types |
| 15 | [Errors](15_errors/) | handling things that go wrong, the Go way |
| 16 | [Packages](16_packages/) | split code into files and folders |
| 17 | [Generics](17_generics/) | one function for many types, without copy-paste |

## Part 3: Doing many things at once

| # | Lesson | You will learn |
|---|---|---|
| 18 | [Goroutines](18_goroutines/) | run functions at the same time |
| 19 | [Channels](19_channels/) | send data between goroutines |
| 20 | [Mutex](20_mutex/) | safely share a variable |
| 21 | [Context](21_context/) | cancel work or give it a time limit |

## Part 4: Building real things

| # | Lesson | You will learn |
|---|---|---|
| 22 | [Testing](22_testing/) | write code that checks your code |
| 23 | [Web server](23_web_server/) | build a small JSON API |
| 24 | [Final project](24_final_project/) | a website checker that uses everything you learned |

## After the course

[`taskapi/`](taskapi/) is a **real-world project**: a REST API with a Postgres database, a clean folder layout, tests, and Docker.
It shows how professionals organise a Go application. Study it after Lesson 24.

`00_exploration/` is a scratch folder for your own experiments.

---

## Commands you'll use

```bash
go run ./06_loops          # run a lesson
go build -o myapp ./24_final_project   # make a program file
go fmt ./...               # auto-format all code (Go has one standard style)
go vet ./...               # find common mistakes
go test ./22_testing       # run tests (Lesson 22)
go doc strings             # read the docs for a package in the terminal
```

## Getting stuck?

- **Read the error message slowly.** Go's errors usually say exactly which file, which line, and what's wrong.
- **Go's official tour:** https://go.dev/tour
- **Go by Example** (short recipes): https://gobyexample.com
