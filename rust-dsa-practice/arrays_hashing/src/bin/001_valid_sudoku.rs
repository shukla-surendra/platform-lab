// Problem: LeetCode 36 - Valid Sudoku.
//
// Given a 9x9 board where each cell is a digit '1'..'9' or '.' (empty),
// decide whether the FILLED cells break any Sudoku rule:
//   1. no digit repeats within a row,
//   2. no digit repeats within a column,
//   3. no digit repeats within a 3x3 sub-box.
// We are NOT asked whether the board is solvable - only whether what is
// already written down is self-consistent. That distinction matters: a
// board can be perfectly "valid" and still have no solution.
//
// ---------------------------------------------------------------------
// WHY THE OBVIOUS APPROACH IS AWKWARD
// ---------------------------------------------------------------------
// The instinct is to iterate over the GROUPS: "extract row 0, check for
// duplicates; extract row 1, check; ... then all 9 columns; then all 9
// boxes." That works, but it forces you to write three different
// extraction routines, and the box one is genuinely fiddly - you end up
// with a nested loop over (box_row, box_col, offset_r, offset_c) and it's
// easy to get the arithmetic wrong under interview pressure.
//
// The move that collapses all of it:
//
//     Don't iterate over the groups. Iterate over the CELLS, and let each
//     cell announce which three groups it belongs to.
//
// Every cell sits at the intersection of exactly one row, one column, and
// one box. So a cell has three coordinates in "constraint space":
// (row, col, box). One pass over 81 cells, three membership registries,
// done. No extraction functions at all.
//
// ---------------------------------------------------------------------
// DERIVING THE BOX INDEX (don't memorize this - rebuild it)
// ---------------------------------------------------------------------
// Integer division by 3 collapses 9 rows into 3 horizontal BANDS, and 9
// columns into 3 vertical STACKS:
//
//         col:   0 1 2 | 3 4 5 | 6 7 8
//                stack0  stack1  stack2
//     row 0..2   [  0  ][   1  ][   2  ]   band0   (row / 3 == 0)
//     row 3..5   [  3  ][   4  ][   5  ]   band1   (row / 3 == 1)
//     row 6..8   [  6  ][   7  ][   8  ]   band2   (row / 3 == 2)
//
// So a box is really a 2-D coordinate (band, stack) in a 3x3 grid of
// boxes. To store it in a flat array we flatten 2-D -> 1-D exactly the
// way we always do, row-major: index = row * width + col. Here width is
// 3, "row" is the band and "col" is the stack:
//
//     box_index = (row / 3) * 3 + (col / 3)
//
// It is the same flattening formula used for any 2-D-array-in-a-1-D-Vec.
// Recognizing it as that, rather than as a magic Sudoku formula, is what
// makes it transfer to other problems.
//
// ---------------------------------------------------------------------
// WHY ONE FORWARD PASS IS ENOUGH (the correctness argument)
// ---------------------------------------------------------------------
// "Is a duplicate" is a SYMMETRIC relation: if cells A and B collide,
// they collide in both directions. So we never need all-pairs comparison.
// Scan in a fixed order; if A comes before B, then by the time we reach B
// the value of A is already recorded, and B's membership check catches
// the collision. Checking each cell only against what came BEFORE it is
// therefore complete - it cannot miss a conflicting pair.
//
// This is the same argument that justifies "check the complement, then
// insert" in Two Sum. Worth having ready as a sentence, because
// interviewers do ask "are you sure one pass is sufficient?"
//
// Complexity: the board is fixed at 9x9, so strictly this is O(1). The
// more useful answer is to generalize to an n x n board (n = 9): O(n^2)
// time - each cell touched once, O(1) work per cell - and O(n^2) space
// for the registries. Give both; saying only "O(1), it's 81 cells" is
// technically true but reads as dodging the question.

use std::collections::HashSet;

