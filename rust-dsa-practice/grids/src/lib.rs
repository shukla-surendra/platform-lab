//! Reusable scaffolding for grid problems - any `rows x cols`, not just 9x9.
//!
//! ## What this is for
//!
//! A large family of interview problems is "a graph wearing a grid costume":
//! Number of Islands, Rotting Oranges, Word Search, Shortest Path in Binary
//! Matrix, Walls and Gates, Pacific Atlantic, Surrounded Regions, Sudoku
//! Solver, N-Queens. They differ in three small places and are otherwise the
//! same code:
//!
//!   1. which neighbours count (4-way? 8-way? knight? diagonals only?),
//!   2. what "passable" means (not a wall / same colour / letter matches),
//!   3. what you accumulate (a count, a distance, a path, a set of cells).
//!
//! Everything else - bounds checking, the visited set, the frontier - is
//! boilerplate you should be able to write without thinking. That's what this
//! module is: the boilerplate, written once, so practice time goes into the
//! three things that actually vary.
//!
//! ## Interview-scale vs. lab-scale
//!
//! Do NOT try to reproduce this file on a whiteboard. Under time pressure you
//! write the ~10-line core (see `README`-level note in
//! `docs/grid-traversal-scaffold.md`) and nothing else. This crate exists so
//! that when you *practise*, the interesting part isn't retyping `in_bounds`
//! for the fortieth time.
//!
//! ## The one Rust-specific trap
//!
//! Grid coordinates are `usize`. Direction deltas are negative. `row - 1` when
//! `row == 0` does not give you `-1`; it **panics in debug and wraps to
//! `usize::MAX` in release**. Every neighbour helper here goes through
//! [`usize::checked_add_signed`], which returns `None` on underflow - so the
//! "did I fall off the top edge" check and the "did I fall off the bottom
//! edge" check are handled by two different mechanisms. See
//! [`Grid::neighbors`].

use std::cmp::Reverse;
use std::collections::{BinaryHeap, VecDeque};
use std::fmt;
use std::ops::{Index, IndexMut};

// ===========================================================================
// Direction sets
// ===========================================================================
// Order matters more than people expect: it fixes the tie-breaking order of
// BFS/DFS, so a path-reconstruction test that hardcodes one specific shortest
// path is really testing this constant. Prefer asserting on path *length*.

/// Von Neumann neighbourhood - up, down, left, right. The default.
pub const DIRS4: [(isize, isize); 4] = [(-1, 0), (1, 0), (0, -1), (0, 1)];

/// Moore neighbourhood - the 8 surrounding cells, diagonals included.
pub const DIRS8: [(isize, isize); 8] = [
    (-1, -1),
    (-1, 0),
    (-1, 1),
    (0, -1),
    (0, 1),
    (1, -1),
    (1, 0),
    (1, 1),
];

/// The four diagonals only.
pub const DIRS_DIAG: [(isize, isize); 4] = [(-1, -1), (-1, 1), (1, -1), (1, 1)];

/// Knight moves - Knight Dialer, Minimum Knight Moves, N-Knights.
pub const KNIGHT: [(isize, isize); 8] = [
    (-2, -1),
    (-2, 1),
    (-1, -2),
    (-1, 2),
    (1, -2),
    (1, 2),
    (2, -1),
    (2, 1),
];

/// A cell coordinate, `(row, col)`.
pub type Cell = (usize, usize);

// ===========================================================================
// Grid<T>
// ===========================================================================

/// A rectangular grid stored as a single flat `Vec<T>` in row-major order.
///
/// **Why flat instead of `Vec<Vec<T>>`?** One allocation instead of `rows + 1`;
/// contiguous memory, so row-order scans are cache-friendly; and every cell has
/// a single `usize` identity (`idx`) that slots straight into a `Vec`-backed
/// visited/distance/parent array with no hashing. The cost is that you index
/// through `self.idx(r, c)` rather than `g[r][c]`, which the [`Index`] impl
/// below hides: `g[(r, c)]`.
///
/// `idx = row * cols + col` is the same row-major flattening as the Sudoku box
/// formula `(row / 3) * 3 + (col / 3)` - there, the "grid" is the 3x3 grid of
/// boxes and the "width" is 3.
#[derive(Clone, PartialEq, Eq)]
pub struct Grid<T> {
    pub rows: usize,
    pub cols: usize,
    pub cells: Vec<T>,
}

