# 3Sum Problem - Solution Guide

## Problem Recap
Find all unique triplets in an array that sum to zero.

## Solving Strategy

### Step 1: Understand the Problem Better
- **Input:** Array of integers
- **Output:** List of lists (each list is a triplet summing to 0)
- **Constraint:** No duplicate triplets in the output

### Step 2: Key Insight - Reduce to Known Problem
The **3Sum** problem can be reduced to the **2Sum** problem!

**Idea:**
1. Fix one number (let's call it `nums[i]`)
2. Find two numbers that sum to `-nums[i]` (so the three sum to 0)
3. Repeat for all positions

### Step 3: Implement Two-Pointer Technique

**For each fixed number:**
1. Initialize two pointers:
   - `left` = next element after current
   - `right` = last element
   
2. While `left < right`:
   - Calculate `sum = nums[i] + nums[left] + nums[right]`
   - If `sum == 0`: Found triplet! Add to result, move pointers
   - If `sum < 0`: Need larger sum → `left += 1`
   - If `sum > 0`: Need smaller sum → `right -= 1`

### Step 4: Handle Duplicates
This is the tricky part!

**Sort first:** 
- Sorting makes two pointers work
- Also makes deduplication easier

**Skip duplicates:**
```rust
// After sorting, if current element same as previous, skip
if i > 0 && nums[i] == nums[i-1] {
    continue;
}
```

**Skip duplicate results:**
```rust
// After finding a triplet, skip duplicate values
while left < right && nums[left] == nums[left+1] {
    left += 1;
}
while left < right && nums[right] == nums[right-1] {
    right -= 1;
}
```

## Pseudocode

```
function threeSum(nums):
    sort(nums)
    result = []
    
    for i = 0 to len(nums)-3:
        // Skip duplicate first numbers
        if i > 0 and nums[i] == nums[i-1]:
            continue
        
        // Early termination: if smallest sum is too large, stop
        if nums[i] + nums[i+1] + nums[i+2] > 0:
            break
        
        // Skip if largest sum is too small
        if nums[i] + nums[-2] + nums[-1] < 0:
            continue
        
        // Two pointer approach
        left = i + 1
        right = len(nums) - 1
        target = -nums[i]
        
        while left < right:
            sum = nums[left] + nums[right]
            
            if sum == target:
                result.add([nums[i], nums[left], nums[right]])
                
                // Skip duplicates
                while left < right and nums[left] == nums[left+1]:
                    left += 1
                while left < right and nums[right] == nums[right-1]:
                    right -= 1
                
                left += 1
                right -= 1
            
            elif sum < target:
                left += 1
            else:
                right -= 1
    
    return result
```

## Rust Implementation Notes

### Key Rust Concepts You'll Need:
1. **Sorting vectors:** `nums.sort()` (sorts in-place)
2. **Accessing elements:** `nums[i]`, `nums.len()`
3. **Creating vectors:** `vec![]`
4. **Looping:** `for i in 0..nums.len()` or `while left < right`
5. **Comparing:** `==`, `<`, `>`

### Rust-Specific Tips:
```rust
// Sort mutable reference
let mut nums = vec![3, 0, -2, -1];
nums.sort();

// Loop with index
for i in 0..nums.len() - 2 {
    // Can access nums[i], nums[i+1], etc
}

// Two pointers
let mut left = i + 1;
let mut right = nums.len() - 1;
while left < right {
    let sum = nums[i] + nums[left] + nums[right];
    // ...
    left += 1;
    right -= 1;
}

// Push to result
result.push(vec![nums[i], nums[left], nums[right]]);
```

## Test Cases to Consider

1. **Basic case:** `[-1,0,1,2,-1,-4]` → `[[-1,-1,2],[-1,0,1]]`
2. **No solution:** `[0,1,1]` → `[]`
3. **All zeros:** `[0,0,0]` → `[[0,0,0]]`
4. **Large array:** Handle duplicates correctly
5. **Negative only:** `[-4,-2,-2,-2]` → should find valid triplets

## Time & Space Complexity

**Time Complexity:**
- Sorting: O(n log n)
- Outer loop: O(n)
- Inner two-pointer: O(n)
- **Total: O(n²)** (dominated by two pointers, not sorting)

**Space Complexity:**
- O(1) if not counting the output
- O(n) if counting output in worst case
- Sorting space depends on algorithm (Python: O(n), Rust: depends)

## Common Mistakes to Avoid

❌ **Forgetting to sort** - Two pointers only work on sorted arrays
❌ **Not handling duplicates** - Will get duplicate triplets in output
❌ **Off-by-one errors** - Careful with array indices
❌ **Wrong termination condition** - Make sure `left < right`
❌ **Wrong target sum** - Remember target is `-nums[i]`, not `0`

## Optimization Tips

1. **Early termination:**
   - If `nums[i] > 0`, all future sums will be positive, so break

2. **Skip early:**
   - If `nums[i] + nums[i+1] + nums[i+2] > 0`, can't find sum to 0

3. **Cache lookups:**
   - Use `len()` once instead of calling it multiple times

## After You Solve It

1. Verify all test cases pass
2. Check the time complexity is O(n²)
3. Make sure no duplicate triplets in output
4. Try the problem with even larger arrays
5. Could you solve it in O(n log n)? (Hard mode!)

---

**Good luck!** Remember:
- Sort the array first
- Use two pointers for each fixed element
- Skip duplicates carefully
- Test with provided examples

Start coding! 🚀
