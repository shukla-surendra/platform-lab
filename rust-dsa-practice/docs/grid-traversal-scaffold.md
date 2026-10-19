# Grid traversal scaffold — `grids` crate

Notes on the reusable grid toolkit in [`../grids/`](../grids/). The code is in
`grids/src/lib.rs` (19 tests) and a runnable tour is in
`grids/src/bin/001_grid_tour.rs`:

```
cd grids
cargo test
cargo run --bin 001_grid_tour
```

## The unifying idea

A grid problem is a **graph problem wearing a grid costume**. Cells are
vertices; the adjacency rule supplies the edges implicitly, so there is no
adjacency list to build — you compute neighbours on demand.

Once you see that, the whole family collapses. Number of Islands, Rotting
Oranges, Word Search, Shortest Path in Binary Matrix, Walls and Gates, Pacific
Atlantic, Surrounded Regions, Sudoku Solver, N-Queens differ in exactly three
places:

1. **which neighbours count** — 4-way, 8-way, knight, diagonals only;
2. **what "passable" means** — not a wall / same colour / next letter matches;
3. **what you accumulate** — a count, a distance, a path, a set of cells.

Everything else — bounds checking, the visited set, the frontier — is
boilerplate. The scaffold exists so practice time goes into the three things
that vary, not into retyping `in_bounds` for the fortieth time.

## Picking the traversal

This is the decision you're actually being graded on. Get it wrong and no
amount of clean code recovers.

| Question the problem asks | Use | Why |
|---|---|---|
| Are these cells connected? How many regions? | DFS / flood fill | Order is irrelevant, so use the cheaper one |
| Fewest **steps**, every step equal | **BFS** | First time BFS reaches a cell is optimal. O(V+E) |
| Fewest steps from the **nearest** of many starts | **Multi-source BFS** | Seed the queue with all sources at distance 0 |
| Cheapest path, **unequal** step costs | **Dijkstra** | BFS is simply wrong here |
| Costs are only 0 or 1 | 0-1 BFS (`VecDeque`, push_front/back) | Dijkstra's log factor is avoidable |
| Enumerate/validate **paths**, no cell reused | **Backtracking** (mark → recurse → **unmark**) | Reachability ≠ path search |
| Every cell independently, no traversal | Plain double loop | Don't over-engineer |

Two traps worth stating explicitly:

- **DFS does not find shortest paths.** It finds *a* path. People reach for the
  recursive one out of habit and quietly answer a different question.
- **Multi-source BFS is not a separate algorithm.** It's BFS with more than one
  cell enqueued at distance 0. Recognising that Rotting Oranges, Walls and
  Gates, and 01 Matrix are one technique — not three — is the generalization an
  interviewer is listening for.

## The interview-scale core

**Do not reproduce `lib.rs` on a whiteboard.** Under time pressure you write
this and nothing else:

```rust
let (rows, cols) = (grid.len(), grid[0].len());
let mut seen = vec![vec![false; cols]; rows];
let mut stack = vec![(r0, c0)];
seen[r0][c0] = true;

while let Some((r, c)) = stack.pop() {
    for (dr, dc) in [(-1i32, 0i32), (1, 0), (0, -1), (0, 1)] {
        let (nr, nc) = (r as i32 + dr, c as i32 + dc);
        if nr < 0 || nc < 0 || nr >= rows as i32 || nc >= cols as i32 { continue; }
        let (nr, nc) = (nr as usize, nc as usize);
        if !seen[nr][nc] && passable(grid[nr][nc]) {
            seen[nr][nc] = true;
            stack.push((nr, nc));
        }
    }
}
```

Swap `stack.pop()` → `queue.pop_front()` for BFS. That's the whole difference,
and being able to say *"DFS and BFS are the same code with a different
container"* is worth more than either implementation.

## Rust-specific traps

### 1. `usize` underflow — the one that actually bites

Coordinates are `usize`. Deltas are negative. `r - 1` when `r == 0` does **not**
give `-1`: it panics in debug and wraps to `usize::MAX` in release. A wrap is
worse than a panic — it silently reads the wrong cell.

Three fixes, in order of preference:

