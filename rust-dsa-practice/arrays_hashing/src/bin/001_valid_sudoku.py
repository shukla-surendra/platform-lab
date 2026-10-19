#!/usr/bin/env python3
"""LeetCode 36 - Valid Sudoku. PRACTICE SCAFFOLD - the logic is yours to write.

    python3 001_valid_sudoku.py

Fill in the stubs in the YOUR CODE section. Everything below the divider is the
test data and runner - you shouldn't need to touch it.

Unimplemented functions are SKIPPED, not failed, so you can work one at a time.
Suggested order:

    1. box_index()               <- do this first; it has its own tests
    2. is_valid_sudoku_sets()    <- the version you'd write in an interview
    3. is_valid_sudoku_bitmask() <- the "no extra allocation" follow-up
    4. is_valid_sudoku_one_set() <- the key-encoding variation

Stuck? The worked explanation is in
fundamentals/dsa_prep/arrays_hashing/08_valid_sudoku/problem.md, and the Rust
version of all three is the .rs file sitting next to this one. Try to get
box_index and the first implementation out without either.
"""

import sys
import traceback

# ===========================================================================
# YOUR CODE - everything above the divider
# ===========================================================================

# A board is a 9x9 list of lists of single-character strings.
# Each cell is '1'-'9' (filled) or '.' (empty).
Board = list[list[str]]


def box_index(row: int, col: int) -> int:
    """Which 3x3 sub-box does cell (row, col) belong to?

    Boxes are numbered 0-8 in reading order: box 0 is the top-left, box 2 is
    the top-right, box 8 is the bottom-right.

    Contract this must satisfy (the tests check both):
      - returns a value in 0..=8 for every (row, col) in 0..=8
      - over all 81 cells, each of the 9 box numbers comes up exactly 9 times
    """
    raise NotImplementedError


def is_valid_sudoku_sets(board: Board) -> bool:
    """Return True if no digit repeats within any row, column, or 3x3 box.

    Only filled cells are validated - '.' constrains nothing. You are NOT being
    asked whether the board is solvable.

    Use three collections of sets: one per row, one per column, one per box.
    """
    raise NotImplementedError


def is_valid_sudoku_bitmask(board: Board) -> bool:
    """Same result, no sets - one integer per row / column / box.

    There are only 9 possible values, so a 9-bit integer can record which
    digits a group has already seen. `mask & bit` tests membership,
    `mask |= bit` records it.
    """
    raise NotImplementedError


def is_valid_sudoku_one_set(board: Board) -> bool:
    """Same result, using a SINGLE set for all three constraints.

    Encode each observation as a distinct key so the three constraint families
    can't collide with each other. Think about what goes wrong if you store
    just (0, '5') for both "row 0 has a 5" and "column 0 has a 5".
    """
    raise NotImplementedError


# ===========================================================================
# TEST DATA AND RUNNER - you shouldn't need to edit below here
# ===========================================================================

IMPLEMENTATIONS = [
    ("is_valid_sudoku_sets", is_valid_sudoku_sets),
    ("is_valid_sudoku_bitmask", is_valid_sudoku_bitmask),
    ("is_valid_sudoku_one_set", is_valid_sudoku_one_set),
]


def parse(rows: list[str]) -> Board:
    """Build a board from 9 strings of 9 characters each."""
    assert len(rows) == 9, f"expected 9 rows, got {len(rows)}"
    assert all(len(r) == 9 for r in rows), "every row must be 9 characters"
    return [list(r) for r in rows]


def blank() -> Board:
    return [["."] * 9 for _ in range(9)]


def place(*cells: tuple[int, int, str]) -> Board:
    """An otherwise-empty board with specific cells filled: place((0, 0, '5'))."""
    board = blank()
    for row, col, value in cells:
        board[row][col] = value
    return board


def render(board: Board) -> str:
    """Pretty-print with box separators - for eyeballing a failure."""
    lines = []
    for r in range(9):
        if r % 3 == 0:
            lines.append("      +------+------+------+")
        cells = " ".join(
            ("|" if c % 3 == 0 else "") + board[r][c] for c in range(9)
        )
        lines.append(f"      | {cells} |".replace("| |", "|"))
    lines.append("      +------+------+------+")
    return "\n".join(lines)


