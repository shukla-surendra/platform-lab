// Problem: compute the nth Fibonacci number, using dynamic programming -
// bottom-up (tabulation) this time, instead of the top-down memoization
// in 001_nth_fibonacci_memoization.rs.
//
// Top-down vs. bottom-up, both are DP, same idea (solve each distinct
// subproblem once, reuse the result), different direction:
//   - TOP-DOWN (001, memoization): start from fib(n), the thing you
//     actually want, and recurse DOWN toward the base cases, caching
//     results the first time each is computed along the way. Uses the
//     call stack; needs a HashMap because subproblems are solved in a
//     scattered, on-demand order (whatever the recursion happens to hit).
//   - BOTTOM-UP (this file, tabulation): start from the base cases,
//     fib(0) and fib(1), and iteratively build UP to fib(n) in a loop.
//     No recursion, no call stack growth. Subproblems are solved in
//     strict order (0, 1, 2, ..., n), so a plain array/Vec works as the
//     "table" (that's where "tabulation" gets its name) instead of a
//     HashMap - table[i] is always filled before table[i+1] needs it.
//
// Recursive definition, same as always:
//   fib(0) = 0
//   fib(1) = 1
//   fib(n) = fib(n - 1) + fib(n - 2)   for n > 1
//
// Tabulation just evaluates that definition in the opposite direction:
//   table[0] = 0
//   table[1] = 1
//   table[i] = table[i - 1] + table[i - 2]   for i from 2 up to n, in a loop
//   answer = table[n]
//
// e.g. fib(5): table = [0, 1, _, _, _, _]
//   i=2: table[2] = table[1] + table[0] = 1 + 0 = 1  -> [0,1,1,_,_,_]
//   i=3: table[3] = table[2] + table[1] = 1 + 1 = 2  -> [0,1,1,2,_,_]
//   i=4: table[4] = table[3] + table[2] = 2 + 1 = 3  -> [0,1,1,2,3,_]
//   i=5: table[5] = table[4] + table[3] = 3 + 2 = 5  -> [0,1,1,2,3,5]
//   answer = table[5] = 5
//
// Complexity: O(n) time (one loop iteration per value from 2 to n, O(1)
// work each), O(n) space for the table. Same time complexity as the
// memoized version, but:
//   - No recursion/call-stack depth at all - can't stack-overflow no
//     matter how large n is, unlike 001's recursive version.
//   - No hashing overhead - direct array indexing instead of HashMap
//     lookups/inserts.
//   This is generally the preferred DP style when the subproblems have a
//   natural, known-ahead-of-time order to solve them in (as Fibonacci
//   does: you always need everything from 0 up to n).
//
// Further optimization: the loop only ever looks at the last two table
// entries, `table[i-1]` and `table[i-2]` - the rest of the table is dead
// weight. Replacing the full Vec with two rolling variables gets this
// down to O(1) space instead of O(n), while keeping O(n) time. That
// version is deliberately kept as a SEPARATE file,
// 003_nth_fibonacci_loop.rs, rather than replacing this one - see that
// file for why "tabulation" and "just loop with two variables" are worth
// distinguishing even though both are iterative.

fn fib(n: u64) -> u64 {
    if n == 0 {
        return 0; // table[1] would be out of bounds for a size-1 table
    }

    // The table: table[i] will hold fib(i), for every i from 0 to n.
    let mut table = vec![0u64; (n + 1) as usize];
    table[0] = 0; // base case
    table[1] = 1; // base case

    // Fill the table in order, smallest subproblem to largest. Each cell
    // only depends on the two before it, both already filled by the time
    // we get here.
    for i in 2..=(n as usize) {
        table[i] = table[i - 1] + table[i - 2];
    }

    table[n as usize]
}

fn main() {
    for n in 0..15 {
        println!("fib({}) = {}", n, fib(n));
    }
}
