# Lesson 05: if / else (making decisions)

**You will learn:** how to make your program do different things in different situations.

```bash
go run ./05_if_else
```

---

## The idea

In real life: *"**If** it is raining, take an umbrella. **Otherwise**, wear sunglasses."*

In Go:

```go
raining := true

if raining {
	fmt.Println("Take an umbrella")
} else {
	fmt.Println("Wear sunglasses")
}
```

**Rules:**
- No brackets `( )` around the condition.
- Curly braces `{ }` are **always** required.
- `else` must be on the same line as the closing `}`.

## Comparing values

| Symbol | Meaning | Example |
|---|---|---|
| `==` | equal to | `age == 18` |
| `!=` | not equal to | `name != ""` |
| `>` | greater than | `score > 50` |
| `<` | less than | `price < 100` |
| `>=` | greater than or equal | `age >= 18` |
| `<=` | less than or equal | `items <= 10` |

**Careful:** `=` puts a value in a box. `==` asks "are these equal?"

## More than two choices: else if

```go
marks := 72

if marks >= 90 {
	fmt.Println("Grade A")
} else if marks >= 70 {
	fmt.Println("Grade B")
} else if marks >= 50 {
	fmt.Println("Grade C")
} else {
	fmt.Println("Fail")
}
// prints: Grade B
```

Go checks from **top to bottom** and runs only the **first** block that matches.

## Combining conditions

| Symbol | Meaning | Example |
|---|---|---|
| `&&` | AND: both must be true | `age >= 18 && hasTicket` |
| `\|\|` | OR: at least one must be true | `isWeekend \|\| isHoliday` |
| `!` | NOT: flips true/false | `!isRaining` |

```go
age := 20
hasTicket := true

if age >= 18 && hasTicket {
	fmt.Println("You can enter")
}
```

## Bonus: a short variable inside if

You'll see this pattern a lot in Go code:

```go
if length := len("hello"); length > 3 {
	fmt.Println("Long word, length is", length)
}
```

It means: *"Make `length`, then check `length > 3`."*
The variable `length` only exists inside this `if`.
We'll use this pattern a lot with errors in Lesson 15.

## Practice

1. Make `temperature := 35`. Print "Hot" if it's above 30, "Nice" if it's 15 to 30, and "Cold" otherwise.
2. Make `num := 7`. Print whether it's even or odd. (Hint: `num % 2 == 0` means even.)
3. A shop gives a discount if you spend more than 1000 **or** you are a member. Write the `if`.

<details>
<summary>Answers</summary>

```go
temperature := 35
if temperature > 30 {
	fmt.Println("Hot")
} else if temperature >= 15 {
	fmt.Println("Nice")
} else {
	fmt.Println("Cold")
}

num := 7
if num%2 == 0 {
	fmt.Println("Even")
} else {
	fmt.Println("Odd")
}

spent := 800
isMember := true
if spent > 1000 || isMember {
	fmt.Println("You get a discount!")
}
```
</details>

---

**Next:** [Lesson 06: Loops](../06_loops/)
