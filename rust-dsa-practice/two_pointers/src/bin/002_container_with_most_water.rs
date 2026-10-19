/*
 * LeetCode 11: Container With Most Water
 * Difficulty: Medium
 * Technique: Two Pointers
 *
 * PROBLEM STATEMENT:
 * ==================
 * You are given an integer array height of length n.
 * There are n vertical lines drawn such that the two endpoints of the ith line
 * are (i, 0) and (i, height[i]).
 *
 * Find two lines that together with the x-axis form a container, such that
 * the container contains the most water.
 *
 * Return the maximum area of water a container can store.
 * Notice that you may not slant the container.
 *
 * Example 1:
 *   Input: height = [1,8,6,2,5,4,8,3,7]
 *   Output: 49
 *   Explanation: The vertical lines are at index 1 and 8.
 *   Container width = 8 - 1 = 7
 *   Container height = min(8, 7) = 7
 *   Area = 7 * 7 = 49
 *
 * Example 2:
 *   Input: height = [1,1]
 *   Output: 1
 *
 * Constraints:
 *   - 2 <= height.length <= 10^5
 *   - 0 <= height[i] <= 10^4
 *
 * ============================================================================
 * APPROACH HINTS:
 * ============================================================================
 *
 * KEY INSIGHT:
 * Area = width × min(height_left, height_right)
 *
 * MOVEMENT STRATEGY:
 * Start with maximum width (left at 0, right at end)
 * Then shrink width by moving one pointer
 * Which pointer should move?
 *   → Move the pointer with SMALLER height
 *   → Why? If you move the taller one, you can only stay same or decrease
 *      But moving the shorter one might find a taller line
 *
 * TIME COMPLEXITY: O(n)
 * SPACE COMPLEXITY: O(1)
 *
 * ============================================================================
 */

/// Find two lines that form a container with maximum area
fn maxArea(height: Vec<i32>) -> i32 {
    // TODO: Implement your solution here!
    //
    // Hints:
    // 1. Initialize two pointers at start and end
    // 2. Calculate current area
    // 3. Track maximum area seen so far
    // 4. Move the pointer with smaller height inward
    // 5. Repeat until pointers meet

    0
}

// ============================================================================
// TEST CASES
// ============================================================================

fn main() {
    println!("=== Container With Most Water ===\n");

    // Test Case 1: Standard case
    println!("Test 1: [1,8,6,2,5,4,8,3,7]");
    let result1 = maxArea(vec![1, 8, 6, 2, 5, 4, 8, 3, 7]);
    println!("Output: {}", result1);
    println!("Expected: 49");
    assert_eq!(result1, 49);
    println!("✓ Test 1 passed\n");

    // Test Case 2: Two equal heights
    println!("Test 2: [1,1]");
    let result2 = maxArea(vec![1, 1]);
    println!("Output: {}", result2);
    println!("Expected: 1");
    assert_eq!(result2, 1);
    println!("✓ Test 2 passed\n");

    // Test Case 3: Large heights at ends
    println!("Test 3: [2,3,4,5,18,17,6]");
    let result3 = maxArea(vec![2, 3, 4, 5, 18, 17, 6]);
    println!("Output: {}", result3);
    println!("Expected: 17");
    assert_eq!(result3, 17);
    println!("✓ Test 3 passed\n");

    // Test Case 4: Maximum at start and end
    println!("Test 4: [9,3,4,8,2]");
    let result4 = maxArea(vec![9, 3, 4, 8, 2]);
    println!("Output: {}", result4);
    println!("Expected: 16");
    assert_eq!(result4, 16);
    println!("✓ Test 4 passed\n");

    // Test Case 5: All same height
    println!("Test 5: [5,5,5,5]");
    let result5 = maxArea(vec![5, 5, 5, 5]);
    println!("Output: {}", result5);
    println!("Expected: 15");
    assert_eq!(result5, 15);
    println!("✓ Test 5 passed\n");

    println!("=== All tests passed! ===");
}

/*
 * AFTER YOU'RE DONE:
 * 1. Verify all test cases pass
 * 2. Think: Why do we move the shorter pointer?
 * 3. Verify time complexity is O(n), not O(n²)
 * 4. Could we optimize further?
 */
