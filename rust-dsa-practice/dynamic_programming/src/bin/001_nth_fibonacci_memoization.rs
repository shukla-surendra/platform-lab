// Problem: compute the nth Fibonacci number, using dynamic programming
// (top-down / memoization approach).
//
// What is Dynamic Programming (DP)?
// DP is an optimization technique for recursive problems that have two
// properties:
//   1. OPTIMAL SUBSTRUCTURE - the answer to a problem can be built from
//      the answers to its subproblems (fib(n) is built from fib(n-1) and
//      fib(n-2)).
//   2. OVERLAPPING SUBPROBLEMS - solving it naively recomputes the SAME
//      subproblem many times (fib(3) gets recomputed independently every
//      time it's needed while computing fib(5), fib(6), fib(7), ...).
//      Contrast with something like merge sort, which is also recursive
//      with optimal substructure, but each subproblem is distinct - no
//      repeated work to eliminate, so DP doesn't apply there.
// DP's core idea: solve each distinct subproblem ONCE, store ("cache") the
// result, and reuse it instead of recomputing. Fibonacci is the textbook
// first example because the naive recursive version
// (see ../../recursion/src/bin/008_nth_fibonacci_recursion.rs) makes the
// overlapping-subproblems waste extremely visible - O(2^n) calls to solve
// something with only n distinct subproblems.
//
// Two ways to apply DP - this file covers the first:
//   - TOP-DOWN (memoization): keep the natural recursive structure
//     (fib(n) still calls fib(n-1) and fib(n-2)), but check a cache before
//     doing any work, and populate the cache after. This file.
//   - BOTTOM-UP (tabulation): flip it around - start from the base cases
//     and iteratively build UP to fib(n) in a loop, filling a table (or
//     just two rolling variables) as you go, no recursion/call stack at
//     all. A later problem in this folder.
//
// Recursive definition (same as the naive version):
//   fib(0) = 0
//   fib(1) = 1
//   fib(n) = fib(n - 1) + fib(n - 2)   for n > 1
//
// Memoization changes HOW that gets computed, not the definition itself:
//   1. Before computing fib(n), check the cache - if it's already there,
//      return the cached value immediately (O(1)).
//   2. Otherwise compute it recursively as normal, then store the result
//      in the cache before returning, so every future call for this same
//      n is a cache hit instead of a recomputation.
// This prunes the exponential call tree down to one call per distinct n -
// effectively turning the tree into a DAG, where repeated branches become
// cache hits instead of re-expanding into their own subtrees.
//
// Complexity: O(n) time (n distinct subproblems fib(0)..fib(n), each
// computed exactly once; combining two cached values is O(1)), O(n) space
// (the cache, plus O(n) recursion depth). Down from the naive O(2^n).
//
// Rust-specific plumbing: `fib` needs a cache that PERSISTS across
// recursive calls and can be both read and written. Rust has no implicit
// shared mutable state, default arguments, or static local variables the
// way some languages do, so the cache is threaded through explicitly as a
// `&mut HashMap<u64, u64>` parameter - the same accumulator-passing style
// used for `sum` in ../../recursion/src/bin/004_parameterized_recursion_sum.rs,
// just carrying a cache instead of a running total.

use std::collections::HashMap;

fn fib(n: u64, memo: &mut HashMap<u64, u64>) -> u64 {
    // Base cases - nothing to look up yet.
    if n == 0 {
        return 0;
    }
    if n == 1 {
        return 1;
    }

    // Cache hit: this subproblem was already solved on an earlier branch
    // of the recursion - reuse it instead of recomputing the whole subtree.
    if let Some(&cached) = memo.get(&n) {
        return cached;
    }

    // Cache miss: compute it the normal recursive way...
    let result = fib(n - 1, memo) + fib(n - 2, memo);

    // ...then remember it before returning, so the next caller that needs
    // fib(n) gets an O(1) lookup instead of redoing this work.
    memo.insert(n, result);

    result
}

fn main() {
    let mut memo: HashMap<u64, u64> = HashMap::new();
    for n in 0..15 {
        println!("fib({}) = {}", n, fib(n, &mut memo));
    }
}
