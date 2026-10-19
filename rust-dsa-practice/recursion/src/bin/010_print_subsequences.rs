// Problem: print all subsequences of a string, using recursion.
//
// Subsequence vs substring - these are often confused but mean different
// things:
//   - SUBSTRING: a contiguous run of characters from the original string.
//     Nothing can be skipped in the middle.
//       "abc" substrings: "", "a", "b", "c", "ab", "bc", "abc"   (7 total)
//       "ac" is NOT a substring of "abc" - the 'b' in between can't be
//       skipped while staying contiguous.
//   - SUBSEQUENCE: characters from the original string in the same
//     relative ORDER, but NOT required to be contiguous - characters can
//     be skipped.
//       "abc" subsequences: "", "a", "b", "c", "ab", "ac", "bc", "abc"
//       (8 total - includes "ac", which is not a valid substring)
//
// The same substring/subsequence split exists for ARRAYS too, just under
// different names - the terms line up like this:
//   string    <-> array
//   substring <-> SUBARRAY   (contiguous run of elements, order preserved)
//   subsequence <-> SUBSEQUENCE   (same term - order preserved, gaps allowed)
// e.g. for [1, 2, 3]:
//   subarrays:    [], [1], [2], [3], [1,2], [2,3], [1,2,3]        (contiguous)
//   subsequences: [], [1], [2], [3], [1,2], [1,3], [2,3], [1,2,3] (order kept, gaps ok)
// Note [1,3] is a valid subsequence of [1,2,3] but NOT a subarray, for the
// same reason "ac" is a subsequence but not a substring of "abc" - the
// skipped middle element breaks contiguity.
// (A third, looser term - SUBSET - drops the order requirement entirely:
// {3,1} counts as the same subset as {1,3}. Subsequence keeps order,
// subset doesn't; that distinction matters for problems like "subset sum"
// vs. "longest increasing subsequence".)
//
// For a string of length n, there are exactly 2^n subsequences (including
// the empty one): at each of the n positions, independently decide
// "include this character" or "exclude it" - 2 choices per position, n
// positions, 2^n combinations. This "include/exclude" framing is exactly
// how the recursion below is structured, and it's another example of
// MULTIPLE recursion (see 008_nth_fibonacci_recursion.rs) - two branches
// per call, forming a call tree with 2^n leaves.
//
// Recursive definition (build up `current` as we go, print it at the leaf):
//   subsequences(s, i, current):
//     if i == len(s):                        // base case: end of string
//       print(current)
//       return
//     subsequences(s, i + 1, current + s[i])  // branch 1: INCLUDE s[i]
//     subsequences(s, i + 1, current)         // branch 2: EXCLUDE s[i]
//
// e.g. subsequences("ab", 0, "")
//   include 'a' -> subsequences(1, "a")
//     include 'b' -> subsequences(2, "ab") -> print "ab"
//     exclude 'b' -> subsequences(2, "a")  -> print "a"
//   exclude 'a' -> subsequences(1, "")
//     include 'b' -> subsequences(2, "b")  -> print "b"
//     exclude 'b' -> subsequences(2, "")   -> print ""
//
// Complexity: O(2^n) calls (matches the 2^n subsequences that exist, so
// unlike naive Fibonacci this exponential blowup is inherent to the
// output size, not wasted duplicate work - there's nothing to memoize
// here since no subproblem is solved twice). O(n) recursion depth.

fn subsequences(chars: &[char], i: usize, current: &mut String) {
    if i == chars.len() {
        println!("{}", current);
        return;
    }

    // branch 1: include chars[i]
    current.push(chars[i]);
    
    subsequences(chars, i + 1, current);
    current.pop(); // backtrack

    // branch 2: exclude chars[i]
    subsequences(chars, i + 1, current);
}

fn main() {
    let s = "abc";
    let chars: Vec<char> = s.chars().collect();
    let mut current = String::new();
    subsequences(&chars, 0, &mut current);
}
