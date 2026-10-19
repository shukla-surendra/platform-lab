// Problem: compute the sum of the first n natural numbers, using
// parameterized recursion (a.k.a. accumulator-passing recursion).
//
// Sum definition: sum(n) = n + (n-1) + ... + 1 + 0
//
// Two styles of recursion, contrast with factorial (see 003_recursive_factorial.rs):
//   - Functional recursion: combine the result AFTER the recursive call
//     returns, on the way back up the call stack.
//       fact(n) = n * fact(n - 1)
//   - Parameterized recursion: carry the running result DOWN as an extra
//     parameter (the accumulator), updating it BEFORE each recursive call.
//     The base case just returns the accumulator - no work happens on the
//     way back up.
//
// Recursive definition (accumulator style):
//   sum(n, acc) = acc                  when n == 0
//   sum(n, acc) = sum(n - 1, acc + n)  when n > 0
// Initial call: sum(n, 0)
//
// e.g. sum(5, 0) -> sum(4, 5) -> sum(3, 9) -> sum(2, 12) -> sum(1, 14) -> sum(0, 15) -> 15
//
// Sanity check (closed form): sum(n) = n * (n + 1) / 2

fn sum(n: u32, acc: &mut u32) {
    if n == 0 {
        // base case: do nothing, just return
    } else {
        *acc += n; // update the accumulator
        sum(n - 1, acc); // recursive call with updated accumulator
    }
}

fn main(){
    let n = 5;
    let mut result: u32 = 0;
    sum(n, & mut result);
    println!("Sum of first {} natural numbers is {}", n, result);
}