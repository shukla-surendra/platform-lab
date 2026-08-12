// Problem: LeetCode 238 - Product of Array Except Self.
//
// Given nums, return an array `answer` where answer[i] is the product
// of every element EXCEPT nums[i]. Must run in O(n), and - the actual
// constraint that makes this problem interesting - WITHOUT using
// division, in O(1) *extra* space (the output array itself doesn't
// count against that).
//
// ---------------------------------------------------------------------
// WHY THE OBVIOUS APPROACH IS AWKWARD
// ---------------------------------------------------------------------
// "Multiply everything, then divide by nums[i] for each i" is O(n) and
// looks tempting - and it's disallowed for a real reason, not an
// arbitrary rule: it breaks the instant any element is 0 (division by
// zero), and it's ALSO wrong-shaped for more than one zero (every
// answer would need to be 0 except at the zero's own index, which the
// naive division formula doesn't produce correctly even if you special
// case one zero). The clean solution has to avoid division entirely,
// which forces a genuinely different idea.
//
// ---------------------------------------------------------------------
// THE MENTAL MODEL: answer[i] = (everything to its LEFT) x (everything
// to its RIGHT)
// ---------------------------------------------------------------------
// "Product of everything except position i" is exactly "product of the
// prefix before i" times "product of the suffix after i". If you had
// two arrays - prefix[i] = product of nums[0..i], suffix[i] = product
// of nums[i+1..] - the answer is just prefix[i] * suffix[i] for every
// i. That's the whole idea; everything else is just building those two
// arrays cheaply and then not actually allocating both of them.
//
//     nums:     [1,   2,   3,   4]
//     prefix:   [1,   1,   2,   6]     prefix[i] = product of nums[0..i]
//     suffix:   [24,  12,  4,   1]     suffix[i] = product of nums[i+1..]
//     answer:   [24,  12,  8,   6]     answer[i] = prefix[i] * suffix[i]
//
// ---------------------------------------------------------------------
// COLLAPSING TWO ARRAYS INTO ONE, IN PLACE
// ---------------------------------------------------------------------
// Build `prefix` directly into the output array on a left-to-right
// pass. Then, instead of allocating a separate `suffix` array, walk
// right-to-left carrying the running suffix product in a single
// variable, multiplying it into the output in place as you go. The
// output array is not counted as "extra" space per the problem's own
// rules, so this genuinely reaches O(1) extra space, O(n) time, no
// division.

pub fn product_except_self(nums: &[i32]) -> Vec<i32> {
    let n = nums.len();
    let mut answer = vec![1; n];

    // Pass 1: answer[i] becomes the product of everything BEFORE i.
    let mut prefix = 1;
    for i in 0..n {
        answer[i] = prefix;
        prefix *= nums[i];
    }

    // Pass 2: multiply in the product of everything AFTER i, carried
    // in `suffix` rather than stored in its own array.
    let mut suffix = 1;
    for i in (0..n).rev() {
        answer[i] *= suffix;
        suffix *= nums[i];
    }

    answer
}

// =====================================================================
// LeetCode signature adapter
// =====================================================================
pub fn product_except_self_leetcode(nums: Vec<i32>) -> Vec<i32> {
    product_except_self(&nums)
}

fn main() {
    let examples: [&[i32]; 2] = [&[1, 2, 3, 4], &[-1, 1, 0, -3, 3]];
    for ex in examples {
        println!("{:?} -> {:?}", ex, product_except_self(ex));
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn example_1() {
        assert_eq!(product_except_self(&[1, 2, 3, 4]), vec![24, 12, 8, 6]);
    }

    // The case naive division actively gets wrong: a single zero makes
    // every OTHER answer 0 (since the product always includes that
    // zero), while the zero's own position gets the product of
    // everything else.
    #[test]
    fn single_zero() {
        assert_eq!(
            product_except_self(&[-1, 1, 0, -3, 3]),
            vec![0, 0, 9, 0, 0]
        );
    }

    // Two zeros: EVERY position now includes at least one zero in its
    // "except self" product, so the whole answer is all zeros. Naive
    // division has no sane way to produce this at all.
    #[test]
    fn two_zeros_everything_is_zero() {
        assert_eq!(product_except_self(&[0, 4, 0]), vec![0, 0, 0]);
    }

    #[test]
    fn two_elements() {
        assert_eq!(product_except_self(&[3, 5]), vec![5, 3]);
    }

    #[test]
    fn negative_numbers() {
        assert_eq!(product_except_self(&[-1, -2, -3]), vec![6, 3, 2]);
    }
}
