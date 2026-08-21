/*
 * LeetCode 26: Remove Duplicates from Sorted Array
 * Difficulty: Easy
 * Technique: Two Pointers
 *
 * PROBLEM STATEMENT:
 * ==================
 * Given an integer array nums sorted in non-decreasing order,
 * remove the duplicates in-place such that each unique element appears only once.
 * The relative order of the elements should be kept the same.
 *
 * Then return the number of unique elements in nums.
 *
 * Do not allocate extra space for another array.
 * You must do this by modifying the input array in-place with O(1) extra memory.
 *
 * Example 1:
 *   Input: nums = [1,1,2]
 *   Output: 2, nums = [1,2,_]
 *   Explanation: Your function should return k = 2, with first 2 elements
 *   of nums being 1 and 2 respectively. It does not matter what you leave
 *   beyond the returned k.
 *
 * Example 2:
 *   Input: nums = [0,0,1,1,1,2,2,3,3,4]
 *   Output: 5, nums = [0,1,2,3,4,_,_,_,_,_]
 *
 * Constraints:
 *   - 1 <= nums.length <= 3 * 10^4
 *   - -100 <= nums[i] <= 100
 *   - nums is sorted in non-decreasing order.
 *
 * ============================================================================
 * APPROACH HINTS:
 * ============================================================================
 *
 * INSIGHT:
 * Since array is sorted, duplicates are adjacent!
 * Use two pointers:
 * - One to read (iterate through array)
 * - One to write (position to place next unique element)
 *
 * STRATEGY:
 * 1. slow = 0 (position to place next unique)
 * 2. fast = 1 (pointer to read)
 * 3. While fast hasn't reached end:
 *    - If nums[fast] != nums[slow]:
 *      - slow += 1
 *      - nums[slow] = nums[fast]
 *    - fast += 1
 * 4. Return slow + 1 (count of unique elements)
 *
 * TIME COMPLEXITY: O(n)
 * SPACE COMPLEXITY: O(1)
 *
 * ============================================================================
 */

/// Remove duplicates in-place from sorted array
/// Returns the number of unique elements
fn removeDuplicates(nums: &mut Vec<i32>) -> i32 {
    // TODO: Implement your solution here!
    //
    // Hints:
    // 1. Use two pointers: slow (write) and fast (read)
    // 2. Start slow at 0, fast at 1
    // 3. When nums[fast] != nums[slow], advance slow and copy value
    // 4. Always advance fast
    // 5. Return slow + 1 as count

    1
}

// ============================================================================
// TEST CASES
// ============================================================================

fn main() {
    println!("=== Remove Duplicates from Sorted Array ===\n");

    // Test Case 1: Basic case
    println!("Test 1: [1,1,2]");
    let mut nums1 = vec![1, 1, 2];
    let k1 = removeDuplicates(&mut nums1);
    println!("Output: k = {}", k1);
    println!("Array after: {:?}", &nums1[0..k1 as usize]);
    println!("Expected: k = 2, array = [1, 2]");
    assert_eq!(k1, 2);
    assert_eq!(&nums1[0..2], &[1, 2]);
    println!("✓ Test 1 passed\n");

    // Test Case 2: Multiple duplicates
    println!("Test 2: [0,0,1,1,1,2,2,3,3,4]");
    let mut nums2 = vec![0, 0, 1, 1, 1, 2, 2, 3, 3, 4];
    let k2 = removeDuplicates(&mut nums2);
    println!("Output: k = {}", k2);
    println!("Array after: {:?}", &nums2[0..k2 as usize]);
    println!("Expected: k = 5, array = [0, 1, 2, 3, 4]");
    assert_eq!(k2, 5);
    assert_eq!(&nums2[0..5], &[0, 1, 2, 3, 4]);
    println!("✓ Test 2 passed\n");

    // Test Case 3: No duplicates
    println!("Test 3: [1,2,3]");
    let mut nums3 = vec![1, 2, 3];
    let k3 = removeDuplicates(&mut nums3);
    println!("Output: k = {}", k3);
    println!("Array after: {:?}", &nums3[0..k3 as usize]);
    println!("Expected: k = 3, array = [1, 2, 3]");
    assert_eq!(k3, 3);
    assert_eq!(&nums3[0..3], &[1, 2, 3]);
    println!("✓ Test 3 passed\n");

    // Test Case 4: All same elements
    println!("Test 4: [1,1,1,1]");
    let mut nums4 = vec![1, 1, 1, 1];
    let k4 = removeDuplicates(&mut nums4);
    println!("Output: k = {}", k4);
    println!("Array after: {:?}", &nums4[0..k4 as usize]);
    println!("Expected: k = 1, array = [1]");
    assert_eq!(k4, 1);
    assert_eq!(&nums4[0..1], &[1]);
    println!("✓ Test 4 passed\n");

    // Test Case 5: Negative numbers
    println!("Test 5: [-3,-1,-1,0,0,0,9,9]");
    let mut nums5 = vec![-3, -1, -1, 0, 0, 0, 9, 9];
    let k5 = removeDuplicates(&mut nums5);
    println!("Output: k = {}", k5);
    println!("Array after: {:?}", &nums5[0..k5 as usize]);
    println!("Expected: k = 4, array = [-3, -1, 0, 9]");
    assert_eq!(k5, 4);
    assert_eq!(&nums5[0..4], &[-3, -1, 0, 9]);
    println!("✓ Test 5 passed\n");

    println!("=== All tests passed! ===");
}

/*
 * AFTER YOU'RE DONE:
 * 1. Verify all test cases pass
 * 2. Think: Why can we modify in-place?
 * 3. Why is space complexity O(1)?
 * 4. What if array was unsorted?
 */
