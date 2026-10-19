// Problem: compute the sum of the first n natural numbers, using
// return-based (functional) recursion.
//
// Contrast with 004_parameterized_recursion_sum.rs, which carries the
// running total DOWN as an accumulator parameter. Here, instead, each call
// returns a value and the CALLER combines it with its own contribution
// after the recursive call returns - the same style as factorial in
// 003_recursive_factorial.rs.
//
// Sum definition: sum(n) = n + (n-1) + ... + 1 + 0
//
// Recursive definition (return style):
//   sum(0) = 0
//   sum(n) = n + sum(n - 1)   for n > 0
//
// e.g. sum(5) = 5 + sum(4) = 5 + (4 + sum(3)) = ... = 5+4+3+2+1+0 = 15
//
// Sanity check (closed form): sum(n) = n * (n + 1) / 2

fn sum(n: u32) -> u32 {
    if n == 0 {
        0 // base case //last line without semicolon is returned implicitly
    } else {
        n + sum(n - 1) // recursive case //last line without semicolon is returned implicitly
    }
}

fn main() {
    let n = 35;
    let result = sum(n);
    println!("Sum of first {} natural numbers is {}", n, result);
}