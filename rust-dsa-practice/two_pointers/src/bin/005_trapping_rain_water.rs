/*
 * LeetCode 42: Trapping Rain Water
 * Difficulty: Hard
 * Technique: Two Pointers (or Dynamic Programming)
 *
 * PROBLEM STATEMENT:
 * ==================
 * Given n non-negative integers representing an elevation map where the width
 * of each bar is 1, compute how much water it can trap after raining.
 *
 * Example 1:
 *   Input: height = [0,1,0,2,1,0,1,3,2,1,2,1]
 *   Output: 6
 *   Explanation: The above elevation map is represented by array
 *   [0,1,0,2,1,0,1,3,2,1,2,1]. In this case, 6 units of rain water
 *   (blue section) are trapped.
 *
 * Example 2:
 *   Input: height = [4,2,0,3,2,5]
 *   Output: 9
 *
 * Constraints:
 *   - n == height.length
 *   - 1 <= n <= 2 * 10^4
 *   - 0 <= height[i] <= 10^5
 *
 * ============================================================================
 * APPROACH HINTS:
 * ============================================================================
 *
 * KEY INSIGHT:
 * Water trapped at position i = min(max_left, max_right) - height[i]
 *
 * TWO POINTER STRATEGY:
 * 1. left pointer at start, right at end
 * 2. Track max_left and max_right seen so far
 * 3. Move the pointer with SMALLER value inward
 * 4. Calculate trapped water based on which side has smaller max
 *
 * WHY THIS WORKS:
 * If left_max < right_max:
 *   - Water at current left position is limited by left_max
 *   - We know right side has taller building, so we can use left_max
 * If right_max <= left_max:
 *   - Water at current right position is limited by right_max
 *   - We know left side has taller building, so we can use right_max
 *
 * TIME COMPLEXITY: O(n)
 * SPACE COMPLEXITY: O(1)
 *
 * ============================================================================
 */

/// Calculate how much water can be trapped after raining
fn trap(height: Vec<i32>) -> i32 {
    // TODO: Implement your solution here!
    //
    // Hints:
    // 1. Use two pointers: left at 0, right at len-1
    // 2. Track max_left and max_right
    // 3. While left < right:
    //    - If height[left] < height[right]:
    //      - Update max_left
    //      - Add trapped water: max_left - height[left]
    //      - Move left pointer
    //    - Else:
    //      - Update max_right
    //      - Add trapped water: max_right - height[right]
    //      - Move right pointer
    // 4. Return total trapped water

    0
}

// ============================================================================
// TEST CASES
// ============================================================================

fn main() {
    println!("=== Trapping Rain Water ===\n");

    // Test Case 1: Classic case
    println!("Test 1: [0,1,0,2,1,0,1,3,2,1,2,1]");
    let result1 = trap(vec![0, 1, 0, 2, 1, 0, 1, 3, 2, 1, 2, 1]);
    println!("Output: {}", result1);
    println!("Expected: 6");
    assert_eq!(result1, 6);
    println!("✓ Test 1 passed\n");

    // Test Case 2: Two peaks
    println!("Test 2: [4,2,0,3,2,5]");
    let result2 = trap(vec![4, 2, 0, 3, 2, 5]);
    println!("Output: {}", result2);
    println!("Expected: 9");
    assert_eq!(result2, 9);
    println!("✓ Test 2 passed\n");

    // Test Case 3: No water trapped
    println!("Test 3: [0,1,2,3,4,5]");
    let result3 = trap(vec![0, 1, 2, 3, 4, 5]);
    println!("Output: {}", result3);
    println!("Expected: 0");
    assert_eq!(result3, 0);
    println!("✓ Test 3 passed\n");

    // Test Case 4: Simple valley
    println!("Test 4: [3,0,2]");
    let result4 = trap(vec![3, 0, 2]);
    println!("Output: {}", result4);
    println!("Expected: 2");
    assert_eq!(result4, 2);
    println!("✓ Test 4 passed\n");

    // Test Case 5: Multiple valleys
    println!("Test 5: [5,4,3,4,5]");
    let result5 = trap(vec![5, 4, 3, 4, 5]);
    println!("Output: {}", result5);
    println!("Expected: 3");
    assert_eq!(result5, 3);
    println!("✓ Test 5 passed\n");

    println!("=== All tests passed! ===");
}

/*
 * AFTER YOU'RE DONE:
 * 1. Verify all test cases pass
 * 2. Visualize: draw the elevation map to understand water trapping
 * 3. Think: Why do we move the shorter pointer?
 * 4. Alternative approach: use Dynamic Programming (precompute max_left/right)
 * 5. Space optimization: two pointers is better than DP approach
 */
