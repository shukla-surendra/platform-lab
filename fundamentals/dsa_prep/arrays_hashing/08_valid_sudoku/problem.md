# 8. Valid Sudoku

**Difficulty:** Medium
**Topic:** Arrays & Hashing
**Pattern:** Seen-before check with multiple derived keys (row / column / box)
**LeetCode:** 36

## Problem
Given a 9×9 Sudoku board where each cell holds a digit `'1'`–`'9'` or `'.'` (empty),
decide whether the **filled** cells break any rule:

1. no digit repeats within a row,
2. no digit repeats within a column,
3. no digit repeats within a 3×3 sub-box.

We are not asked whether the board is *solvable* — only whether what is already written
down is self-consistent. A board can be perfectly valid and still have no solution.

## Examples
```
Input:  [["5","3",".",".","7",".",".",".","."],
         ["6",".",".","1","9","5",".",".","."],
         [".","9","8",".",".",".",".","6","."],
         ["8",".",".",".","6",".",".",".","3"],
         ["4",".",".","8",".","3",".",".","1"],
         ["7",".",".",".","2",".",".",".","6"],
         [".","6",".",".",".",".","2","8","."],
         [".",".",".","4","1","9",".",".","5"],
         [".",".",".",".","8",".",".","7","9"]]
Output: true

Input:  same board, but board[0][0] changed from "5" to "8"
Output: false   (two 8s in the top-left 3x3 box)
```

Note what example 2 does *not* contain: no row conflict and no column conflict. Only the
box rule catches it. That is the test case that separates a correct box index from a
plausible-looking wrong one.

## Why the Obvious Approach Is Awkward
The instinct is to iterate over the **groups**: extract row 0 and check for duplicates,
extract row 1 and check, … then all nine columns, then all nine boxes. It is O(n²) and
correct, so it isn't *wrong* — but it costs you three separate extraction routines, and
the box one is genuinely fiddly. You end up with a four-deep nested loop over
`(box_row, box_col, offset_r, offset_c)`, which is exactly the kind of index arithmetic
people get wrong on a whiteboard.

