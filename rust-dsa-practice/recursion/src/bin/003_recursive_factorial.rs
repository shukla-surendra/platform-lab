// Problem: compute the factorial of a non-negative integer n, using recursion.
//
// Definition: factorial of n (written n!) is the product of all positive
// integers from 1 to n:
//   n! = n * (n-1) * (n-2) * ... * 2 * 1
// Base case: 0! = 1 (empty product).
//
// Recursive definition:
//   fact(0) = 1
//   fact(n) = n * fact(n - 1)   for n > 0
//
// e.g. fact(5) = 5 * 4 * 3 * 2 * 1 = 120

fn factorial(n: u32) -> u32 {
    if n == 0 {
        1 // base case //last line without semicolon is returned implicitly
    } else {
        n * factorial(n - 1) // recursive case //last line without semicolon is returned implicitly
    }
}

fn main() {
    let n = 5;
    let result = factorial(n);
    println!("Factorial of {} is {}", n, result);
}

// WARNING: overflow risk.
// factorial(n) grows faster than exponentially, so it blows past u32 fast:
//   12! = 479,001,600   (fits in u32)
//   13! = 6,227,020,800 (overflows u32::MAX = 4,294,967,295)
// Debug build: panics with "attempt to multiply with overflow".
// Release build: silently wraps (two's-complement), giving a wrong answer.
// Fix: use u64 (fits up to 20!), u128 (fits up to 34!), or a bignum crate
// (e.g. num-bigint) for larger n.