impl<T> Grid<T> {
    /// A `rows x cols` grid with every cell set to `fill`.
    pub fn new(rows: usize, cols: usize, fill: T) -> Self
    where
        T: Clone,
    {
        Grid {
            rows,
            cols,
            cells: vec![fill; rows * cols],
        }
    }

    /// Build from nested rows. Panics if the rows are ragged - a ragged grid is
    /// almost always a parsing bug, and failing loudly here beats an
    /// out-of-bounds panic three functions later.
    pub fn from_vecs(rows: Vec<Vec<T>>) -> Self {
        let n_rows = rows.len();
        let n_cols = rows.first().map_or(0, |r| r.len());
        assert!(
            rows.iter().all(|r| r.len() == n_cols),
            "ragged grid: all rows must have the same length"
        );
        Grid {
            rows: n_rows,
            cols: n_cols,
            cells: rows.into_iter().flatten().collect(),
        }
    }

    /// `(row, col)` -> flat index. Row-major.
    #[inline]
    pub fn idx(&self, r: usize, c: usize) -> usize {
        r * self.cols + c
    }

    /// Flat index -> `(row, col)`. The inverse of [`Grid::idx`].
    #[inline]
    pub fn coord(&self, idx: usize) -> Cell {
        (idx / self.cols, idx % self.cols)
    }

    #[inline]
    pub fn len(&self) -> usize {
        self.cells.len()
    }

    #[inline]
    pub fn is_empty(&self) -> bool {
        self.cells.is_empty()
    }

    /// Bounds check on already-unsigned coordinates. Note there is no `>= 0`
    /// test: `usize` cannot be negative, so the *only* way to fall off the top
    /// or left edge is an underflow that happened earlier - which is exactly
    /// what [`Grid::neighbors`] catches with `checked_add_signed`.
    #[inline]
    pub fn in_bounds(&self, r: usize, c: usize) -> bool {
        r < self.rows && c < self.cols
    }

    pub fn get(&self, r: usize, c: usize) -> Option<&T> {
        self.in_bounds(r, c).then(|| &self.cells[self.idx(r, c)])
    }

    pub fn get_mut(&mut self, r: usize, c: usize) -> Option<&mut T> {
        if self.in_bounds(r, c) {
            let i = self.idx(r, c);
            Some(&mut self.cells[i])
        } else {
            None
        }
    }

    /// Every in-bounds cell, row-major. Handy for "scan for all starts" passes.
    pub fn iter_cells(&self) -> impl Iterator<Item = Cell> + use<T> {
        let cols = self.cols;
        (0..self.rows * cols).map(move |i| (i / cols, i % cols))
    }

    /// In-bounds neighbours of `(r, c)` under an arbitrary direction set.
    ///
    /// This is the function the whole module exists for. Two distinct failure
    /// modes are handled by two different mechanisms, and conflating them is
    /// the classic grid bug:
    ///
    /// - **top / left edge**: `r.checked_add_signed(-1)` when `r == 0` returns
    ///   `None`, because the result would be negative. `?` in the closure turns
    ///   that into "skip this direction".
    /// - **bottom / right edge**: no underflow happens, so we need the explicit
    ///   `nr < rows && nc < cols` test.
    ///
    /// The returned iterator captures `rows`/`cols` **by copy**, so it does not
    /// borrow `self` - meaning you can mutate the grid while iterating a cell's
    /// neighbours, which flood-fill and backtracking both need.
    pub fn neighbors(
        &self,
        r: usize,
        c: usize,
        dirs: &'static [(isize, isize)],
    ) -> impl Iterator<Item = Cell> + use<T> {
        let (rows, cols) = (self.rows, self.cols);
        dirs.iter().filter_map(move |&(dr, dc)| {
            let nr = r.checked_add_signed(dr)?;
            let nc = c.checked_add_signed(dc)?;
            (nr < rows && nc < cols).then_some((nr, nc))
        })
    }

    /// [`Grid::neighbors`] with [`DIRS4`] - the common case.
    pub fn neighbors4(&self, r: usize, c: usize) -> impl Iterator<Item = Cell> + use<T> {
        self.neighbors(r, c, &DIRS4)
    }

