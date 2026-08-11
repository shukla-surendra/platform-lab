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
