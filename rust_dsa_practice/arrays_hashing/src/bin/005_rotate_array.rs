// Problem: LeetCode 189 - Rotate Array.
//
// Rotate nums RIGHT by k steps, in place. E.g. [1,2,3,4,5,6,7] rotated
// right by 3 becomes [5,6,7,1,2,3,4] - the last k elements move to the
// front, everything else slides right.
//
// ---------------------------------------------------------------------
// WHY THE OBVIOUS APPROACH IS AWKWARD
// ---------------------------------------------------------------------
// "Rotate one step at a time, k times" works but is O(n*k) - each single
// -step rotation is itself an O(n) shift. "Copy into a new array at the
// rotated positions" is O(n) time but needs O(n) EXTRA space, which the
// problem explicitly asks you to avoid ("in place" is right there in
// the statement). The real constraint is doing this in O(n) time with
// O(1) *extra* space - and that combination is what forces something
// cleverer than the direct translation of "rotate."
//
// ---------------------------------------------------------------------
// VERSION 1 - the honest, obviously-correct baseline (uses O(n) space)
// ---------------------------------------------------------------------
// Worth having explicitly, both because "obviously correct first" is
// the right interview order, and because it's the version to reach for
// when the O(1)-space constraint genuinely doesn't matter. Position i
// in the ORIGINAL array lands at position (i + k) % n in the rotated
// one - that's the entire rule; build a new array by placing each
// element there directly.
pub fn rotate_extra_space(nums: &[i32], k: usize) -> Vec<i32> {
    let n = nums.len();
    if n == 0 {
        return Vec::new();
    }
    let k = k % n; // rotating by n is a no-op; k can exceed n
    let mut result = vec![0; n];
    for (i, &val) in nums.iter().enumerate() {
        result[(i + k) % n] = val;
    }
    result
}

// =====================================================================
// VERSION 2 - the in-place trick: three reversals
// =====================================================================
// The move that gets this to O(1) extra space is a neat, memorizable
// identity: reversing the WHOLE array, then reversing each of its two
// natural pieces separately, produces exactly the rotation.
//
//     original:            [1,2,3,4,5,6,7]   k = 3
//     reverse everything:  [7,6,5,4,3,2,1]
//     reverse first k:     [5,6,7,4,3,2,1]      (the "5 6 7" piece un-flips)
//     reverse the rest:    [5,6,7,1,2,3,4]      (the "1 2 3 4" piece un-flips)
//
// Why it works: reversing the whole array puts every element in the
// right RELATIVE final order but with each of the two blocks (what
// should be the new front, and what should be the new back) individually
// backwards. Reversing each block on its own then un-flips exactly that
// block, in place, without disturbing the other one - because
// `reverse()` on a slice only ever touches the range you hand it.
//
// This works because reversal is its own inverse and array reversal
// only touches the given range - a fact worth being able to say
// out loud, not just the three steps by rote.
//
// Complexity: O(n) time (three passes, each O(n), so still O(n) - not
// O(n) three times over in any way that matters), O(1) extra space.
pub fn rotate_in_place(nums: &mut [i32], k: usize) {
    let n = nums.len();
    if n == 0 {
        return;
    }
    let k = k % n;

    nums.reverse();
    nums[..k].reverse();
    nums[k..].reverse();
}

// =====================================================================
// LeetCode signature adapter
// =====================================================================
// LeetCode's actual signature mutates `nums: &mut Vec<i32>` in place and
// returns nothing - this delegates straight to the in-place version.
pub fn rotate_leetcode(nums: &mut Vec<i32>, k: i32) {
    rotate_in_place(nums, k as usize);
}

fn main() {
    let mut a = vec![1, 2, 3, 4, 5, 6, 7];
    println!("extra-space: {:?}", rotate_extra_space(&a, 3));
    rotate_in_place(&mut a, 3);
    println!("in-place:    {a:?}");
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn example_1_both_versions_agree() {
        let nums = [1, 2, 3, 4, 5, 6, 7];
        let mut in_place = nums.to_vec();
        rotate_in_place(&mut in_place, 3);
        assert_eq!(rotate_extra_space(&nums, 3), vec![5, 6, 7, 1, 2, 3, 4]);
        assert_eq!(in_place, vec![5, 6, 7, 1, 2, 3, 4]);
    }

    #[test]
    fn example_2_two_elements() {
        let mut nums = vec![-1, -100, 3, 99];
        rotate_in_place(&mut nums, 2);
        assert_eq!(nums, vec![3, 99, -1, -100]);
    }

    // k larger than the array length must wrap via k % n, not panic or
    // silently do nothing.
    #[test]
    fn k_larger_than_length_wraps() {
        let mut nums = vec![1, 2, 3];
        rotate_in_place(&mut nums, 4); // equivalent to rotating by 1
        assert_eq!(nums, vec![3, 1, 2]);
    }

    #[test]
    fn k_equal_to_length_is_a_no_op() {
        let mut nums = vec![1, 2, 3];
        rotate_in_place(&mut nums, 3);
        assert_eq!(nums, vec![1, 2, 3]);
    }

    #[test]
    fn k_zero_is_a_no_op() {
        let mut nums = vec![1, 2, 3];
        rotate_in_place(&mut nums, 0);
        assert_eq!(nums, vec![1, 2, 3]);
    }

    #[test]
    fn single_element() {
        let mut nums = vec![42];
        rotate_in_place(&mut nums, 5);
        assert_eq!(nums, vec![42]);
    }

    #[test]
    fn empty_array_does_not_panic() {
        let mut nums: Vec<i32> = vec![];
        rotate_in_place(&mut nums, 3);
        assert_eq!(nums, Vec::<i32>::new());
    }
}