    /// [`Grid::neighbors`] with [`DIRS8`].
    pub fn neighbors8(&self, r: usize, c: usize) -> impl Iterator<Item = Cell> + use<T> {
        self.neighbors(r, c, &DIRS8)
    }

    /// Rows and columns swapped. `Rotate Image`, `Transpose Matrix`.
    pub fn transpose(&self) -> Grid<T>
    where
        T: Clone,
    {
        let mut cells = Vec::with_capacity(self.len());
        for c in 0..self.cols {
            for r in 0..self.rows {
                cells.push(self.cells[self.idx(r, c)].clone());
            }
        }
        Grid {
            rows: self.cols,
            cols: self.rows,
            cells,
        }
    }

    /// Rotate clockwise 90 degrees = transpose, then reverse each row.
    /// Worth remembering as that decomposition rather than as index algebra.
    pub fn rotate_cw(&self) -> Grid<T>
    where
        T: Clone,
    {
        let mut g = self.transpose();
        for r in 0..g.rows {
            let start = r * g.cols;
            g.cells[start..start + g.cols].reverse();
        }
        g
    }
}

impl Grid<char> {
    /// Parse from string rows - the shape LeetCode hands you.
    ///
    /// ```
    /// # use grids::Grid;
    /// let g = Grid::from_lines(&["..#", ".#.", "..."]);
    /// assert_eq!((g.rows, g.cols), (3, 3));
    /// assert_eq!(g[(1, 1)], '#');
    /// ```
    pub fn from_lines(lines: &[&str]) -> Self {
        Grid::from_vecs(lines.iter().map(|l| l.chars().collect()).collect())
    }
}

impl<T> Index<Cell> for Grid<T> {
    type Output = T;
    fn index(&self, (r, c): Cell) -> &T {
        &self.cells[r * self.cols + c]
    }
}

impl<T> IndexMut<Cell> for Grid<T> {
    fn index_mut(&mut self, (r, c): Cell) -> &mut T {
        let i = r * self.cols + c;
        &mut self.cells[i]
    }
}

/// Renders row-by-row rather than as one flat `Vec`, so a failing `assert_eq!`
/// on two grids is actually readable.
impl<T: fmt::Debug> fmt::Debug for Grid<T> {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        writeln!(f, "Grid {}x{} [", self.rows, self.cols)?;
        for r in 0..self.rows {
            writeln!(f, "  {:?}", &self.cells[r * self.cols..(r + 1) * self.cols])?;
        }
        write!(f, "]")
    }
}

impl fmt::Display for Grid<char> {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        for r in 0..self.rows {
            let row: String = self.cells[r * self.cols..(r + 1) * self.cols].iter().collect();
            writeln!(f, "{row}")?;
        }
        Ok(())
    }
}

// ===========================================================================
// BFS - unweighted shortest path
// ===========================================================================

/// Result of a BFS sweep: distance to every reachable cell, plus enough
/// information to rebuild the path.
pub struct BfsResult {
    /// `dist[idx]` = steps from the nearest source, or `None` if unreachable.
    pub dist: Vec<Option<u32>>,
    /// `prev[idx]` = flat index of the cell we arrived from, or `usize::MAX`
    /// for a source / unvisited cell.
    pub prev: Vec<usize>,
    cols: usize,
}

impl BfsResult {
    pub fn dist_at(&self, r: usize, c: usize) -> Option<u32> {
        self.dist[r * self.cols + c]
    }

    /// Walk `prev` backwards from `goal` to its source. Returns `None` if the
    /// goal was never reached.
    ///
    /// The path comes out backwards and gets reversed - that reversal is the
    /// step people forget, and it produces a silently-mirrored answer rather
    /// than a crash.
    pub fn path_to(&self, goal: Cell) -> Option<Vec<Cell>> {
        let goal_idx = goal.0 * self.cols + goal.1;
        self.dist[goal_idx]?;

        let mut path = vec![goal];
        let mut cur = goal_idx;
        while self.prev[cur] != usize::MAX {
            cur = self.prev[cur];
            path.push((cur / self.cols, cur % self.cols));
        }
        path.reverse();
        Some(path)
    }
}

