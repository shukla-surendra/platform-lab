// Problem: compute the nth Fibonacci number, using recursion.
//
// This demonstrates MULTIPLE recursion (a.k.a. tree recursion): the
// function calls itself more than once per invocation, branching into two
// subcalls rather than the single self-call seen in 003-007. Each call
// spawns two more, forming a call tree instead of a call chain/stack.
//
// Fibonacci definition:
//   fib(0) = 0
//   fib(1) = 1
//   fib(n) = fib(n - 1) + fib(n - 2)   for n > 1
//
// e.g. fib(5)
//   fib(5) = fib(4) + fib(3)
//          = (fib(3) + fib(2)) + (fib(2) + fib(1))
//          = ... = 5
//
// Complexity: O(2^n) time - naive multiple recursion recomputes the same
// subproblems over and over (e.g. fib(3) is computed twice just for
// fib(5), fib(2) three times, etc.), so the call tree grows exponentially
// with duplicated work. O(n) call-stack depth (the tree's height), so
// space is linear even though time is exponential.
//
// This is NOT the optimal way to compute Fibonacci - it's here purely to
// demonstrate what multiple recursion looks like and why naive tree
// recursion can blow up. Faster alternatives:
//   - Iterative loop, O(n) time / O(1) space: track the last two values.
//   - Memoized recursion (top-down DP), O(n) time / O(n) space: cache
//     fib(k) results the first time each is computed so repeat subcalls
//     are O(1) lookups instead of recomputation.
//   - Matrix exponentiation / closed-form (Binet's formula), O(log n) time.

fn fib(n: u64) -> u64 {
    match n {
        0 => 0,
        1 => 1,
        _ => fib(n - 1) + fib(n - 2),
    }
}

fn main() {
    for n in 0..15 {
        println!("fib({}) = {}", n, fib(n));
    }
}
