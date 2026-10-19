# Climbing Stairs, explained by hand: `004` vs `005`

Both problems live in `dynamic_programming/src/bin/`:
[`004_climbing_stairs.rs`](../dynamic_programming/src/bin/004_climbing_stairs.rs)
and
[`005_min_cost_climbing_stairs.rs`](../dynamic_programming/src/bin/005_min_cost_climbing_stairs.rs).
This doc traces both with real numbers, no shortcuts, before looking at
the recurrence or the code.

## 004 - Climbing Stairs (count the ways)

**The setup:** you're at the bottom of a staircase with `n` steps. Each
move, you go up 1 or 2 steps. Question: how many *different sequences of
moves* get you exactly to the top?

**Try n = 4 by hand, just listing every path:**

```
1+1+1+1
1+1+2
1+2+1
2+1+1
2+2
```

5 paths. That's what `ways(4) = 5` means - not "5 steps," but "5
different ways to arrange your 1s and 2s to sum to 4."

**Now, why is `ways(4) = ways(3) + ways(2)`?**

Look at those 5 paths again, but ask: *what was the very last move in
each one?*

```
1+1+1 | +1     <- last move was +1, everything before it sums to 3
1+1+2          <- last move was +2, everything before it sums to 2
1+2+1 | +1     <- last move was +1, everything before it sums to 3
2+1+1 | +1     <- last move was +1, everything before it sums to 3
2+2            <- last move was +2, everything before it sums to 2
```

Every path's last move is either `+1` (and everything before it is a
valid way to make 3) or `+2` (and everything before it is a valid way to
make 2). There's no third option - those are the only moves allowed. So:

> **total ways to make 4** = **(ways to make 3, then one more +1 step)**
> + **(ways to make 2, then one more +2 step)**

That's literally `ways(4) = ways(3) + ways(2)`. It's not a formula pulled
out of nowhere - it's "group all the paths by their last move, and count
each group."

**Base cases**, same logic at the edge: `ways(0) = 1` means "you're
already standing at the target with zero moves - that's 1 valid (empty)
way." `ways(1) = 1` means "only one path makes 1: a single `+1`."

**The code just is that sentence:**

```rust
fn ways(n: u64) -> u64 {
    if n == 0 || n == 1 { return 1; }
    ways(n - 1) + ways(n - 2)
}
```

## 005 - Min Cost Climbing Stairs (cheapest way, not count)

**The setup changes:** now every stair `i` has a price tag, `cost[i]`.
You still move 1 or 2 steps at a time, starting free at step 0 or step 1.
Every time you step on a stair, you pay its price. Question: what's the
*cheapest total* to get past the top?

**Walk `cost = [10, 15, 20]` by hand - list every path and its total
price:**

```
start 0 (free) -> pay 10 -> +1 -> 1 -> pay 15 -> +2 -> top                        = 25
start 0 (free) -> pay 10 -> +2 -> 2 -> pay 20 -> +1 -> top                        = 30
start 0 (free) -> pay 10 -> +1 -> 1 -> pay 15 -> +1 -> 2 -> pay 20 -> +1 -> top   = 45
start 1 (free) -> pay 15 -> +2 -> top                                            = 15   <- cheapest
start 1 (free) -> pay 15 -> +1 -> 2 -> pay 20 -> +1 -> top                       = 35
```

Cheapest is **15**: start at step 1 for free, pay 15 to step onto it,
then jump straight over the top with a `+2`.

**Why `minCost(i) = min(minCost(i-1) + cost[i-1], minCost(i-2) +
cost[i-2])`?**

Same "look at the last move" trick as before, but now instead of
*counting* the two options, you *pick the cheaper one* - because the
question asks for cheapest, not "how many."

To land on step `i`, your last move was either:

- a `+1` from step `i-1` - you had to already be standing on `i-1` (cost
  `minCost(i-1)`), *then pay `cost[i-1]` to leave it and move to `i`*
- a `+2` from step `i-2` - already on `i-2` (cost `minCost(i-2)`), *then
  pay `cost[i-2]` to leave it and move to `i`*

You get to choose whichever route was cheaper - that's the `min(...)`.
This is the exact same "which was my last move" question as `004`, just
swapping "add up both options" for "take the cheaper option," because the
question changed from *count all ways* to *find the best way*.

**The subtle bit that's easy to miss:** `minCost(i)` means "cheapest cost
*to arrive at* step `i`, not counting the price of leaving `i` yet."
That's why `table[0] = 0` and `table[1] = 0` - standing on step 0 or 1
costs nothing *by itself*; you only pay when you actually use that step
as a launchpad to jump further. Trace it:

```
table[0] = 0                                          (free to stand here)
table[1] = 0                                          (free to stand here)
table[2] = min(table[1] + cost[1], table[0] + cost[0])
         = min(0 + 15,            0 + 10)   = 10
table[3] = min(table[2] + cost[2], table[1] + cost[1])
         = min(10 + 20,            0 + 15)  = 15
```

`table[3]` is the "top" (one past the last real stair, index 3 for a
3-element array) - and 15 matches the hand-walked answer above. The
winning path is captured in `min(10+20, 0+15)` picking the second option:
reach step 1 for free (`table[1] = 0`), pay `cost[1] = 15` to leave it -
that's the "start at 1, pay 15, jump to top" path from the hand-walk.

## The one-sentence difference

Same question shape ("what's my last move, +1 or +2"), but `004` *adds
up* both possibilities (because it's counting), and `005` *takes the
minimum* of both possibilities (because it's optimizing cost). Same
skeleton, different combining operation - see
[dp-problem-solving-framework.md](dp-problem-solving-framework.md) (step
3) for why that's the general pattern across all DP optimization
problems, not just this one.
