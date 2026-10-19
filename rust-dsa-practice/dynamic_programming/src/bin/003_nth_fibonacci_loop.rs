// Problem: compute the nth Fibonacci number, using a plain loop with two
// rolling variables - no recursion, no cache, no table.
//
// This is the O(1)-space optimization flagged at the end of
// 002_nth_fibonacci_tabulation.rs. It computes the exact same values, the
// exact same way conceptually (build up from the base cases), but doesn't
// bother keeping the FULL table around - fib(i) only ever needs fib(i-1)
// and fib(i-2), so once fib(i) is computed, everything before fib(i-1) is
// garbage. Two variables that get overwritten each iteration is enough.
//
// Three ways to solve the same problem, and why they're not all "the same
// thing" despite all being valid DP-adjacent solutions:
//
//   1. MEMOIZATION (001_nth_fibonacci_memoization.rs) - top-down.
//      Recursive: fib(n) calls fib(n-1) and fib(n-2), same shape as the
//      mathematical definition. A HashMap cache avoids recomputation.
//      O(n) time, O(n) space (cache + call stack). You write the
//      recursion the "natural" way and let memoization clean up the
//      redundant calls for you.
//
//   2. TABULATION (002_nth_fibonacci_tabulation.rs) - bottom-up, full
//      table. Iterative: a `for` loop fills a `Vec` from index 0 up to n,
//      in order. O(n) time, O(n) space (the table). No recursion at all -
//      you're explicitly restating the recurrence as "fill this array,
//      left to right."
//
//   3. LOOP / rolling variables (this file) - bottom-up, no table. Also
//      iterative, also a `for` loop, but instead of storing ALL of
//      fib(0)..fib(n) in a Vec, it only keeps the last two values around
//      in named variables (prev, next) and throws the rest away as it
//      goes. O(n) time, O(1) space.
//
// So "tabulation" and "loop" are really the same technique (bottom-up,
// iterative) at two different space budgets - tabulation keeps the whole
// history in case something later needs to look back arbitrarily far;
// this version notices Fibonacci never needs to look back further than 2
// steps, so it throws the history away. The real conceptual split is
// TOP-DOWN (memoization, #1) vs. BOTTOM-UP (tabulation and loop, #2 and
// #3) - whether you start from n and recurse down, or start from the base
// cases and iterate up.
//
// Complexity: O(n) time (same as the other two), O(1) space - the best of
// the three, since Fibonacci's recurrence only ever reaches back 2 steps.
// Not every DP problem can be squeezed to O(1) space like this - it only
// works because the "window" of subproblems each step depends on is
// small and fixed. (004_climbing_stairs.rs has the identical recurrence,
// so the same trick applies there too.)

fn fib(n: u64) -> u64 {
    if n == 0 {
        return 0;
    }

    // prev = fib(i - 2), next = fib(i - 1), sliding forward one step
    // per loop iteration until `next` reaches fib(n).
    let (mut prev, mut next) = (0u64, 1u64);

    for _ in 2..=n {
        let sum = prev + next;
        prev = next;
        next = sum;
    }

    next
}

fn main() {
    for n in 0..15 {
        println!("fib({}) = {}", n, fib(n));
    }
}
