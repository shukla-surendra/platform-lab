# Lesson 06: Loops (repeating things)

**You will learn:** how to run the same code many times.

```bash
go run ./06_loops
```

---

## Go has only ONE loop: `for`

Other languages have `for`, `while`, and `do-while`. Go has only `for`.
You can write it in a few different shapes.

## Shape 1: Repeat N times (the easiest)

```go
for i := range 5 {
	fmt.Println("Hello", i)
}
```

Output:

```
Hello 0
Hello 1
Hello 2
Hello 3
Hello 4
```

Notice that counting starts at **0**, not 1. That's normal in programming.

## Shape 2: The classic counter loop

```go
for i := 1; i <= 5; i++ {
	fmt.Println(i)
}
```

It has 3 parts, separated by `;`:

| Part | Code | Meaning |
|---|---|---|
| start | `i := 1` | Begin with i = 1 |
| condition | `i <= 5` | Keep going while this is true |
| step | `i++` | After each round, add 1 to i |

Use this shape when you need to start at a different number or skip by 2, 5, and so on.

## Shape 3: "While" loop

Give only a condition. The loop runs while the condition is true:

```go
money := 100
for money > 0 {
	fmt.Println("Spending 30. Money left:", money)
	money -= 30
}
```

## Shape 4: Forever loop + break

```go
count := 0
for {
	count++
	if count == 3 {
		break    // stop the loop now
	}
}
```

`break` means **stop the loop now**.

## Skipping one round: continue

```go
for i := 1; i <= 10; i++ {
	if i%2 == 0 {
		continue // skip even numbers, go to the next round
	}
	fmt.Println(i) // prints 1 3 5 7 9
}
```

`continue` means **skip the rest of this round and start the next one**.

## Looping over text

```go
for index, letter := range "Go!" {
	fmt.Println(index, string(letter))
}
```

Output:

```
0 G
1 o
2 !
```

`range` gives you two things each round: the **position** and the **item**.
In Lesson 09 you'll use `range` on lists too.

## Practice

1. Print the numbers 1 to 10.
2. Print the 5 times table: `5 x 1 = 5` … `5 x 10 = 50`.
3. Add up all numbers from 1 to 100 and print the total (it should be 5050).
4. Print the numbers 1 to 20, but skip every number that divides by 3.

<details>
<summary>Answers</summary>

```go
for i := 1; i <= 10; i++ {
	fmt.Println(i)
}

for i := 1; i <= 10; i++ {
	fmt.Printf("5 x %d = %d\n", i, 5*i)
}

total := 0
for i := 1; i <= 100; i++ {
	total += i
}
fmt.Println(total)

for i := 1; i <= 20; i++ {
	if i%3 == 0 {
		continue
	}
	fmt.Println(i)
}
```
</details>

---

**Next:** [Lesson 07: switch](../07_switch/)