/// Breadth-first search from one or more sources.
///
/// **Multi-source is not a special case** - seeding the queue with every source
/// at distance 0 makes BFS compute "distance to the *nearest* source" for free.
/// That is the entire trick behind Rotting Oranges, Walls and Gates, and
/// 01 Matrix. Recognising that those are one-liner variations of plain BFS,
/// rather than three separate techniques, is most of the value here.
///
/// `passable(&cell_value) -> bool` decides what counts as walkable. Sources are
/// enqueued even if `passable` would reject them, which is what you want for
/// "distance from every wall" style problems.
///
/// Time O(rows * cols), space O(rows * cols).
pub fn bfs<T>(
    grid: &Grid<T>,
    sources: impl IntoIterator<Item = Cell>,
    dirs: &'static [(isize, isize)],
    passable: impl Fn(&T) -> bool,
) -> BfsResult {
    let n = grid.len();
    let mut dist = vec![None; n];
    let mut prev = vec![usize::MAX; n];
    let mut queue = VecDeque::new();

    for (r, c) in sources {
        let i = grid.idx(r, c);
        if dist[i].is_none() {
            dist[i] = Some(0);
            queue.push_back((r, c));
        }
    }

    while let Some((r, c)) = queue.pop_front() {
        let d = dist[grid.idx(r, c)].expect("queued cells always have a distance");
        for (nr, nc) in grid.neighbors(r, c, dirs) {
            let ni = grid.idx(nr, nc);
            // Mark visited at ENQUEUE time, not dequeue time. Marking on
            // dequeue lets the same cell enter the queue several times before
            // it is first processed - still correct, but the queue can blow up
            // to O(V * degree) instead of O(V).
            if dist[ni].is_none() && passable(&grid.cells[ni]) {
                dist[ni] = Some(d + 1);
                prev[ni] = grid.idx(r, c);
                queue.push_back((nr, nc));
            }
        }
    }

    BfsResult {
        dist,
        prev,
        cols: grid.cols,
    }
}

/// Shortest path between two cells, or `None` if unreachable.
pub fn shortest_path<T>(
    grid: &Grid<T>,
    start: Cell,
    goal: Cell,
    dirs: &'static [(isize, isize)],
    passable: impl Fn(&T) -> bool,
) -> Option<Vec<Cell>> {
    bfs(grid, [start], dirs, passable).path_to(goal)
}

// ===========================================================================
// DFS / flood fill / connected components
// ===========================================================================

/// Iterative flood fill from `start`, returning every cell in the region.
///
/// **Iterative on purpose.** The recursive version is prettier and blows the
/// stack on large inputs: a 1000x1000 grid that is one long snaking corridor
/// is a million-deep recursion, and Rust's 8 MB main-thread stack does not
/// survive that. On LeetCode-sized inputs recursion is fine; know which one
/// you are writing and why.
///
/// `visited` is threaded in so callers can run many fills over one shared
/// visited map - that's what [`connected_components`] does.
pub fn flood_fill<T>(
    grid: &Grid<T>,
    start: Cell,
    dirs: &'static [(isize, isize)],
    visited: &mut [bool],
    passable: impl Fn(&T) -> bool,
) -> Vec<Cell> {
    let mut region = Vec::new();
    let start_idx = grid.idx(start.0, start.1);

    if visited[start_idx] || !passable(&grid.cells[start_idx]) {
        return region;
    }

    let mut stack = vec![start];
    visited[start_idx] = true;

    while let Some((r, c)) = stack.pop() {
        region.push((r, c));
        for (nr, nc) in grid.neighbors(r, c, dirs) {
            let ni = grid.idx(nr, nc);
            if !visited[ni] && passable(&grid.cells[ni]) {
                visited[ni] = true;
                stack.push((nr, nc));
            }
        }
    }

    region
}

/// Every maximal connected region of passable cells. `Number of Islands` is
/// `connected_components(..).len()`; `Max Area of Island` is
/// `.map(|r| r.len()).max()`.
pub fn connected_components<T>(
    grid: &Grid<T>,
    dirs: &'static [(isize, isize)],
    passable: impl Fn(&T) -> bool,
) -> Vec<Vec<Cell>> {
    let mut visited = vec![false; grid.len()];
    let mut out = Vec::new();

    for (r, c) in grid.iter_cells() {
        let region = flood_fill(grid, (r, c), dirs, &mut visited, &passable);
        if !region.is_empty() {
            out.push(region);
        }
    }

    out
}

