# Measuring wall-clock time and memory, without touching the code

`cargo run`/`cargo build` doesn't report either by itself, but the OS
already tracks both for every process it runs - external tools just read
that out. No `Instant::now()`, no extra dependencies, no code edits.

## Setup: always benchmark a release build

```
cargo build --release
```

`cargo run` (no flags) uses the **debug** profile - unoptimized, with
overflow checks and debug assertions on. It can be 10-100x slower than
release, so timing/memory numbers from a debug build don't reflect real
performance. Build `--release` first, then run the binary directly out of
`target/release/` (not via `cargo run --release`, which adds a small
amount of its own startup overhead on top of the binary).

## macOS (BSD `time`)

```
/usr/bin/time -l ./target/release/<bin-name>
```

(Note the explicit `/usr/bin/time` - the plain `time` you'd normally type
is your shell's *built-in* `time`, which only reports wall/user/sys, not
memory. `-l` on the real `/usr/bin/time` binary adds the memory/resource
section.)

Example, run against `dynamic_programming`'s `001_nth_fibonacci_memoization`:

```
$ /usr/bin/time -l ./target/release/001_nth_fibonacci_memoization
fib(0) = 0
...
fib(14) = 377
        0.38 real         0.00 user         0.00 sys
             1572864  maximum resident set size
                   0  average shared memory size
                   0  average unshared data size
                   0  average unshared stack size
                 263  page reclaims
                   0  page faults
                   0  swaps
                   0  block input operations
                   0  block output operations
                   0  messages sent
                   0  messages received
                   0  signals received
                   0  voluntary context switches
                   6  involuntary context switches
            15361111  instructions retired
             9850283  cycles elapsed
             1032504  peak memory footprint
```

What to actually read:

- **`real`** - wall-clock time (what you asked for). `user`/`sys` split
  that into CPU time spent in your code vs. in the kernel on its behalf -
  for a single-threaded CPU-bound program like these DSA problems, `real`
  and `user` should be close.
- **`maximum resident set size`** - peak physical memory (RAM) the process
  held at any point, in **bytes** on macOS (this line reads as ~1.5 MB,
  mostly binary/runtime overhead - trivial for `fib(0..15)`).
- **`peak memory footprint`** - macOS-specific, a slightly different
  accounting of peak memory that also includes reclaimable pages; close
  to `maximum resident set size` for most purposes.
- Everything else (page faults, context switches, instructions retired)
  is low-level profiling detail, not needed for a basic "how much time and
  memory did this use" check.

For something with actually-visible memory growth - e.g. the naive
exponential `fib` in `recursion/src/bin/008_nth_fibonacci_recursion.rs`
at a large `n`, or the memoized versions once their `HashMap` has many
entries - the `real` time and `maximum resident set size` numbers will
move accordingly, which is the point of running this against different
implementations for comparison.

## Linux (GNU `time`)

Same idea, different flag and units:

```
/usr/bin/time -v ./target/release/<bin-name>
```

Look for `Elapsed (wall clock) time` and `Maximum resident set size
(kbytes)` (Linux reports memory in **KB**, not bytes). GNU `time` isn't
installed on macOS by default; `brew install gnu-time` (or `coreutils`)
gets you `gtime -v ...` there if you want the more detailed GNU-style
output instead of BSD `time -l`.

## Comparing multiple runs / reducing noise

A single `time` run can be noisy (OS scheduling, cold caches, thermal
throttling). For anything where the difference matters (e.g. comparing
naive vs. memoized Fibonacci at the same `n`), run it a handful of times
and eyeball the spread, or use a proper benchmarking tool:

```
brew install hyperfine
hyperfine './target/release/<bin-name>'
```

`hyperfine` runs the binary repeatedly, warms up first, and reports
mean/stddev/min/max wall-clock time - still zero code changes, just a
statistically sturdier version of `time`.
