# Lesson 07: switch (a cleaner if / else)

**You will learn:** how to choose between many options without writing a long `if / else if` chain.

```bash
go run ./07_switch
```

---

## The problem

This works, but it's long and hard to read:

```go
if day == "Mon" {
	fmt.Println("Start of week")
} else if day == "Fri" {
	fmt.Println("Almost weekend")
} else if day == "Sat" {
	fmt.Println("Weekend!")
} else if day == "Sun" {
	fmt.Println("Weekend!")
} else {
	fmt.Println("Normal day")
}
```

## The solution: switch

```go
switch day {
case "Mon":
	fmt.Println("Start of week")
case "Fri":
	fmt.Println("Almost weekend")
case "Sat", "Sun":
	fmt.Println("Weekend!")
default:
	fmt.Println("Normal day")
}
```

How to read it: *"Look at `day`. If it's `"Mon"`, do this. If it's `"Fri"`, do that…"*

- `case "Sat", "Sun":` means **either** value matches.
- `default:` runs when **no case** matches, just like `else`.
- Go stops after the first matching case. **You don't need `break`**. (Other languages like C and Java need it.)

## Switch with conditions

You can leave out the value after `switch` and put a condition in each `case`:

```go
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
```

This does the same thing as the `if / else if` in Lesson 05, but it's easier to read.

## When to use which?

- **2 choices** → use `if / else`
- **3 or more choices** → use `switch`

## Practice

1. Make `month := 2`. Use `switch` to print the season: 12, 1, 2 → "Winter"; 3, 4, 5 → "Summer"; 6 to 9 → "Monsoon"; everything else → "Autumn".
2. Make `speed := 85`. Use a `switch` with no value: under 40 → "Slow", 40–80 → "Normal", over 80 → "Too fast!".

<details>
<summary>Answers</summary>

```go
month := 2
switch month {
case 12, 1, 2:
	fmt.Println("Winter")
case 3, 4, 5:
	fmt.Println("Summer")
case 6, 7, 8, 9:
	fmt.Println("Monsoon")
default:
	fmt.Println("Autumn")
}

speed := 85
switch {
case speed < 40:
	fmt.Println("Slow")
case speed <= 80:
	fmt.Println("Normal")
default:
	fmt.Println("Too fast!")
}
```
</details>

---

🎉 **Part 1 done!** You now know the basics: variables, printing, math, decisions and loops.
With just these, you can already write small useful programs.

**Next:** [Lesson 08: Functions](../08_functions/)
