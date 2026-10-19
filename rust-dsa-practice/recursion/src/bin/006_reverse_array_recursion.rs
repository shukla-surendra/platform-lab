// Problem: reverse an array of integers in place, using recursion.
//
// Given an array `arr` and two pointers `start` and `end` marking the
// unreversed portion, swap the elements at `start` and `end`, then recurse
// on the shrinking inner sub-array (start + 1, end - 1). The base case is
// reached when the pointers meet or cross.
//
// Recursive definition:
//   reverse(arr, start, end):
//     if start >= end:            // base case: 0 or 1 elements left
//       return
//     swap(arr[start], arr[end])
//     reverse(arr, start + 1, end - 1)   // recursive case
//
// e.g. reverse([1, 2, 3, 4, 5], 0, 4)
//   swap(1, 5) -> [5, 2, 3, 4, 1], reverse(1, 3)
//   swap(2, 4) -> [5, 4, 3, 2, 1], reverse(2, 2)
//   start >= end -> done
//
// Complexity: two-pointer swapping is optimal on time either way - O(n)
// swaps, each O(1), since start and end close the gap by one from both
// ends every step. Where the two versions differ is space:
//   - Iterative (loop) two-pointer: O(1) extra space. No call stack growth,
//     so it scales to arbitrarily large arrays without risk of a stack
//     overflow. This is the version you'd actually want in production code.
//       fn reverse_iter(arr: &mut [i32]) {
//           let (mut start, mut end) = (0, arr.len().saturating_sub(1));
//           while start < end {
//               arr.swap(start, end);
//               start += 1;
//               end -= 1;
//           }
//       }
//   - Recursive two-pointer (this file): O(n) extra space, one stack frame
//     per call/pair swapped, and it's not tail-call optimized by the Rust
//     compiler, so a large enough array can blow the stack. Written here
//     purely as a recursion exercise, not because it's the better solution.
//
// Optimization: drop `end` as a separate parameter - it's redundant, since
// for a fixed array length n it's always derivable from `start` (call it
// `i` instead) as `end = n - 1 - i`. This still swaps the same pairs, still
// O(n) time / O(n) space recursively, but only one index needs to be
// threaded through the calls instead of two.
//   reverse(arr, i, n):
//     if i >= n - 1 - i:                 // same base case, expressed in i
//       return
//     swap(arr[i], arr[n - 1 - i])
//     reverse(arr, i + 1, n)             // recursive case

fn reverse(arr: &mut [i32], start: usize, end: usize) {
    if start >= end {
        return; // base case: 0 or 1 elements left
    }
    arr.swap(start, end); // swap elements at start and end 
    reverse(arr, start + 1, end - 1); // recursive case
}

fn main() {
    let mut arr = vec![1, 2, 3, 4, 5];
    println!("Current array: {:?}", arr);
    let len = arr.len();
    reverse(&mut arr, 0, len - 1);
    println!("Reversed array: {:?}", arr);
}