(The truly naive version — for every filled cell, scan its row, column, and box for a
match — is 81 × 24 comparisons and still only O(n²) here, because the board is fixed. It
isn't the complexity that's the problem; it's the structure.)

## Mental Model
Flip the iteration:

> **Don't iterate over the groups. Iterate over the cells, and let each cell announce
> which three groups it belongs to.**

Every cell sits at the intersection of exactly one row, one column, and one box. So a
cell has three coordinates in *constraint space*: `(row, col, box)`. One pass over 81
cells, three membership registries, done — no extraction functions at all.

This is the same "have I seen this before?" skeleton as Contains Duplicate, with one
twist: each element is checked against **three** registries under three different derived
keys, instead of one.

## Visual: Deriving the Box Index
Integer division by 3 collapses 9 rows into 3 horizontal **bands** and 9 columns into 3
vertical **stacks**:

```
             col:  0 1 2  |  3 4 5  |  6 7 8
                   stack0    stack1    stack2
                 +--------+---------+--------+
  rows 0-2       |   box  |   box   |  box   |   band 0   (row / 3 == 0)
  (row/3 == 0)   |    0   |    1    |   2    |
                 +--------+---------+--------+
  rows 3-5       |   box  |   box   |  box   |   band 1   (row / 3 == 1)
  (row/3 == 1)   |    3   |    4    |   5    |
                 +--------+---------+--------+
  rows 6-8       |   box  |   box   |  box   |   band 2   (row / 3 == 2)
  (row/3 == 2)   |    6   |    7    |   8    |
                 +--------+---------+--------+
                  col/3=0   col/3=1   col/3=2
```

A box is really a 2-D coordinate `(band, stack)` in a 3×3 grid of boxes. To store it in a
flat array, flatten 2-D → 1-D the way we always do — row-major, `index = row * width + col`
— where `width` is 3, "row" is the band, and "col" is the stack:

```
box_index = (row / 3) * 3 + (col / 3)
```

**Don't memorize it; rebuild it.** Recognizing this as the generic 2-D-array-in-a-1-D-Vec
flattening formula, rather than a magic Sudoku constant, is what makes it transfer. Sanity
check the two extremes: `(0,0) → 0`, `(8,8) → 2*3 + 2 = 8`. And note why
`(row/3) + (col/3)` fails — it maps `(0,3)` and `(3,0)` to the same index, merging two
distinct boxes.

## Why One Forward Pass Is Enough (Correctness)
"Is a duplicate of" is a **symmetric relation**: if cells A and B collide, they collide in
both directions. So all-pairs comparison is unnecessary. Scan in any fixed order; if A
precedes B, then by the time we reach B, A's value is already recorded, and B's membership
check catches the collision. Checking each cell only against what came **before** it is
therefore complete — it cannot miss a conflicting pair.

Two more pieces to state if pushed:

- **Completeness:** every filled cell is visited exactly once, and at that visit it is
  checked against all three of its groups. No cell and no constraint is skipped.
- **Early return is safe:** we only need a boolean, so the first conflict is a final
  answer — no need to keep scanning for more.

This is the identical argument that justifies check-then-insert in Two Sum, and it is worth
having as a rehearsed sentence: interviewers do ask *"are you sure one pass is sufficient?"*

## Algorithm
```
rows, cols, boxes  <- 9 empty registries each
for row in 0..9, for col in 0..9:
    value <- board[row][col]
    if value is '.':  continue          # empty cells constrain nothing
    b <- (row / 3) * 3 + (col / 3)
    if value already in rows[row] or cols[col] or boxes[b]:  return false
    record value in rows[row], cols[col], boxes[b]
return true
```

## Why This Approach (Generalizing the Pattern)
This is a concrete instance of the **seen-before check** template with a **derived key** —
both covered in [`../PATTERN.md`](../PATTERN.md). What makes it worth studying is that it
combines them: one element, three simultaneous key functions. If the box-index trick felt
like it came out of nowhere, read the pattern doc, then come back — the choices here should
read as inevitable rather than clever.

## Complexity
The board is fixed at 9×9, so strictly this is **O(1) time and O(1) space**. That answer is
technically correct and reads as dodging. Give both, generalizing to an n×n board:

- **Time:** O(n²) — each cell touched once, O(1) work per cell.
- **Space:** O(n²) for the registries (3n sets holding at most n entries each). The bitmask
  variant below drops this to 3n machine words for any n ≤ 64.

## Solution — Rust

### Version 1: HashSet (write this first)
```rust
use std::collections::HashSet;

pub fn is_valid_sudoku(board: &[[char; 9]; 9]) -> bool {
    let mut rows: Vec<HashSet<char>> = vec![HashSet::new(); 9];
    let mut cols: Vec<HashSet<char>> = vec![HashSet::new(); 9];
    let mut boxes: Vec<HashSet<char>> = vec![HashSet::new(); 9];

    for row in 0..9 {
        for col in 0..9 {
            let value = board[row][col];
            if value == '.' {
                continue;
            }

            let box_index = (row / 3) * 3 + (col / 3);

            if !rows[row].insert(value)
                || !cols[col].insert(value)
                || !boxes[box_index].insert(value)
            {
                return false;
            }
        }
    }

    true
}
```

Three Rust points worth saying out loud:

- **`HashSet::insert` returns `bool`** — `true` if the value was newly added. So the
  membership check *is* the recording step: one hash lookup instead of the two that
  `if set.contains(&v) { … } set.insert(v);` pays for. It also kills a real bug class —
  with separate calls it's possible to check one registry and forget to insert into it,
  and here the two can't drift apart.
- **`||` short-circuits, and that looks like a bug but isn't.** If the row check fails,
  `cols` and `boxes` never get inserted into. That's fine because we return `false` on the
  next line and discard the half-updated state. If this function ever had to keep going
  after a conflict, it would need rewriting — flag that you noticed it.
- **`vec![HashSet::new(); 9]`** works because `HashSet` is `Clone`; the macro builds one
  value and clones it eight times.

### Version 2: Bitmask (the optimization to reach for)
A `HashSet` is the general-purpose tool for "have I seen this?", but this problem's key
domain is tiny and known in advance: exactly nine values. When the domain is small, fixed,
and dense, a bitmask is a **perfect hash** — no hashing, no allocation, no collisions.

```rust
pub fn is_valid_sudoku(board: &[[char; 9]; 9]) -> bool {
    let mut rows = [0u16; 9];
    let mut cols = [0u16; 9];
    let mut boxes = [0u16; 9];

    for (row, line) in board.iter().enumerate() {
        for (col, &value) in line.iter().enumerate() {
            if value == '.' {
                continue;
            }

            // digits are contiguous in ASCII: '1'..='9' -> bits 0..=8
            let bit = 1u16 << (value as u8 - b'1');
            let box_index = (row / 3) * 3 + (col / 3);

            if rows[row] & bit != 0 || cols[col] & bit != 0 || boxes[box_index] & bit != 0 {
                return false;
            }

            rows[row] |= bit;
            cols[col] |= bit;
            boxes[box_index] |= bit;
        }
    }

    true
}
```

`mask & bit != 0` is `contains`; `mask |= bit` is `insert`. Three arrays of nine `u16`s is
**54 bytes, entirely on the stack**, versus 27 heap-allocated hash tables in version 1.
Identical asymptotics, dramatically smaller constant. This is the answer to *"can you do it
without extra allocation?"*

### Version 3: One HashSet, three encoded keys
```rust
let mut seen: HashSet<(char, usize, char)> = HashSet::new();
// ...
if !seen.insert(('r', row, value))
    || !seen.insert(('c', col, value))
    || !seen.insert(('b', box_index, value))
{
    return false;
}
```

The tag character keeps the three key families from colliding. This is precisely the
**canonical key** idea from `PATTERN.md`. Slower and less readable — don't lead with it —
but recognizing the encoding is what lets you add a fourth constraint (say, both diagonals,
for X-Sudoku) without restructuring anything.

### A note on the LeetCode signature
LeetCode gives you `Vec<Vec<char>>` wrapped in `impl Solution`, which doesn't exist outside
their harness and won't compile standalone. The board size is a compile-time constant, so
`&[[char; 9]; 9]` is the honest Rust type — keep an adapter at the boundary rather than
letting one judge's calling convention shape the algorithm.

**Runnable version**, all three implementations plus nine tests, in the sibling Rust crate:

```
cd rust_dsa_practice/arrays_hashing
cargo test --bin 001_valid_sudoku
cargo run  --bin 001_valid_sudoku
```

## Solution — Python
Runnable, with sample test cases at the bottom (`python3 arrays_hashing/08_valid_sudoku/solution.py`):

```python
--8<-- "arrays_hashing/08_valid_sudoku/solution.py"
```

## Test Cases Worth Writing
The board-level examples are weak tests — they conflate all three rules. Isolate them:

| Case | Expectation | What it catches |
|---|---|---|
| Empty board | `true` | Treating `'.'` as a value |
| `(0,0)` and `(0,8)` both `'5'` | `false` | Row check |
| `(0,0)` and `(8,0)` both `'5'` | `false` | Column check |
| `(0,0)` and `(1,1)` both `'5'` | `false` | Box check *in isolation* — no row or column conflict |
| `(2,2)` and `(3,3)` both `'5'` | `true` | Off-by-one in the box formula (`row/3 + col/3` fails here) |
| `(row/3)*3 + (col/3)` over all 81 cells | each index hit exactly 9× | The formula is a bijection onto `0..=8` |

That last one is a property test, not an example test — it verifies the box index never
collapses two boxes into one (valid boards wrongly rejected) or skips one (a box never
checked at all).

## Variations
- **Sudoku Solver (LC 37)** — the natural follow-up. These same three registries become the
  incremental validity check inside a backtracking search, and now you must *undo* on
  backtrack. With bitmasks that's a one-liner: `mask ^= bit`. This is why version 2 matters
  beyond micro-optimization.
- **N-Queens (LC 51)** — structurally the *same problem*: one pass placing items, three
  constraint registries, except the keys are column, diagonal (`r + c`), and anti-diagonal
  (`r - c + n`). Naming that equivalence out loud is strong generalization signal.
- **X-Sudoku / hyper-Sudoku** — add a fourth and fifth registry. Version 3's key encoding
  absorbs this with no structural change.
- **General n²×n² board** — replace the literal `3` with `n` and `9` with `n*n`; the box
  formula becomes `(row / n) * n + (col / n)`, which is the row-major flattening again.
- **"Which cells conflict?"** rather than a boolean — drop the early return, record the
  offending coordinates. This is where the `||` short-circuit above would become a genuine
  bug.

## Articulate It: Interview Framing & Vocabulary

### Three Ways to Explain This

- **Brute-force-first framing (the default — name the naive approach before optimizing):**
  "The straightforward version iterates over the groups: check all nine rows, then all nine
  columns, then all nine boxes. That's still O(n²), so the complexity isn't the problem —
  the problem is that it needs three separate extraction routines and the box one is fiddly
  index arithmetic. So instead I'll iterate over cells and let each cell tell me which three
  groups it belongs to. Same complexity, one loop, no extraction."
- **Invariant framing (good for defending correctness under pushback):** "The invariant is
  that after processing cell k, the three registries contain exactly the values seen in the
  first k cells, grouped by row, column, and box. Since 'is a duplicate of' is a symmetric
  relation, checking each cell only against what came before it is complete — if two cells
  conflict, the later one catches it. That's why one forward pass is sufficient and I don't
  need all-pairs comparison."
- **Pattern-recognition framing (good for showing you're generalizing, not recalling):**
  "This is the seen-before check from the hashing family, with one twist — each element is
  checked against three registries under three derived keys instead of one. Once I frame it
  that way, N-Queens is visibly the same problem with column, diagonal, and anti-diagonal as
  the keys, and Sudoku Solver is this plus backtracking, where the registries need an undo
  operation."

### Vocabulary Builder

- **perfect hash** (n. phrase) — a key-to-slot mapping with no collisions, possible when the
  key domain is small, fixed, and known in advance; the justification for replacing a
  `HashSet` with a bitmask here. *"Nine possible digits means I can use a bitmask as a
  perfect hash instead of paying for a general-purpose hash table."*
- **row-major flattening** (n. phrase) — collapsing a 2-D index into 1-D via
  `row * width + col`; naming the box formula as an instance of this is what turns it from a
  memorized constant into something you can rederive.
- **symmetric relation** (n. phrase) — one where `aRb` implies `bRa`; the property that makes
  a single forward pass complete rather than requiring all-pairs comparison. *"Because
  duplication is symmetric, I only ever need to look backwards."*
- **short-circuit evaluation** (n. phrase) — `||` skipping later operands once one is true;
  worth naming explicitly here because it means a failed row check leaves the column and box
  registries un-updated. *"That's short-circuiting, and it's safe only because I return
  immediately — if I needed to collect every conflict it would be a bug."*
- **"the complexity isn't the problem, the structure is"** — a reusable line for justifying a
  rewrite that doesn't improve the big-O. Interviewers respect knowing *why* you're
  refactoring when the asymptotics don't move.