// =====================================================================
// VERSION 1 - HashSet, the direct translation of the mental model
// =====================================================================
// Three vectors of 9 sets each: one per row, one per column, one per box.
// This is the version to write first in an interview. It is readable and
// obviously correct, and correctness-first is the right order.
//
// Rust notes:
//   - vec![HashSet::new(); 9] works because HashSet is Clone: the macro
//     builds one value and clones it 8 times. (An empty set clones
//     cheaply, so this is fine here.)
//   - We take &[[char; 9]; 9] rather than LeetCode's Vec<Vec<char>>.
//     The board size is a compile-time constant, so encoding it in the
//     type removes a whole class of bounds questions. See the LeetCode
//     signature adapter at the bottom of this file.
pub fn is_valid_sudoku_hashset(board: &[[char; 9]; 9]) -> bool {
    let mut rows: Vec<HashSet<char>> = vec![HashSet::new(); 9];
    let mut cols: Vec<HashSet<char>> = vec![HashSet::new(); 9];
    let mut boxes: Vec<HashSet<char>> = vec![HashSet::new(); 9];

    for row in 0..9 {
        for col in 0..9 {
            let value = board[row][col];

            // Empty cells constrain nothing - the problem only asks us to
            // validate what is already filled in.
            if value == '.' {
                continue;
            }

            let box_index = (row / 3) * 3 + (col / 3);

            // HashSet::insert RETURNS bool: true if the value was newly
            // added, false if it was already present. So the membership
            // check and the recording step are the same operation - one
            // hash lookup instead of the two you'd pay for
            // `if set.contains(&v) { ... } set.insert(v);`.
            //
            // It also removes a real bug class: with separate
            // contains-then-insert calls, it is possible to check one set
            // and forget to insert into it. Here that cannot drift apart.
            //
            // SUBTLETY worth saying out loud: `||` short-circuits, so if
            // the row check fails we never insert into cols/boxes. That
            // looks like a bug and isn't - we are returning false on the
            // very next line, so the half-updated state is discarded. If
            // this function ever needed to keep going after a conflict
            // (it doesn't), this would have to be rewritten.
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

// =====================================================================
// VERSION 2 - bitmask, the optimization worth knowing
// =====================================================================
// A HashSet is the general-purpose tool for "have I seen this?", but it
// is heavier than this problem needs. Here the key domain is tiny and
// known in advance: exactly 9 possible values, '1'..'9'. When the domain
// is small, fixed, and dense, a bitmask is a PERFECT HASH - no hashing,
// no allocation, no collisions, no pointer chasing.
//
// Map '1' -> bit 0, '2' -> bit 1, ... '9' -> bit 8. Nine bits fit in a
// u16 with room to spare. Three arrays of nine u16s is 54 bytes total,
// entirely on the stack, versus 27 heap-allocated hash tables in v1.
//
// Same O(1)-per-cell asymptotics; dramatically smaller constant factor.
// This is the answer to "can you do it without extra allocation?"
pub fn is_valid_sudoku_bitmask(board: &[[char; 9]; 9]) -> bool {
    let mut rows = [0u16; 9];
    let mut cols = [0u16; 9];
    let mut boxes = [0u16; 9];

    for (row, line) in board.iter().enumerate() {
        for (col, &value) in line.iter().enumerate() {
            if value == '.' {
                continue;
            }

            // b'1' is a u8 byte literal. Digits are contiguous in ASCII,
            // so `value as u8 - b'1'` gives 0..=8 for '1'..='9'.
            // Shifting 1 left by that amount produces the value's bit.
            let bit = 1u16 << (value as u8 - b'1');
            let box_index = (row / 3) * 3 + (col / 3);

            // `mask & bit != 0` asks "is this bit already set?" - the
            // bitwise equivalent of set.contains(). `mask |= bit` is the
            // equivalent of set.insert().
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

// =====================================================================
// VERSION 3 - one HashSet, three encoded keys
// =====================================================================
// Included because it makes the connection to the wider hashing pattern
// explicit rather than incidental. Instead of three registries, use ONE
// set and give each constraint its own key encoding:
//
//     ('r', row, value)  ('c', col, value)  ('b', box, value)
//
// The tag character is what keeps the three key families from colliding
// with each other. This is exactly the "canonical key" idea from
// dsa_prep/arrays_hashing/PATTERN.md: pick a derived key such that
// everything that must not coexist maps to the same key, and nothing
// else does.
//
// It is slower and less readable than v1 - do not lead with it in an
// interview. Its value is that recognizing the encoding trick is what
// lets you handle "now add a fourth constraint (both diagonals)" without
// restructuring anything.
pub fn is_valid_sudoku_single_set(board: &[[char; 9]; 9]) -> bool {
    let mut seen: HashSet<(char, usize, char)> = HashSet::new();

    for row in 0..9 {
        for col in 0..9 {
            let value = board[row][col];
            if value == '.' {
                continue;
            }

            let box_index = (row / 3) * 3 + (col / 3);

            if !seen.insert(('r', row, value))
                || !seen.insert(('c', col, value))
                || !seen.insert(('b', box_index, value))
            {
                return false;
            }
        }
    }

    true
}

// =====================================================================
// LeetCode signature adapter
// =====================================================================
// LeetCode hands you Vec<Vec<char>> and wraps everything in
// `impl Solution`, which does not exist outside their harness. This is
// what you would actually paste there, delegating to the real logic.
// Keeping the adapter separate is the habit worth building: the
// algorithm should not be shaped by one judge's calling convention.
pub fn is_valid_sudoku(board: Vec<Vec<char>>) -> bool {
    let mut fixed = [['.'; 9]; 9];
    for (r, row) in board.iter().enumerate().take(9) {
        for (c, &ch) in row.iter().enumerate().take(9) {
            fixed[r][c] = ch;
        }
    }
    is_valid_sudoku_bitmask(&fixed)
}

// =====================================================================
// Test data
// =====================================================================

fn parse(rows: [&str; 9]) -> [[char; 9]; 9] {
    let mut board = [['.'; 9]; 9];
    for (r, line) in rows.iter().enumerate() {
        for (c, ch) in line.chars().enumerate() {
            board[r][c] = ch;
        }
    }
    board
}

fn example_valid() -> [[char; 9]; 9] {
    parse([
        "53..7....",
        "6..195...",
        ".98....6.",
        "8...6...3",
        "4..8.3..1",
        "7...2...6",
        ".6....28.",
        "...419..5",
        "....8..79",
    ])
}

// Same board with the top-left 5 changed to 8 -> two 8s in the top-left
// 3x3 box. Note that this board has NO row conflict and NO column
// conflict; only the box rule catches it. A test suite without a case
// like this will happily pass a solution whose box arithmetic is wrong.
fn example_box_conflict() -> [[char; 9]; 9] {
    parse([
        "83..7....",
        "6..195...",
        ".98....6.",
        "8...6...3",
        "4..8.3..1",
        "7...2...6",
        ".6....28.",
        "...419..5",
        "....8..79",
    ])
}

fn main() {
    let valid = example_valid();
    let invalid = example_box_conflict();

    // All three implementations must agree on every board - that
    // agreement is the cheapest correctness check available here.
    for (name, f) in [
        (
            "hashset   ",
            is_valid_sudoku_hashset as fn(&[[char; 9]; 9]) -> bool,
        ),
        ("bitmask   ", is_valid_sudoku_bitmask),
        ("single_set", is_valid_sudoku_single_set),
    ] {
        println!(
            "{name}  example 1 (valid) -> {:<5}   example 2 (box conflict) -> {}",
            f(&valid),
            f(&invalid)
        );
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    const IMPLS: [(&str, fn(&[[char; 9]; 9]) -> bool); 3] = [
        ("hashset", is_valid_sudoku_hashset),
        ("bitmask", is_valid_sudoku_bitmask),
        ("single_set", is_valid_sudoku_single_set),
    ];

    fn check(board: &[[char; 9]; 9], expected: bool, case: &str) {
        for (name, f) in IMPLS {
            assert_eq!(f(board), expected, "{name} disagreed on case: {case}");
        }
    }

    #[test]
    fn example_1_is_valid() {
        check(&example_valid(), true, "leetcode example 1");
    }

    #[test]
    fn example_2_box_conflict_is_invalid() {
        check(&example_box_conflict(), false, "leetcode example 2");
    }

    #[test]
    fn empty_board_is_valid() {
        check(&[['.'; 9]; 9], true, "all cells empty");
    }

    #[test]
    fn row_conflict_only() {
        let mut b = [['.'; 9]; 9];
        b[0][0] = '5';
        b[0][8] = '5'; // same row, different column, different box
        check(&b, false, "row conflict in isolation");
    }

    #[test]
    fn column_conflict_only() {
        let mut b = [['.'; 9]; 9];
        b[0][0] = '5';
        b[8][0] = '5'; // same column, different row, different box
        check(&b, false, "column conflict in isolation");
    }

    #[test]
    fn box_conflict_only() {
        let mut b = [['.'; 9]; 9];
        b[0][0] = '5';
        b[1][1] = '5'; // same box, different row AND different column
        check(&b, false, "box conflict in isolation");
    }

    // Guards against an off-by-one in the box formula: these two cells
    // are diagonally adjacent but sit in DIFFERENT boxes. A buggy index
    // (e.g. row/3 + col/3, which maps (0,3) and (3,0) to the same box)
    // would wrongly reject this.
    #[test]
    fn adjacent_cells_across_a_box_boundary_are_fine() {
        let mut b = [['.'; 9]; 9];
        b[2][2] = '5'; // bottom-right of box 0
        b[3][3] = '5'; // top-left of box 4
        check(&b, true, "same value, adjacent, different boxes");
    }

    // The specific formula (row/3)*3 + (col/3) must be a BIJECTION from
    // the 9 (band, stack) pairs onto 0..=8. If it collapses two boxes
    // into one index, valid boards get rejected; if it skips an index,
    // one box goes unchecked entirely.
    #[test]
    fn box_index_covers_each_box_exactly_once() {
        let mut hits = [0u32; 9];
        for row in 0..9 {
            for col in 0..9 {
                hits[(row / 3) * 3 + (col / 3)] += 1;
            }
        }
        assert_eq!(hits, [9; 9], "each box must receive exactly 9 cells");
    }

    #[test]
    fn leetcode_adapter_matches() {
        let nested: Vec<Vec<char>> = example_valid().iter().map(|r| r.to_vec()).collect();
        assert!(is_valid_sudoku(nested));
    }
}
