// Problem: print all subsequences of an array of integers whose elements
// sum to exactly k, using recursion.
//
// This builds directly on 010_print_subsequences.rs's include/exclude
// recursion - same 2^n call tree shape, same two branches per element -
// but now each branch also tracks a running sum, and only the leaves
// where that running sum equals k get printed. Everything else in the
// tree is explored and discarded.
//
// Recursive definition (extend `current` and `running_sum` as we go):
//   subsequences_with_sum(arr, i, k, current, running_sum):
//     if i == len(arr):                                  // base case
//       if running_sum == k:
//         print(current)
//       return
//     current.push(arr[i])
//     subsequences_with_sum(arr, i + 1, k, current, running_sum + arr[i])  // include arr[i]
//     current.pop()                                        // backtrack
//     subsequences_with_sum(arr, i + 1, k, current, running_sum)          // exclude arr[i]
//
// e.g. subsequences_with_sum([1, 2, 3], 0, 3, [], 0)
//   include 1 -> running_sum=1
//     include 2 -> running_sum=3
//       include 3 -> running_sum=6, leaf: 6 != 3, skip
//       exclude 3 -> running_sum=3, leaf: 3 == 3, print [1, 2]
//     exclude 2 -> running_sum=1
//       include 3 -> running_sum=4, leaf: skip
//       exclude 3 -> running_sum=1, leaf: skip
//   exclude 1 -> running_sum=0
//     include 2 -> running_sum=2
//       include 3 -> running_sum=5, leaf: skip
//       exclude 3 -> running_sum=2, leaf: skip
//     exclude 2 -> running_sum=0
//       include 3 -> running_sum=3, leaf: print [3]
//       exclude 3 -> running_sum=0, leaf: skip
//   result: [1, 2] and [3]
//
// Complexity: O(2^n) calls (still visits every subsequence, same as
// 010 - the sum check only decides what to PRINT at each leaf, it doesn't
// prune any branches here). O(n) recursion depth, O(n) space for
// `current` at any point in time.
//
// Optimization note (left as-is here, worth exploring separately): unlike
// 010, this problem CAN be pruned - if all remaining array elements are
// known non-negative, and running_sum already exceeds k, every deeper
// branch can only add more (never subtract), so that whole subtree can be
// skipped early instead of still being walked down to a leaf. That's a
// straightforward variant of this same function once you're comfortable
// with the base version.

fn subsequences_with_sum(arr: &[i32], i: usize, k: i32, current: &mut Vec<i32>, running_sum: i32) {
    if i == arr.len() {
        if running_sum == k {
            println!("{:#?}", current);
        }
        return;
    }

    // branch 1: include arr[i]
    current.push(arr[i]);
    
    subsequences_with_sum(arr, i + 1, k, current, running_sum + arr[i]);
    current.pop(); // backtrack

    // branch 2: exclude arr[i]
    subsequences_with_sum(arr, i + 1, k, current, running_sum);
}

fn main() {
    let arr = [1, 2, 3];
    let k = 3;
    let mut current: Vec<i32> = Vec::new();
    subsequences_with_sum(&arr, 0, k, &mut current, 0);
}