EXAMPLE_1 = parse([
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

# Example 1 with the top-left 5 changed to an 8 -> two 8s in the top-left box.
# Note there is NO row conflict and NO column conflict here; only the box rule
# catches it. A solution with a broken box index still passes example 1.
EXAMPLE_2 = parse([
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

# (name, board, expected, what it catches)
CASES: list[tuple[str, Board, bool, str]] = [
    ("leetcode example 1", EXAMPLE_1, True, "a genuinely valid board"),
    ("leetcode example 2", EXAMPLE_2, False, "box conflict, no row/col conflict"),
    ("empty board", blank(), True, "treating '.' as a real value"),
    ("row conflict only", place((0, 0, "5"), (0, 8, "5")), False,
     "the row check"),
    ("column conflict only", place((0, 0, "5"), (8, 0, "5")), False,
     "the column check"),
    ("box conflict only", place((0, 0, "5"), (1, 1, "5")), False,
     "the box check, isolated from row and column"),
    ("adjacent across a box edge", place((2, 2, "5"), (3, 3, "5")), True,
     "off-by-one in the box formula: (row//3 + col//3) wrongly fails this"),
    ("full valid row", place(*[(0, c, str(c + 1)) for c in range(9)]), True,
     "1-9 in one row is legal, not a conflict"),
    ("full row with a repeat", place(*[(0, c, str(c + 1)) for c in range(8)],
                                     (0, 8, "1")), False,
     "a conflict at the very end of a scan"),
]


def check_box_index() -> tuple[str, str]:
    """box_index has its own contract, testable before any board logic works."""
    try:
        hits = [0] * 9
        for row in range(9):
            for col in range(9):
                got = box_index(row, col)
                if not isinstance(got, int) or not 0 <= got <= 8:
                    return "FAIL", f"box_index({row}, {col}) returned {got!r}, want an int in 0..8"
                hits[got] += 1
        if hits != [9] * 9:
            return "FAIL", (
                f"each box should receive exactly 9 cells, got {hits}\n"
                "        (the formula must be a bijection onto 0..8 - if two boxes\n"
                "         share an index, valid boards get rejected; if one is never\n"
                "         produced, that box is never checked at all)"
            )
        corners = {(0, 0): 0, (0, 8): 2, (4, 4): 4, (8, 0): 6, (8, 8): 8}
        for (row, col), want in corners.items():
            if box_index(row, col) != want:
                return "FAIL", f"box_index({row}, {col}) = {box_index(row, col)}, want {want}"
        return "PASS", "6/6 checks"
    except NotImplementedError:
        return "SKIP", "not implemented yet"
    except Exception:
        return "ERROR", traceback.format_exc(limit=2).strip()


def check_implementation(fn) -> tuple[str, str]:
    failures = []
    for name, board, expected, catches in CASES:
        # Defensive copy: a buggy solution that mutates the board in place
        # would otherwise corrupt later cases and produce confusing results.
        copy = [row[:] for row in board]
        try:
            got = fn(copy)
        except NotImplementedError:
            return "SKIP", "not implemented yet"
        except Exception:
            return "ERROR", f"{name}: " + traceback.format_exc(limit=2).strip()

        if got is not expected:
            detail = (
                f"{name}: got {got!r}, want {expected!r}\n"
                f"        catches: {catches}"
            )
            if board not in (EXAMPLE_1, EXAMPLE_2):
                detail += "\n" + render(board)
            failures.append(detail)

    if failures:
        return "FAIL", "\n      ".join(failures)
    return "PASS", f"{len(CASES)}/{len(CASES)} cases"


def main() -> int:
    results = [("box_index", *check_box_index())]
    for name, fn in IMPLEMENTATIONS:
        results.append((name, *check_implementation(fn)))

    width = max(len(name) for name, _, _ in results)
    print()
    for name, status, detail in results:
        marker = {"PASS": "ok  ", "FAIL": "FAIL", "SKIP": "--  ", "ERROR": "ERR "}[status]
        print(f"  {marker} {name:<{width}}  {detail.splitlines()[0]}")
        for line in detail.splitlines()[1:]:
            print(f"       {line}")

    passed = sum(1 for _, s, _ in results if s == "PASS")
    skipped = sum(1 for _, s, _ in results if s == "SKIP")
    broken = len(results) - passed - skipped

    print(f"\n  {passed} passed, {skipped} not implemented, {broken} failing")
    if skipped == len(results):
        print("  Nothing implemented yet - start with box_index().")
    elif broken == 0 and skipped == 0:
        print("  All four done. Now say the approach out loud in under 90 seconds.")
    print()

    return 1 if broken else 0


if __name__ == "__main__":
    sys.exit(main())
