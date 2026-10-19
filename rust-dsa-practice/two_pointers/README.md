# Two Pointers Technique Practice

Practice problems using the **two-pointer technique** in Rust.

## What is Two Pointers?

Two pointers is a technique where you maintain two indices (pointers) into an array, starting from different positions, and move them based on some condition.

**Common uses:**
- Finding pairs that sum to a target
- Removing duplicates
- Merging sorted arrays
- Container with most water
- 3Sum, 4Sum problems

## Problems in This Folder

### 001: 3Sum (Medium)
**Difficulty:** Medium  
**Technique:** Two Pointers + Sorting  
**Key Concepts:** Deduplication, moving pointers based on sum

**Problem:** Find all unique triplets that sum to zero.

**To solve:**
```bash
cd ~/projects/2026/platform-lab/rust_dsa_practice/two_pointers

# Read the problem and hints
cat src/bin/001_3sum.rs

# Read solution guide (hints only, no solution)
cat SOLUTION_GUIDE.md

# Implement your solution in 001_3sum.rs

# Test your solution
cargo run --bin 001_3sum

# When all tests pass, you're done!
```

## How to Use This Folder

1. **Read the problem** in `src/bin/PROBLEM.rs`
   - Problem statement is at the top
   - Hints are provided
   - Test cases are at the bottom

2. **Read the solution guide** `SOLUTION_GUIDE.md`
   - Strategy for approaching the problem
   - Pseudocode (language-agnostic)
   - Rust-specific tips
   - Common mistakes to avoid

3. **Implement your solution**
   - Write in the `fn solution()` function
   - Don't modify test cases

4. **Test your solution**
   ```bash
   cargo run --bin PROBLEM_NUMBER
   ```

5. **Debug if needed**
   - Check the hints in the problem file
   - Review pseudocode in solution guide
   - Add print statements to debug

## Problem Progression

Start with **001_3Sum** first. Future problems will be added in order of difficulty.

Coming soon:
- 002: Container with Most Water
- 003: Trapping Rain Water
- 004: Remove Duplicates from Sorted Array
- 005: Move Zeros

## Learning Goals

By solving problems in this section, you'll understand:
- ✓ When to use two pointers
- ✓ How to initialize and move pointers
- ✓ Two pointer examples: sum problems, array manipulation
- ✓ Time complexity: usually O(n) with two pointers vs O(n²) brute force
- ✓ Space complexity: often O(1) or O(n) depending on problem

## Tips for Success

1. **Always start by sorting** if needed - many two-pointer problems need sorted input
2. **Think about movement logic** - when should left move, when should right move?
3. **Handle duplicates** - this is often the trickiest part
4. **Test edge cases** - empty array (if applicable), single element, duplicates
5. **Analyze complexity** - verify your solution is actually O(n), not O(n²)

## File Structure

```
two_pointers/
├── Cargo.toml              # Rust project file
├── README.md               # This file
├── SOLUTION_GUIDE.md       # Hints (no spoilers!)
└── src/
    └── bin/
        ├── 001_3sum.rs     # Your assignment
        └── PROBLEM.rs      # Future problems
```

## Command Cheatsheet

```bash
# Test a specific problem
cargo run --bin 001_3sum

# Build all binaries
cargo build --release

# Run with verbose output
cargo run --bin 001_3sum -- --nocapture
```

## Troubleshooting

### "Cannot find function X"
Check that your function signature matches what's expected in the problem file.

### "Index out of bounds"
Check loop conditions: are you accessing valid indices?

### "Wrong output"
- Verify test case expectations
- Check deduplication logic
- Add println! for debugging

### "Test panics"
Read the panic message - it tells you what's wrong!

## Resources

- [Two Pointers Technique Explanation](https://www.geeksforgeeks.org/two-pointers-technique/)
- [LeetCode Two Pointers Problems](https://leetcode.com/tag/two-pointers/)
- [Rust Book - Ownership & References](https://doc.rust-lang.org/book/ch04-01-what-is-ownership.html)

## Ready?

Start with **001_3sum.rs** and implement your solution! 🚀

Don't look at other solutions online until you've tried. The struggle is where learning happens!