// ===========================================================================
// Dijkstra - weighted shortest path
// ===========================================================================

/// Dijkstra over a grid where entering a cell costs `cost(&cell) -> Option<u64>`
/// (`None` = impassable). Returns cost-to-reach for every cell.
///
/// Reach for this the moment steps stop costing the same - terrain costs,
/// `Path With Minimum Effort`, `Swim in Rising Water`. If every step costs 1,
/// use [`bfs`]: it is O(V + E) against Dijkstra's O(E log V), and simpler.
///
/// Two Rust details that are easy to get wrong:
/// - [`BinaryHeap`] is a **max**-heap; [`Reverse`] flips it into a min-heap.
/// - Tuple ordering is lexicographic, so `(cost, idx)` sorts by cost first,
///   which is what makes the bare tuple work as a priority.
///
/// There is no decrease-key here - we push duplicates and skip stale entries
/// on pop (the `> best[i]` guard). That is the standard, and simpler, trade.
pub fn dijkstra<T>(
    grid: &Grid<T>,
    start: Cell,
    dirs: &'static [(isize, isize)],
    cost: impl Fn(&T) -> Option<u64>,
) -> Vec<Option<u64>> {
    let n = grid.len();
    let mut best: Vec<Option<u64>> = vec![None; n];
    let mut heap = BinaryHeap::new();

    let s = grid.idx(start.0, start.1);
    best[s] = Some(0);
    heap.push(Reverse((0u64, s)));

    while let Some(Reverse((d, i))) = heap.pop() {
        // Stale entry: we already found a cheaper route to `i` after this one
        // was pushed. Skipping is what replaces decrease-key.
        if best[i].is_some_and(|b| d > b) {
            continue;
        }
        let (r, c) = grid.coord(i);
        for (nr, nc) in grid.neighbors(r, c, dirs) {
            let ni = grid.idx(nr, nc);
            let Some(step) = cost(&grid.cells[ni]) else {
                continue;
            };
            let nd = d + step;
            if best[ni].is_none_or(|b| nd < b) {
                best[ni] = Some(nd);
                heap.push(Reverse((nd, ni)));
            }
        }
    }

    best
}

// ===========================================================================
// Backtracking on a grid
// ===========================================================================

/// Word Search (LC 79): does `word` appear as a 4-directionally connected path
/// with no cell reused?
///
/// This is the **mark / recurse / unmark** template, and the unmark is the
/// whole thing. A DFS that explores reachability marks a cell visited forever.
/// A DFS that explores *paths* must un-mark on the way out, because a cell
/// blocked on this path may be essential on a different one. Forgetting the
/// restore is the single most common backtracking bug - it does not crash, it
/// just returns `false` on inputs that should succeed.
///
/// Complexity O(rows * cols * 4^len) worst case; the length check prunes hard
/// in practice.
pub fn word_search(grid: &Grid<char>, word: &str) -> bool {
    let word: Vec<char> = word.chars().collect();
    if word.is_empty() {
        return true;
    }
    if word.len() > grid.len() {
        return false;
    }

    let mut used = vec![false; grid.len()];

    fn dfs(grid: &Grid<char>, word: &[char], k: usize, r: usize, c: usize, used: &mut [bool]) -> bool {
        let i = grid.idx(r, c);
        if used[i] || grid.cells[i] != word[k] {
            return false;
        }
        if k + 1 == word.len() {
            return true;
        }

        used[i] = true; // mark
        let found = grid
            .neighbors4(r, c)
            .any(|(nr, nc)| dfs(grid, word, k + 1, nr, nc, used));
        used[i] = false; // UNMARK - the line everyone forgets

        found
    }

    grid.iter_cells()
        .any(|(r, c)| dfs(grid, &word, 0, r, c, &mut used))
}

#[cfg(test)]
mod tests {
    use super::*;

    // -- coordinates ------------------------------------------------------

