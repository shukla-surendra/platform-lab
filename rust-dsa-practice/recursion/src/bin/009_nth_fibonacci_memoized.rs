// Problem: compute the nth Fibonacci number, using recursion + memoization
// (top-down dynamic programming).
//
// See 008_nth_fibonacci_recursion.rs for the naive version and why it's
// O(2^n): the same fib(k) gets recomputed from scratch every time it's
// needed, and it's needed by many different branches of the call tree.
//
// Memoization fixes this by remembering ("memo" = memorandum, a note to
// remember) results we've already computed, in a cache indexed by n. The
// recursive structure stays identical - we still branch into
// fib(n-1) + fib(n-2) - but each distinct n is only ever computed once:
//   1. Before doing any work, check the cache: if fib(n) is already in
//      there, return the cached value immediately (O(1) lookup).
//   2. Otherwise compute it recursively as before, then STORE the result
//      in the cache before returning, so future calls for this same n
//      short-circuit via step 1.
//
// This turns the exponential call tree into what's effectively a DAG - the
// duplicate branches get pruned to a cache hit instead of re-expanding
// into their own subtrees.
//
// Complexity: O(n) time (each of the n distinct subproblems fib(0)..fib(n)
// is computed exactly once, and combining is O(1)), O(n) space (the cache,
// plus O(n) call-stack depth as before). This is the same complexity as
// the plain iterative loop mentioned in 008 - memoization is the recursive
// way to get there.
//
// Rust-specific plumbing: `fib` needs to be able to both READ and WRITE a
// cache that persists across recursive calls. Since Rust doesn't have
// implicit shared mutable state / default arguments / static local
// variables the way some languages do, the cache has to be threaded
// through explicitly. Two common ways to do that:
//   (a) Pass a `&mut HashMap<u64, u64>` into the function as an extra
//       parameter (what this file does) - simple, explicit, no hidden
//       state, mirrors the accumulator-passing style already used in
//       004_parameterized_recursion_sum.rs.
//   (b) Wrap the cache in a `RefCell<HashMap<..>>` captured by a closure,
//       or store it in a struct with a method - lets the public function
//       signature stay `fn fib(n: u64) -> u64` with no cache parameter
//       visible to callers, at the cost of a bit more ceremony.

use std::collections::HashMap;

fn fib(n: u64, memo: &mut HashMap<u64, u64>) -> u64 {
    // Base cases, same as the naive version - nothing to look up yet.
    if n == 0 {
        return 0;
    }
    if n == 1 {
        return 1;
    }

    // Cache hit: we've solved fib(n) on some earlier branch of the
    // recursion - reuse it instead of recomputing the whole subtree.
    if let Some(&cached) = memo.get(&n) {
        return cached;
    }

    // Cache miss: compute it the normal recursive way...
    let result = fib(n - 1, memo) + fib(n - 2, memo);

    // ...then remember it before returning, so the NEXT time any caller
    // asks for fib(n) (e.g. the sibling branch that needs fib(n) while
    // computing fib(n + 2) = fib(n + 1) + fib(n)), it's an O(1) lookup
    // instead of re-doing this whole computation.
    memo.insert(n, result);

    result
}

fn main() {
    let mut memo: HashMap<u64, u64> = HashMap::new();
    for n in 0..15 {
        println!("fib({}) = {}", n, fib(n, &mut memo));
    }
}