```rust
// (a) checked_add_signed — what the library uses. Underflow → None.
let nr = r.checked_add_signed(dr)?;
let nc = c.checked_add_signed(dc)?;
if nr < rows && nc < cols { /* in bounds */ }

// (b) cast to signed, check, cast back. Verbose but obvious; fine in an interview.
let (nr, nc) = (r as i32 + dr, c as i32 + dc);
if nr >= 0 && nc >= 0 && (nr as usize) < rows && (nc as usize) < cols { .. }

// (c) wrapping_add — clever, and I'd avoid it. Underflow wraps to a huge
//     number, which then fails `< rows` anyway. Correct, but a reader has to
//     stop and prove that to themselves.
let nr = r.wrapping_add_signed(dr);
if nr < rows { .. }
```

Note what (a) buys conceptually: **the two edges fail differently.** The top and
left edges are caught by underflow (`None`); the bottom and right edges are
caught by the explicit `< rows`/`< cols` test. There is no `>= 0` check anywhere
because `usize` can't be negative. Conflating those two mechanisms is the
classic grid bug.

### 2. Recursive DFS and the stack

The recursive version is prettier and overflows the stack on large inputs. A
1000×1000 grid shaped as one snaking corridor is a million-deep recursion;
Rust's 8 MB main-thread stack doesn't survive it. On LeetCode-sized inputs
recursion is fine — just know which one you're writing and be ready to say why.

### 3. Flat `Vec<T>` beats `Vec<Vec<T>>`

`Grid<T>` stores one flat `Vec` with `idx = row * cols + col`:

- one allocation instead of `rows + 1`;
- contiguous memory, so row-order scans are cache-friendly;
- every cell has a single `usize` identity that indexes a `Vec`-backed
  visited/dist/parent array directly — **no `HashSet<(usize, usize)>`, no
  hashing**.

That last point matters more than it looks. `vec![false; rows * cols]` is
strictly better than a `HashSet` of coordinates for a dense grid, and reaching
for the `HashSet` is a common reflex worth unlearning.

And `idx = row * cols + col` is the same row-major flattening as the Sudoku box
formula `(row / 3) * 3 + (col / 3)` — there the "grid" is the 3×3 grid of boxes
and the "width" is 3. One formula, two problems.

### 4. Mark visited at enqueue, not dequeue

```rust
if dist[ni].is_none() && passable(..) {
    dist[ni] = Some(d + 1);   // <- here, before push_back
    queue.push_back((nr, nc));
}
```

Marking on dequeue still terminates and still gives the right answer, but the
same cell can enter the queue once per incoming edge before it's first
processed, so the queue grows to O(V·degree) instead of O(V).

### 5. Backtracking must un-mark

```rust
used[i] = true;
let found = neighbours.any(|n| dfs(.., n, used));
used[i] = false;   // the line everyone forgets
```

A DFS exploring *reachability* marks a cell visited forever. A DFS exploring
*paths* must restore state on the way out, because a cell that blocks this path
may be essential on a different one. Forgetting the restore doesn't crash — it
returns `false` on inputs that should succeed, which is much harder to spot.

## Mapping real problems onto the scaffold

| Problem | Call |
|---|---|
| Number of Islands (200) | `connected_components(&g, &DIRS4, \|&c\| c == '1').len()` |
| Max Area of Island (695) | same, `.map(\|r\| r.len()).max()` |
| Flood Fill (733) | `flood_fill(..)`, then repaint the returned cells |
| Shortest Path in Binary Matrix (1091) | `shortest_path(.., &DIRS8, \|&c\| c == 0)` |
| Rotting Oranges (994) | `bfs(&g, all_rotten, &DIRS4, ..)`, answer = max dist |
| 01 Matrix (542) / Walls and Gates (286) | multi-source `bfs` from every 0 / every gate |
| Word Search (79) | `word_search(&g, word)` |
| Path With Minimum Effort (1631) | `dijkstra` with a max-edge-cost relaxation |
| Rotate Image (48) | `rotate_cw()` |
| Surrounded Regions (130) | flood fill inward **from the border** — invert the question |
| Pacific Atlantic (417) | two multi-source BFS from opposite borders, intersect |

The last two are the interesting ones. Both look like "search from the inside"
and are far easier searched **from the border inward** — that inversion, not the
traversal, is the insight being tested.

## Where this doesn't apply

`DIRS4`-style movement assumes a static board. It breaks down when:

- **state is more than position** — keys/doors (LC 864), fuel budgets,
  "at most k obstacles removed" (LC 1293). The fix is to widen the node from
  `(r, c)` to `(r, c, state)` and BFS over that larger space. The visited array
  becomes `[rows][cols][2^states]`. Same algorithm, bigger vertex.
- **the board changes as you move** — Sudoku Solver, N-Queens. Those are
  backtracking over placements, not traversal over cells; the grid is the
  *output*, not the graph.
