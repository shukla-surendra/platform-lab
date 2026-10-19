# A repeatable framework for tackling DP problems

A step-by-step method to apply to any new recursion/DP problem, not just
the ones already solved in this repo. Grounded against
[`004_climbing_stairs.rs`](../dynamic_programming/src/bin/004_climbing_stairs.rs)
- see
[dynamic-programming-climbing-stairs-explained.md](dynamic-programming-climbing-stairs-explained.md)
for that problem walked through by hand with real numbers first, if the
steps below feel too abstract on their own.

## Step 1 - Represent the state as an index

Ask: "what's the *one changing thing* between recursive calls?" Usually
it collapses to one or more indices into an array-like state space.

- Climbing Stairs / Fibonacci: "which step am I standing on" -> `i`. The
  function becomes `f(i)`.
- Some problems need more than one index (e.g. "remaining capacity" in a
  knapsack problem) - but it's always some index/indices, never something
  vaguer.

## Step 2 - At that index, try every choice the problem statement allows

Don't think about efficiency yet - just enumerate the literal choices.
Climbing Stairs says "1 or 2 steps," so from `i` you can go to `i+1` or
`i+2`. These become the branches of the recursion - the same move used
for the include/exclude branches in
[`010_print_subsequences.rs`](../recursion/src/bin/010_print_subsequences.rs),
or the two `fib(n-1)`/`fib(n-2)` calls. "Try every choice" is the same
step every time, just with a different set of choices per problem.

## Step 3 - Combine the branches based on what the question asks

This is the step people skip and then get stuck. Read the question type:

| Question asks for...              | Combine with                          |
|------------------------------------|----------------------------------------|
| "how many ways"                    | **sum** the branches: `f(i) = f(i+1) + f(i+2)` |
| "min/max cost, length, profit"     | **min/max** the branches: `f(i) = min(f(i+1), f(i+2)) + cost` |
| "is it possible at all"            | **OR** the branches (any true wins)   |
| "print/list all of them"           | no combine - recurse and record at the leaf |

`004_climbing_stairs.rs` asks "how many ways" -> sum.
`005_min_cost_climbing_stairs.rs` asks "cheapest" -> min. Same `f(i)`,
same two branches, different row of this table - that's the entire
difference between the two files.

## Step 4 - Base case: what happens when the index runs off the end?

Standing exactly on the top -> 1 way (do nothing more). Standing past the
top -> 0 ways (invalid). Always "what's the answer when the index hits
the boundary" - usually the two obvious edge values (0 and 1, or empty
and single-element).

## Step 5 - Write the brute-force recursion first. Optimize only after it's correct

At this point you have the *recursive definition* comment block that
heads every file in `recursion/` and `dynamic_programming/` - write that
in comments before touching code, and verify it by hand on a small
example (as in the climbing-stairs doc linked above) before trusting it.
Then:

1. Does the same `f(i)` get called from multiple different paths? (Draw
   the tree for a small `n` - if `f(3)` appears twice, yes.) If so ->
   overlapping subproblems -> DP applies.
2. Add a cache -> **memoization** (see
   [`001_nth_fibonacci_memoization.rs`](../dynamic_programming/src/bin/001_nth_fibonacci_memoization.rs)).
3. Notice the valid call order is just `0, 1, 2, ..., n` -> flip to a
   loop filling a table -> **tabulation** (see
   [`002_nth_fibonacci_tabulation.rs`](../dynamic_programming/src/bin/002_nth_fibonacci_tabulation.rs),
   `004`, `005`).
4. Check how far back the recurrence actually looks (`f(i)` needs
   `f(i-1)` and `f(i-2)` -> window of 2) -> replace the table with that
   many rolling variables -> **space-optimized** (see
   [`003_nth_fibonacci_loop.rs`](../dynamic_programming/src/bin/003_nth_fibonacci_loop.rs)).

That last mile (memo -> tabulate -> space-optimize) is mechanical once
step 5's recursion is correct. Nearly all the actual thinking happens in
steps 1-4: deciding *what the index is* and *how to combine the choices*.
