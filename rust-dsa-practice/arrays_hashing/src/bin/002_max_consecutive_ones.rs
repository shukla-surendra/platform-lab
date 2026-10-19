// Problem: LeetCode 485 - Max Consecutive Ones.
//
// Given a binary array (only 0s and 1s), return the length of the longest
// run of consecutive 1s.
//
// ---------------------------------------------------------------------
// WHY THIS ISN'T REALLY AN "ARRAY" PROBLEM
// ---------------------------------------------------------------------
// The instinct that wastes time here is reaching for indices, windows,
// two pointers - machinery this problem doesn't need. Nothing about a
// run of 1s cares where it started; you only ever need two numbers in
// flight: how long the CURRENT run is, and the longest run seen SO FAR.
// That's it. This is the simplest member of a whole family of "running
// state, one pass, no lookback" problems - the shape to recognize is:
// whenever a streak resets on some condition, and you only care about
// the streak's length, you almost never need to store where it started.
//
// ---------------------------------------------------------------------
// THE ALGORITHM
// ---------------------------------------------------------------------
// Walk the array once. On a 1: extend the current run. On a 0: the run
// breaks, so before resetting it to zero, record it if it's the best
// one seen. Complexity: O(n) time, O(1) space - a single forward pass,
// nothing kept but two counters.

pub fn find_max_consecutive_ones(nums: &[i32]) -> i32 {
    let mut best = 0;
    let mut current = 0;

    for &n in nums {
        if n == 1 {
            current += 1;
            // Updating `best` on every 1 (rather than only when a run
            // ends) means a run that reaches the very end of the array
            // is still counted - there's no closing 0 to trigger the
            // check. This sidesteps the classic off-by-one bug of only
            // checking `best` inside the `== 0` branch.
            best = best.max(current);
        } else {
            current = 0;
        }
    }

    best
}

// =====================================================================
// LeetCode signature adapter
// =====================================================================
pub fn find_max_consecutive_ones_leetcode(nums: Vec<i32>) -> i32 {
    find_max_consecutive_ones(&nums)
}

fn main() {
    let examples: [&[i32]; 3] = [&[1, 1, 0, 1, 1, 1], &[1, 0, 1, 1, 0, 1], &[0, 0, 0]];
    for ex in examples {
        println!("{:?} -> {}", ex, find_max_consecutive_ones(ex));
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn example_1() {
        assert_eq!(find_max_consecutive_ones(&[1, 1, 0, 1, 1, 1]), 3);
    }

    #[test]
    fn example_2() {
        assert_eq!(find_max_consecutive_ones(&[1, 0, 1, 1, 0, 1]), 2);
    }

    #[test]
    fn all_zeros() {
        assert_eq!(find_max_consecutive_ones(&[0, 0, 0]), 0);
    }

    #[test]
    fn all_ones() {
        assert_eq!(find_max_consecutive_ones(&[1, 1, 1, 1]), 4);
    }

    #[test]
    fn empty_array() {
        assert_eq!(find_max_consecutive_ones(&[]), 0);
    }

    // Guards against the "only check on reset" bug: the best run is the
    // LAST one, with no trailing 0 to trigger a check.
    #[test]
    fn best_run_ends_at_array_boundary() {
        assert_eq!(find_max_consecutive_ones(&[0, 1, 0, 1, 1, 1]), 3);
    }
}