    #[test]
    fn idx_and_coord_are_inverses() {
        let g = Grid::new(4, 7, 0u8);
        for i in 0..g.len() {
            let (r, c) = g.coord(i);
            assert_eq!(g.idx(r, c), i);
        }
    }

    #[test]
    fn corner_neighbors_do_not_underflow() {
        // The whole reason checked_add_signed is used. In a naive `r - 1`
        // implementation this panics in debug / wraps in release.
        let g = Grid::new(3, 3, 0u8);
        let mut got: Vec<Cell> = g.neighbors4(0, 0).collect();
        got.sort();
        assert_eq!(got, vec![(0, 1), (1, 0)]);
    }

    #[test]
    fn far_corner_neighbors_respect_upper_bound() {
        let g = Grid::new(3, 3, 0u8);
        let mut got: Vec<Cell> = g.neighbors4(2, 2).collect();
        got.sort();
        assert_eq!(got, vec![(1, 2), (2, 1)]);
    }

    #[test]
    fn interior_cell_has_full_neighbourhoods() {
        let g = Grid::new(3, 3, 0u8);
        assert_eq!(g.neighbors4(1, 1).count(), 4);
        assert_eq!(g.neighbors8(1, 1).count(), 8);
        assert_eq!(g.neighbors(1, 1, &KNIGHT).count(), 0); // all off-board on 3x3
    }

    #[test]
    fn non_square_grids_are_not_transposed_by_accident() {
        // Guards the classic rows/cols swap: on a square grid this bug is
        // invisible, which is why a non-square fixture matters.
        let g = Grid::from_lines(&["abcd", "efgh", "ijkl"]);
        assert_eq!((g.rows, g.cols), (3, 4));
        assert_eq!(g[(2, 3)], 'l');
        assert_eq!(g.idx(2, 3), 11);
    }

    // -- bfs --------------------------------------------------------------

    #[test]
    fn bfs_finds_shortest_path_around_a_wall() {
        let g = Grid::from_lines(&[".....", ".###.", ".....",]);
        let path = shortest_path(&g, (0, 0), (2, 4), &DIRS4, |&ch| ch != '#').unwrap();
        assert_eq!(path.first(), Some(&(0, 0)));
        assert_eq!(path.last(), Some(&(2, 4)));
        assert_eq!(path.len(), 7); // 6 moves; assert length, not identity
        assert!(path.iter().all(|&(r, c)| g[(r, c)] != '#'));
    }

    #[test]
    fn bfs_reports_unreachable() {
        let g = Grid::from_lines(&[".#.", ".#.", ".#."]);
        assert!(shortest_path(&g, (0, 0), (0, 2), &DIRS4, |&ch| ch != '#').is_none());
    }

    #[test]
    fn diagonal_moves_shorten_the_path() {
        let g = Grid::from_lines(&["...", "...", "..."]);
        let four = shortest_path(&g, (0, 0), (2, 2), &DIRS4, |_| true).unwrap();
        let eight = shortest_path(&g, (0, 0), (2, 2), &DIRS8, |_| true).unwrap();
        assert_eq!(four.len(), 5); // 4 moves
        assert_eq!(eight.len(), 3); // 2 diagonal moves
    }

    #[test]
    fn multi_source_bfs_measures_distance_to_nearest_source() {
        // Rotting Oranges / 01 Matrix in one call.
        let g = Grid::from_lines(&["S...S"]);
        let sources: Vec<Cell> = g.iter_cells().filter(|&(r, c)| g[(r, c)] == 'S').collect();
        let res = bfs(&g, sources, &DIRS4, |_| true);
        assert_eq!(res.dist_at(0, 0), Some(0));
        assert_eq!(res.dist_at(0, 1), Some(1));
        assert_eq!(res.dist_at(0, 2), Some(2)); // 2 from each side, not 4
        assert_eq!(res.dist_at(0, 3), Some(1));
        assert_eq!(res.dist_at(0, 4), Some(0));
    }

    #[test]
    fn path_of_length_one_is_the_start_itself() {
        let g = Grid::from_lines(&["..."]);
        let path = shortest_path(&g, (1 - 1, 0), (0, 0), &DIRS4, |_| true).unwrap();
        assert_eq!(path, vec![(0, 0)]);
    }

    // -- components -------------------------------------------------------

