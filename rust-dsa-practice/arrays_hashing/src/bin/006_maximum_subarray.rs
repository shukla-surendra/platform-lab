// Problem: LeetCode 53 - Maximum Subarray.
//
// Given an array of integers (possibly negative), find the CONTIGUOUS
// subarray with the largest sum, and return that sum. The subarray must
// be non-empty.
//
// ---------------------------------------------------------------------
// WHY THE OBVIOUS APPROACH IS AWKWARD
// ---------------------------------------------------------------------
// "Try every (start, end) pair, sum each, keep the best" is O(n^2) (or
// O(n^3) if you re-sum from scratch instead of extending a running
// sum). The n^2 version is doing real wasted work: for a fixed start,
// once the running sum has gone deeply negative, continuing to extend
// it from THAT start can never be part of the eventual best answer
// beginning anywhere at or after where it went negative - a fresh start
// from the next index is always at least as good. The n^2 loop has no
// way to notice and act on that; it just keeps trying every start
// regardless.
//
// ---------------------------------------------------------------------
// THE INSIGHT: A NEGATIVE RUNNING SUM IS DEAD WEIGHT
// ---------------------------------------------------------------------
// This is Kadane's algorithm, and the one-sentence justification is
// worth being able to say cold: if the best subarray ENDING at index i
// has a sum that's negative, then dropping it and starting fresh at
// index i+1 is strictly better for every subarray beginning after i -
// carrying a negative prefix forward can only ever subtract from
// whatever comes next, never add. So at each position you only need to
// ask one question: "is it better to extend the current run, or
// abandon it and start over here?" - and the answer is simply whichever
// of (current_run + nums[i]) or (nums[i] alone) is bigger.
//
//     nums:        [-2, 1, -3, 4, -1, 2, 1, -5, 4]
//     running sum:  -2  1  -2  4   3  5  6   1  5
//                        ^-- reset: -2 + 1 = -1 is worse than starting fresh at 1
//                                        ^-- best subarray found here: [4,-1,2,1] = 6
//
// ---------------------------------------------------------------------
// THE ALGORITHM
// ---------------------------------------------------------------------
// Track two numbers: `current` (the best sum of a subarray ENDING right
// here) and `best` (the best sum seen anywhere so far). At each step,
// `current` either extends the previous run or restarts at the current
// element, whichever is larger; `best` is updated against the new
// `current` every step, not just on a reset, so the best subarray
// reaching all the way to the end is still captured.
//
// Complexity: O(n) time, O(1) space - one pass, two running numbers.
// (A divide-and-conquer solution also exists, O(n log n) - split the
// array in half, recursively solve each half, and separately handle the
// case where the best subarray straddles the midpoint. It's worth
// knowing it exists, since "can you think of a non-linear approach too"
// is a fair follow-up, but Kadane's is the answer to lead with here.)

pub fn max_sub_array(nums: &[i32]) -> i32 {
    // The problem guarantees nums is non-empty; unwrap is safe as a
    // result, but written this way to fail loudly rather than silently
    // if that guarantee is ever violated by a caller.
    let mut current = nums[0];
    let mut best = nums[0];

    for &n in &nums[1..] {
        current = n.max(current + n);
        best = best.max(current);
    }

    best
}

// =====================================================================
// LeetCode signature adapter
// =====================================================================
pub fn max_sub_array_leetcode(nums: Vec<i32>) -> i32 {
    max_sub_array(&nums)
}

fn main() {
    let examples: [&[i32]; 3] = [&[-2, 1, -3, 4, -1, 2, 1, -5, 4], &[1], &[5, 4, -1, 7, 8]];
    for ex in examples {
        println!("{:?} -> {}", ex, max_sub_array(ex));
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn example_1() {
        assert_eq!(max_sub_array(&[-2, 1, -3, 4, -1, 2, 1, -5, 4]), 6);
    }

    #[test]
    fn single_element() {
        assert_eq!(max_sub_array(&[1]), 1);
    }

    #[test]
    fn all_positive_take_everything() {
        assert_eq!(max_sub_array(&[5, 4, -1, 7, 8]), 23);
    }

    // The subarray must be non-empty, so an all-negative array must
    // still return its LARGEST (least negative) single element, not 0.
    // A buggy version that seeds `best` at 0 fails exactly this case.
    #[test]
    fn all_negative_returns_least_negative_single_element() {
        assert_eq!(max_sub_array(&[-3, -1, -2]), -1);
    }

    #[test]
    fn best_subarray_reaches_the_end_of_the_array() {
        // Best run is [3, 4] at the very end - with no trailing element
        // to trigger a "reset" comparison, `best` must still have been
        // updated on the FINAL step, not only when a run breaks.
        assert_eq!(max_sub_array(&[-5, -1, 3, 4]), 7);
    }
}
