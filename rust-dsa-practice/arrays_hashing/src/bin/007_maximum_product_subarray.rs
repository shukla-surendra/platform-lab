// Problem: LeetCode 152 - Maximum Product Subarray.
//
// Given an array of integers, find the CONTIGUOUS subarray with the
// largest PRODUCT, and return that product.
//
// ---------------------------------------------------------------------
// WHY KADANE'S ALGORITHM, UNCHANGED, DOESN'T WORK HERE
// ---------------------------------------------------------------------
// This looks like a copy-paste of Maximum Subarray (53, in this same
// crate) with `+` swapped for `*` - and that swap is exactly the trap.
// Addition and multiplication behave very differently around negative
// numbers: for sums, "the best run ending here" only ever needs the
// single running MAXIMUM, because adding a negative number always makes
// things worse in a way that stays worse. For PRODUCTS, a negative
// number doesn't just shrink a running value - it can FLIP its sign.
// A large negative running product, multiplied by one more negative
// number, can suddenly become the largest positive product in the whole
// array. Tracking only "best product ending here" throws away exactly
// the information (a large-magnitude NEGATIVE running product) that a
// later negative number could turn into the answer.
//
//     nums:     [2, 3, -2, 4]
//     if you only track the running max product:
//       i=0: 2      i=1: 6      i=2: max(6*-2, -2) = -2 (!)   i=3: max(-2*4, 4) = 4
//     but the TRUE best subarray is [2,3] = 6 - the moment you multiplied
//     by -2 and kept only the max (-2), you threw away 6, which was the
//     answer, and had no way to recover it once you moved on.
//
// ---------------------------------------------------------------------
// THE FIX: TRACK BOTH THE RUNNING MAX AND THE RUNNING MIN
// ---------------------------------------------------------------------
// Since a negative number can turn the SMALLEST (most negative) running
// product into the largest one, carry both extremes forward at every
// step, not just the max. At each element, the new running max is the
// best of three candidates: the element alone, (old max * element), or
// (old min * element) - and symmetrically for the new running min. The
// three-way max/min (rather than assuming the max always comes from the
// old max) is what correctly captures a sign flip.
//
//     nums:      [2,   3,        -2,           4]
//     run_max:    2    6    max(-2,-12,-6)=-2    max(4,-8,-48)=4
//     run_min:    2    3    min(-2,-12,-6)=-12    min(4,-8,-48)=-48
//     best:       2    6    6                      6
//
// The best answer stays 6 (from [2,3]) - the trailing -2 and 4 never
// produce a larger product than that, but notice run_min plunges to
// -48 by the end. Change this array to [2,3,-2,4,-1] and that carried
// run_min of -48 is exactly what the next negative element would
// multiply against to produce a new candidate for run_max - which is
// the entire reason run_min has to be carried forward at every step,
// not just consulted when a negative number is seen.
//
// Complexity: O(n) time, O(1) space - one pass, two running values
// instead of Kadane's one.

pub fn max_product(nums: &[i32]) -> i32 {
    let mut run_max = nums[0];
    let mut run_min = nums[0];
    let mut best = nums[0];

    for &n in &nums[1..] {
        // Compute both candidates from the OLD run_max/run_min before
        // overwriting either - otherwise run_min's update would already
        // be using the just-updated run_max, corrupting the three-way
        // comparison.
        let candidates = [n, run_max * n, run_min * n];
        run_max = candidates.into_iter().max().unwrap();
        run_min = candidates.into_iter().min().unwrap();

        best = best.max(run_max);
    }

    best
}

// =====================================================================
// LeetCode signature adapter
// =====================================================================
pub fn max_product_leetcode(nums: Vec<i32>) -> i32 {
    max_product(&nums)
}

fn main() {
    let examples: [&[i32]; 3] = [&[2, 3, -2, 4], &[-2, 0, -1], &[-2, 3, -4]];
    for ex in examples {
        println!("{:?} -> {}", ex, max_product(ex));
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn example_1() {
        assert_eq!(max_product(&[2, 3, -2, 4]), 6); // [2,3]
    }

    // A zero breaks any run through it, exactly like Max Consecutive
    // Ones's 0 does - but here the "reset value" after a zero is 0
    // itself (any product involving it collapses to 0), which the
    // three-way max/min over {n, max*n, min*n} handles automatically
    // without a special case: run_max*0 = 0, run_min*0 = 0, and n = 0.
    #[test]
    fn zero_resets_the_running_product() {
        assert_eq!(max_product(&[-2, 0, -1]), 0);
    }

    // The case that actually distinguishes this problem from Kadane's:
    // two negatives flanking a positive multiply back to a large
    // positive, but only if the running MINIMUM was tracked through the
    // first negative rather than discarded.
    #[test]
    fn two_negatives_flip_to_a_larger_positive() {
        assert_eq!(max_product(&[-2, 3, -4]), 24); // the whole array
    }

    #[test]
    fn single_negative_element() {
        assert_eq!(max_product(&[-3]), -3);
    }

    #[test]
    fn all_positive() {
        assert_eq!(max_product(&[1, 2, 3, 4]), 24);
    }
}
