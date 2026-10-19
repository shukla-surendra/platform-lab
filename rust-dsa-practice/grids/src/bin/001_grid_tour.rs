// A runnable tour of the `grids` scaffold. Every primitive, with output you
// can eyeball.
//
//     cargo run --bin 001_grid_tour
//
// Read this top-to-bottom once, then use it as a lookup table. The first
// section is the only part you should ever reproduce from memory.

use grids::{DIRS4, DIRS8, Grid, KNIGHT, bfs, connected_components, dijkstra, shortest_path};

// ===========================================================================
// PART 0 - what you actually write in an interview
// ===========================================================================
// Do NOT try to rebuild the library on a whiteboard. This is the whole thing,
// standalone, ~12 lines. Everything else in this crate is convenience for
// practice, not something to memorise.
//
// Commit THIS to muscle memory:
fn count_islands_from_scratch(grid: &[Vec<char>]) -> usize {
    let (rows, cols) = (grid.len(), grid[0].len());
    let mut seen = vec![vec![false; cols]; rows];
    let mut count = 0;

    for r in 0..rows {
        for c in 0..cols {
            if grid[r][c] != '1' || seen[r][c] {
                continue;
            }
            count += 1;
            let mut stack = vec![(r, c)];
            seen[r][c] = true;
            while let Some((cr, cc)) = stack.pop() {
                for (dr, dc) in [(-1i32, 0i32), (1, 0), (0, -1), (0, 1)] {
                    // The one line that matters: cast to a signed type, bounds
                    // check, cast back. `cr - 1` on a usize would underflow.
                    let (nr, nc) = (cr as i32 + dr, cc as i32 + dc);
                    if nr < 0 || nc < 0 || nr >= rows as i32 || nc >= cols as i32 {
                        continue;
                    }
                    let (nr, nc) = (nr as usize, nc as usize);
                    if grid[nr][nc] == '1' && !seen[nr][nc] {
                        seen[nr][nc] = true;
                        stack.push((nr, nc));
                    }
                }
            }
        }
    }
    count
}

fn banner(title: &str) {
    println!("\n=== {title} {}", "=".repeat(58usize.saturating_sub(title.len())));
}

fn main() {
    // -----------------------------------------------------------------
    banner("0. the from-scratch core");
    let raw: Vec<Vec<char>> = ["11000", "11000", "00100", "00011"]
        .iter()
        .map(|s| s.chars().collect())
        .collect();
    println!("islands (hand-written, no library) = {}", count_islands_from_scratch(&raw));

    // -----------------------------------------------------------------
    banner("1. construction and indexing");
    let g = Grid::from_lines(&["..#..", ".#...", ".....", "..#.#"]);
    println!("{g}");
    println!("dims          = {}x{}", g.rows, g.cols);
    println!("g[(1,1)]      = {:?}", g[(1, 1)]);
    println!("idx(1,1)      = {}   (row-major: 1 * cols + 1)", g.idx(1, 1));
    println!("coord(6)      = {:?}  (the inverse)", g.coord(6));
    println!("get(9,9)      = {:?}  (out of bounds -> None, no panic)", g.get(9, 9));

    // -----------------------------------------------------------------
    banner("2. neighbours - the underflow-safe part");
    println!("corner (0,0) 4-way : {:?}", g.neighbors4(0, 0).collect::<Vec<_>>());
    println!("  ^ two neighbours, not four. (-1,0) and (0,-1) underflow to None.");
    println!("centre (2,2) 4-way : {:?}", g.neighbors4(2, 2).collect::<Vec<_>>());
    println!("centre (2,2) 8-way : {:?}", g.neighbors8(2, 2).collect::<Vec<_>>());
    println!("centre (2,2) knight: {:?}", g.neighbors(2, 2, &KNIGHT).collect::<Vec<_>>());

    // -----------------------------------------------------------------
    banner("3. BFS - unweighted shortest path");
    let maze = Grid::from_lines(&[".....", ".###.", ".....", ".###.", "....."]);
    println!("{maze}");
    let path = shortest_path(&maze, (0, 0), (4, 4), &DIRS4, |&ch| ch != '#').unwrap();
    println!("(0,0) -> (4,4) in {} moves", path.len() - 1);
    println!("path: {path:?}");

    // Overlay the path onto a copy of the maze - the fastest way to eyeball
    // whether a path result is actually sane.
    let mut drawn = maze.clone();
    for &(r, c) in &path {
        drawn[(r, c)] = 'o';
    }
    println!("\n{drawn}");

    // -----------------------------------------------------------------
    banner("4. multi-source BFS - 'distance to nearest X'");
    // Rotting Oranges, Walls and Gates, 01 Matrix are all THIS, not three
    // separate algorithms: seed the queue with every source at distance 0.
    let orchard = Grid::from_lines(&["R...R", ".....", "....."]);
    let sources: Vec<_> = orchard
        .iter_cells()
        .filter(|&(r, c)| orchard[(r, c)] == 'R')
        .collect();
    let res = bfs(&orchard, sources, &DIRS4, |_| true);
    println!("{orchard}");
    for r in 0..orchard.rows {
        let row: Vec<String> = (0..orchard.cols)
            .map(|c| match res.dist_at(r, c) {
                Some(d) => d.to_string(),
                None => "-".into(),
            })
            .collect();
        println!("{}", row.join(" "));
    }
    println!("^ minutes until every cell is reached; max = the answer to Rotting Oranges");

    // -----------------------------------------------------------------
    banner("5. connected components - islands, regions, blobs");
    let islands = Grid::from_lines(&["11000", "11000", "00100", "00011"]);
    println!("{islands}");
    let comps4 = connected_components(&islands, &DIRS4, |&ch| ch == '1');
    let comps8 = connected_components(&islands, &DIRS8, |&ch| ch == '1');
    println!("4-way: {} islands, largest = {}", comps4.len(),
             comps4.iter().map(|r| r.len()).max().unwrap());
    println!("8-way: {} islands  <- diagonals bridge them into one", comps8.len());
    println!("  ^ same board, same code, ONE constant changed. That's the whole");
    println!("    difference between Number of Islands and its diagonal variant.");

    // -----------------------------------------------------------------
    banner("6. Dijkstra - when steps stop costing the same");
    let terrain = Grid::from_vecs(vec![
        vec![0u64, 9, 9, 9, 1],
        vec![1, 9, 9, 9, 1],
        vec![1, 1, 1, 1, 1],
    ]);
    let cheapest = dijkstra(&terrain, (0, 0), &DIRS4, |&w| Some(w));
    let hops = shortest_path(&terrain, (0, 0), (0, 4), &DIRS4, |_| true).unwrap();
    println!("terrain costs:");
    for r in 0..terrain.rows {
        let row: Vec<String> = (0..terrain.cols).map(|c| terrain[(r, c)].to_string()).collect();
        println!("  {}", row.join(" "));
    }
    println!("BFS      (0,0)->(0,4): {} moves, straight across the 9s", hops.len() - 1);
    println!("Dijkstra (0,0)->(0,4): cost {:?}, the long way round",
             cheapest[terrain.idx(0, 4)]);
    println!("  ^ they disagree. Use BFS only when every step costs the same.");

    // -----------------------------------------------------------------
    banner("7. transforms");
    let small = Grid::from_lines(&["abcd", "efgh", "ijkl"]);
    println!("original:\n{small}");
    println!("transpose:\n{}", small.transpose());
    println!("rotate cw (= transpose, then reverse each row):\n{}", small.rotate_cw());
}
