// Problem: you're climbing a staircase with n steps. Each move you can
// climb either 1 or 2 steps. In how many distinct ways can you reach the
// top (step n)?
//
// e.g. n = 3, the distinct ways are:
//   1+1+1, 1+2, 2+1
// -> 3 ways.
//
// Why this is DP: to reach step n, your LAST move was either a 1-step
// (meaning you were previously at step n-1) or a 2-step (meaning you were
// previously at step n-2) - there's no other way to land exactly on step
// n. So the number of ways to reach step n is the number of ways to reach
// step n-1, plus the number of ways to reach step n-2:
//
//   ways(n) = ways(n - 1) + ways(n - 2)
//
// That's the Fibonacci recurrence, verbatim - this problem IS Fibonacci,
// just arrived at through a different story (counting paths instead of
// "sum of the previous two numbers"). It's a common first "aha" in DP:
// very different-sounding problems can reduce to the exact same
// recurrence once you find the right way to define the subproblem
// (here, "ways to reach step i" as the thing to tabulate).
//
// Base cases:
//   ways(0) = 1   // already at the top with zero steps taken - one way: do nothing
//   ways(1) = 1   // only one path to a single step: a single 1-step move
// (Compare to actual Fibonacci, where fib(0) = 0 - the base cases differ
// even though the recurrence is identical, so double check base cases
// whenever you spot a "this is just Fibonacci" reduction; don't assume
// they carry over.)
//
// This file: plain brute-force recursion, straight off the recurrence
// above - no memo, no table. Same "write the recursion first, optimize
// after" step used for Fibonacci (naive version in
// ../../recursion/src/bin/008_nth_fibonacci_recursion.rs, before
// 001_nth_fibonacci_memoization.rs and 002_nth_fibonacci_tabulation.rs
// optimize it).
//
// e.g. ways(4) - each call branches into the two allowed moves (1-step,
// 2-step), same shape as Fibonacci's call tree:
//   ways(4) = ways(3) + ways(2)
//           = (ways(2) + ways(1)) + (ways(1) + ways(0))
//           = ((ways(1) + ways(0)) + 1) + (1 + 1)
//           = ((1 + 1) + 1) + (1 + 1) = 5
// Notice ways(2) and ways(1) each get recomputed from scratch on
// different branches - that repeated work is exactly what memoization/
// tabulation eliminate, once this version is correct.
//
// Complexity: O(2^n) time - naive tree recursion, identical shape and
// identical waste to 008_nth_fibonacci_recursion.rs's naive fib (every
// distinct ways(k) gets recomputed on every branch that needs it).
// O(n) recursion depth. This is the "brute force" baseline to compare
// the DP-optimized versions against, not the version you'd want in
// production for large n.

fn ways(n: u64) -> u64 {
    if n == 0 || n == 1 {
        return 1; // base cases
    }
    ways(n - 1) + ways(n - 2) // recursive case
}

fn main() {
    for n in 0..15 {
        println!("ways({}) = {}", n, ways(n));
    }
}
