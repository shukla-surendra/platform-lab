// Problem: determine whether a string is a palindrome (reads the same
// forwards and backwards), using recursion.
//
// Using a single index `i` (same optimization as 006_reverse_array_recursion.rs:
// derive the mirrored position from `i` and the length `n`, instead of
// threading two pointers), compare the character at `i` with the character
// at `n - 1 - i`. If they differ, it's not a palindrome. Otherwise recurse
// inward on `i + 1` until the pointers meet or cross.
//
// Recursive definition:
//   is_palindrome(s, i, n):
//     if i >= n - 1 - i:                       // base case: 0 or 1 chars left
//       return true
//     if s[i] != s[n - 1 - i]:
//       return false
//     return is_palindrome(s, i + 1, n)         // recursive case
//
// e.g. is_palindrome("racecar", 0, 7)
//   s[0]='r' == s[6]='r' -> is_palindrome(1, 7)
//   s[1]='a' == s[5]='a' -> is_palindrome(2, 7)
//   s[2]='c' == s[4]='c' -> is_palindrome(3, 7)
//   3 >= 7-1-3=3 -> base case -> true
//
// Complexity: O(n) time (n/2 comparisons), O(n) extra space for the
// recursive call stack (not tail-call optimized by rustc) - same tradeoff
// as the array-reversal problem: an iterative loop version would be O(1)
// extra space.

fn is_palindrome(chars: &[char], i: usize, n: usize) -> bool {

    if i >= n - 1 - i {
        return true;
    }
    if chars[i] != chars[n - 1 - i] {
        return false;
    }
    is_palindrome(chars, i + 1, n) // recursive case, non semicolon because it's an expression returning a value
}

fn main() {
    for s in ["racecar", "hello", "a", "", "noon"] {
        let chars: Vec<char> = s.chars().collect();
        let n = chars.len();
        println!("{:?} is palindrome: {}", s, is_palindrome(&chars, 0, n));
    }
}
