# rust_dsa_problems
Rust dsa problems

## Running a problem

Each topic (`recursion`, `binary_search_tree`, `arrays_hashing`, ...) is its own Cargo crate.
Every problem file under a crate's `src/bin/` directory is a separate binary,
named after the file (without `.rs`).

Run one from inside the crate directory:

```
cd recursion
cargo run --bin 006_reverse_array_recursion
```

Or from the repo root, using `--manifest-path`:

```
cargo run --manifest-path recursion/Cargo.toml --bin 006_reverse_array_recursion
```

List the available binaries in a crate with:

```
cargo run --bin
```

(passing no name prints the list of valid `--bin` targets and exits)

## Reusable scaffolds

Most crates are bins only. `grids/` also exposes a **library** — a reusable
toolkit for the whole grid-problem family (neighbour generation, BFS/DFS,
flood fill, Dijkstra, backtracking), so practice goes into what varies between
problems rather than into retyping bounds checks.

```
cd grids
cargo test                      # 19 tests
cargo run --bin 001_grid_tour   # every primitive, with output
```

Notes and the pick-your-traversal table: [grid-traversal-scaffold.md](docs/grid-traversal-scaffold.md).

## Linked-list crate: two node types, on purpose

`linked_list/` exposes a **library** (like `grids/`) with two node types
used across its `src/bin/` problems:

- `ListNode` (`Option<Box<ListNode>>`) - LeetCode's own representation,
  used for problems where the list is genuinely tree-shaped: reverse,
  merge, palindrome check, middle-finding, add-two-numbers, remove-nth.
- `RawNode` (raw pointers) - for the three problems where it isn't:
  cycle detection (141, 142) and intersection of two lists (160) both
  need either a cycle or a shared tail, neither of which `Box`'s
  unique-ownership model can represent at all. `src/lib.rs` documents
  the reasoning; each affected problem file repeats the specific "why"
  for its own case.

```
cd linked_list
cargo test                                  # 49 tests across 10 problems
cargo run --bin 004_linked_list_cycle_ii    # any problem, with output
```

## Ad-hoc single-file scripts

For standalone `.rs` files that aren't part of a crate:

```
f=dijkstra; rustc $f.rs -o $f.bin && ./$f.bin
```

## Docs

Further notes live in [`docs/`](docs/):

- [grid-traversal-scaffold.md](docs/grid-traversal-scaffold.md)
- [arrays-hashing-rust-syntax-notes.md](docs/arrays-hashing-rust-syntax-notes.md)
- [recursion-rust-syntax-notes.md](docs/recursion-rust-syntax-notes.md)
- [binary-search-tree-rust-syntax-notes.md](docs/binary-search-tree-rust-syntax-notes.md)
- [binary-search-tree-readme.md](docs/binary-search-tree-readme.md)
- [dynamic-programming-rust-syntax-notes.md](docs/dynamic-programming-rust-syntax-notes.md)
- [dp-problem-solving-framework.md](docs/dp-problem-solving-framework.md)
- [dynamic-programming-climbing-stairs-explained.md](docs/dynamic-programming-climbing-stairs-explained.md)
- [measuring-performance.md](docs/measuring-performance.md)