    #[test]
    fn number_of_islands() {
        let g = Grid::from_lines(&["11000", "11000", "00100", "00011"]);
        let comps = connected_components(&g, &DIRS4, |&ch| ch == '1');
        assert_eq!(comps.len(), 3);
        assert_eq!(comps.iter().map(|r| r.len()).max(), Some(4));
    }

    #[test]
    fn diagonal_connectivity_merges_islands() {
        // Same board, 8-way: the lone '1' now bridges two islands.
        let g = Grid::from_lines(&["11000", "11000", "00100", "00011"]);
        assert_eq!(connected_components(&g, &DIRS8, |&ch| ch == '1').len(), 1);
    }

    #[test]
    fn components_cover_every_passable_cell_exactly_once() {
        let g = Grid::from_lines(&["1.1", ".1.", "1.1"]);
        let comps = connected_components(&g, &DIRS4, |&ch| ch == '1');
        let total: usize = comps.iter().map(|r| r.len()).sum();
        assert_eq!(total, 5);
        let mut all: Vec<Cell> = comps.into_iter().flatten().collect();
        all.sort();
        all.dedup();
        assert_eq!(all.len(), 5, "a cell landed in two components");
    }

    // -- dijkstra ---------------------------------------------------------

    #[test]
    fn dijkstra_prefers_the_cheap_detour_over_the_short_expensive_route() {
        // Start (0,0), goal (0,4). Two routes that disagree:
        //   straight across row 0 - 4 steps,  cost 9+9+9+1 = 28
        //   down and around row 2 - 8 steps,  cost 1x8     =  8
        // BFS optimises steps and must take the first; Dijkstra optimises cost
        // and must take the second. If a test can't tell those two apart, it
        // isn't testing Dijkstra at all - which is what the first draft of this
        // test got wrong.
        let g = Grid::from_vecs(vec![
            vec![0u64, 9, 9, 9, 1],
            vec![1, 9, 9, 9, 1],
            vec![1, 1, 1, 1, 1],
        ]);

        let best = dijkstra(&g, (0, 0), &DIRS4, |&w| Some(w));
        assert_eq!(best[g.idx(0, 4)], Some(8), "Dijkstra should take the cheap detour");

        let hops = shortest_path(&g, (0, 0), (0, 4), &DIRS4, |_| true).unwrap();
        assert_eq!(hops.len(), 5, "BFS should take the short expensive route");
    }

    #[test]
    fn dijkstra_marks_walls_unreachable() {
        let g = Grid::from_vecs(vec![vec![0u64, u64::MAX, 0]]);
        let best = dijkstra(&g, (0, 0), &DIRS4, |&w| (w != u64::MAX).then_some(w));
        assert_eq!(best[g.idx(0, 0)], Some(0));
        assert_eq!(best[g.idx(0, 1)], None);
        assert_eq!(best[g.idx(0, 2)], None);
    }

    // -- backtracking -----------------------------------------------------

    #[test]
    fn word_search_finds_a_bending_word() {
        let g = Grid::from_lines(&["ABCE", "SFCS", "ADEE"]);
        assert!(word_search(&g, "ABCCED"));
        assert!(word_search(&g, "SEE"));
        assert!(!word_search(&g, "ABCB")); // would need to reuse 'B'
    }

    #[test]
    fn word_search_restores_state_between_attempts() {
        // If `used` were not un-marked, the failed "AAB" prefix walk would
        // leave cells poisoned and the later valid word would be missed.
        let g = Grid::from_lines(&["AAA", "AAA"]);
        assert!(!word_search(&g, "AAB"));
        assert!(word_search(&g, "AAAAAA"));
    }

    // -- transforms -------------------------------------------------------

    #[test]
    fn rotate_cw_is_transpose_then_reverse_rows() {
        let g = Grid::from_lines(&["ab", "cd"]);
        assert_eq!(g.transpose(), Grid::from_lines(&["ac", "bd"]));
        assert_eq!(g.rotate_cw(), Grid::from_lines(&["ca", "db"]));
    }

    #[test]
    fn four_rotations_return_to_the_original() {
        let g = Grid::from_lines(&["abcd", "efgh", "ijkl"]);
        assert_eq!(g.rotate_cw().rotate_cw().rotate_cw().rotate_cw(), g);
    }
}
