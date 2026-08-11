"""8. Valid Sudoku — Medium
One pass over the cells; each cell reports the three groups it belongs to
(row, column, 3x3 box) and is checked against all three at once.
"""
from typing import List


def is_valid_sudoku(board: List[List[str]]) -> bool:
    rows = [set() for _ in range(9)]
    cols = [set() for _ in range(9)]
    boxes = [set() for _ in range(9)]

    for row in range(9):
        for col in range(9):
            value = board[row][col]
            if value == ".":
                continue

            # 2D (band, stack) -> 1D, the usual row-major flattening
            box_index = (row // 3) * 3 + (col // 3)

            if (value in rows[row]
                    or value in cols[col]
                    or value in boxes[box_index]):
                return False

            rows[row].add(value)
            cols[col].add(value)
            boxes[box_index].add(value)

    return True


if __name__ == "__main__":
    valid = [
        list("53..7...."),
        list("6..195..."),
        list(".98....6."),
        list("8...6...3"),
        list("4..8.3..1"),
        list("7...2...6"),
        list(".6....28."),
        list("...419..5"),
        list("....8..79"),
    ]
    # Same board, top-left 5 -> 8: two 8s in the top-left box.
    # No row or column conflict — only the box rule catches this one.
    box_conflict = [row[:] for row in valid]
    box_conflict[0][0] = "8"

    empty = [["."] * 9 for _ in range(9)]

    row_only = [["."] * 9 for _ in range(9)]
    row_only[0][0] = row_only[0][8] = "5"

    col_only = [["."] * 9 for _ in range(9)]
    col_only[0][0] = col_only[8][0] = "5"

    # Diagonally adjacent but in different boxes — guards the box formula
    across_boundary = [["."] * 9 for _ in range(9)]
    across_boundary[2][2] = across_boundary[3][3] = "5"

    assert is_valid_sudoku(valid) is True
    assert is_valid_sudoku(box_conflict) is False
    assert is_valid_sudoku(empty) is True
    assert is_valid_sudoku(row_only) is False
    assert is_valid_sudoku(col_only) is False
    assert is_valid_sudoku(across_boundary) is True
    print("All tests passed.")
