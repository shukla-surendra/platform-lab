/*
 * LeetCode 15: 3Sum
 * Difficulty: Medium
 * Technique: Two Pointers
 *
 * PROBLEM STATEMENT:
 * ==================
 * Given an integer array nums, return all the triplets [nums[i], nums[j], nums[k]]
 * such that i != j, i != k, and j != k, and nums[i] + nums[j] + nums[k] == 0.
 *
 * IMPORTANT: The solution set must not contain duplicate triplets.
 *
 * Example 1:
 *   Input: nums = [-1,0,1,2,-1,-4]
 *   Output: [[-1,-1,2],[-1,0,1]]
 *
 * Example 2:
 *   Input: nums = [0,1,1]
 *   Output: []
 *
 * Example 3:
 *   Input: nums = [0,0,0]
 *   Output: [[0,0,0]]
 *
 * Constraints:
 *   - 3 <= nums.length <= 3000
 *   - -10^5 <= nums[i] <= 10^5
 *
 * ============================================================================
 * APPROACH HINTS (Try to figure out before reading hints!)
 * ============================================================================
 *
 * KEY INSIGHT:
 * This problem is similar to TwoSum, but with THREE numbers instead of two.
 *
 * SUGGESTED APPROACH:
 * 1. Sort the array first
 *    - Why? Makes it easier to use two pointers
 *    - Makes deduplication easier
 *
 * 2. For each element (as the "first" number):
 *    - Fix that element
 *    - Use TWO POINTERS on the remaining array
 *    - Left pointer starts at index i+1
 *    - Right pointer starts at end
 *
 * 3. Two-pointer logic:
 *    - If sum == target (0), found a triplet! Add to result, move pointers
 *    - If sum < target, move left pointer right (need larger sum)
 *    - If sum > target, move right pointer left (need smaller sum)
 *
 * 4. Handle duplicates:
 *    - After sorting, skip duplicate values
 *    - When you find a triplet, skip duplicates before continuing
 *
 * TIME COMPLEXITY: O(n²)
 *   - Outer loop: O(n)
 *   - Inner two-pointer: O(n)
 *
 * SPACE COMPLEXITY: O(1) or O(n) depending on sorting algorithm
 *   - Not counting the output array
 *
 * ============================================================================
 * YOUR TASK:
 * ============================================================================
 * Implement the function below. Try to solve it YOURSELF first!
 * Don't peek at solutions online until you've attempted it.
 *
 * Test cases are provided below. Run with:
 * cd ~/projects/2026/platform-lab/rust_dsa_practice/two_pointers
 * cargo run --bin 001_3sum
 *
 * ============================================================================
 */

/// Find all unique triplets that sum to zero
///
/// # Arguments
/// * `nums` - A mutable vector of integers (we need to sort it)
///
/// # Returns
/// A vector of vectors, each inner vector contains three numbers that sum to 0
fn three_sum(nums: &mut Vec<i32>) -> Vec<Vec<i32>> {
    // TODO: Implement your solution here!
    //
    // Hints:
    // 1. Start by sorting the vector
    // 2. Use outer loop for the "first" number
    // 3. For each first number, use two pointers for remaining array
    // 4. Handle duplicates carefully

    // Placeholder return (replace with your implementation)
    vec![]
}

// ============================================================================
// TEST CASES - DO NOT MODIFY
// ============================================================================

fn main() {
    println!("=== 3Sum Problem ===\n");

    // Test Case 1: Mixed positive/negative
    println!("Test 1: [-1,0,1,2,-1,-4]");
    let mut nums1 = vec![-1, 0, 1, 2, -1, -4];
    let result1 = three_sum(&mut nums1);
    println!("Output: {:?}", result1);
    println!("Expected: [[-1,-1,2],[-1,0,1]]");
    assert_contains_triplet(&result1, &[-1, -1, 2]);
    assert_contains_triplet(&result1, &[-1, 0, 1]);
    println!("✓ Test 1 passed\n");

    // Test Case 2: No solution
    println!("Test 2: [0,1,1]");
    let mut nums2 = vec![0, 1, 1];
    let result2 = three_sum(&mut nums2);
    println!("Output: {:?}", result2);
    println!("Expected: []");
    assert_eq!(result2.len(), 0);
    println!("✓ Test 2 passed\n");

    // Test Case 3: All zeros
    println!("Test 3: [0,0,0]");
    let mut nums3 = vec![0, 0, 0];
    let result3 = three_sum(&mut nums3);
    println!("Output: {:?}", result3);
    println!("Expected: [[0,0,0]]");
    assert_contains_triplet(&result3, &[0, 0, 0]);
    assert_eq!(result3.len(), 1);
    println!("✓ Test 3 passed\n");

    // Test Case 4: Larger array with duplicates
    println!("Test 4: [-2,0,1,1,2]");
    let mut nums4 = vec![-2, 0, 1, 1, 2];
    let result4 = three_sum(&mut nums4);
    println!("Output: {:?}", result4);
    println!("Expected: [[-2,0,2],[-2,1,1]]");
    assert_contains_triplet(&result4, &[-2, 0, 2]);
    assert_contains_triplet(&result4, &[-2, 1, 1]);
    println!("✓ Test 4 passed\n");

    // Test Case 5: Negative numbers
    println!("Test 5: [-4,-2,-2,-2,0,1,2,2,2,3,3,4,4,6,6]");
    let mut nums5 = vec![-4, -2, -2, -2, 0, 1, 2, 2, 2, 3, 3, 4, 4, 6, 6];
    let result5 = three_sum(&mut nums5);
    println!("Output: {:?}\n", result5);
    // Multiple valid triplets exist
    assert!(result5.len() > 0, "Should find at least one triplet");
    for triplet in &result5 {
        assert_eq!(triplet[0] + triplet[1] + triplet[2], 0,
                   "Each triplet must sum to 0");
    }
    println!("✓ Test 5 passed\n");

    println!("=== All tests passed! ===");
}

/// Helper function to check if result contains a specific triplet
fn assert_contains_triplet(result: &Vec<Vec<i32>>, triplet: &[i32; 3]) {
    let mut sorted_triplet = triplet.to_vec();
    sorted_triplet.sort();

    for res_triplet in result {
        let mut res_sorted = res_triplet.clone();
        res_sorted.sort();
        if res_sorted == sorted_triplet {
            return;
        }
    }
    panic!("Expected triplet {:?} not found in result {:?}", triplet, result);
}

/*
 * ============================================================================
 * AFTER YOU'RE DONE:
 * ============================================================================
 *
 * 1. Test your solution:
 *    cargo run --bin 001_3sum
 *
 * 2. Once all tests pass, optimize:
 *    - Can you reduce memory usage?
 *    - Can you handle duplicates more efficiently?
 *
 * 3. Think about edge cases:
 *    - What if array has very large numbers?
 *    - What if all numbers are the same?
 *    - What if array is very small (exactly 3 elements)?
 *
 * 4. Time complexity analysis:
 *    - What is the actual time complexity of your solution?
 *    - Can it be better than O(n²)?
 *
 * ============================================================================
 * LEARNING OBJECTIVES:
 * ============================================================================
 * After solving this, you should understand:
 * ✓ Two-pointer technique and when to use it
 * ✓ How sorting helps with two-pointer problems
 * ✓ How to handle duplicates in results
 * ✓ Converting problem (find 3 numbers) to simpler problem (find 2 numbers)
 * ✓ Time complexity vs Space complexity tradeoffs
 *
 * ============================================================================
 */
