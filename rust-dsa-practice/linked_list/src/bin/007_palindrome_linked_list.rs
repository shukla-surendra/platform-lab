// Problem: LeetCode 234 - Palindrome Linked List.
//
// Given a singly linked list, determine whether it reads the same
// forward and backward.
//
// ---------------------------------------------------------------------
// WHY THE OBVIOUS APPROACH IS AWKWARD
// ---------------------------------------------------------------------
// A linked list can only be walked forward - there's no `list[i]` to
// compare the first and last elements directly the way you would with
// an array. The straightforward fix, "copy every value into a Vec, then
// two-pointer-compare the Vec front and back," works and is O(n) time -
// but it pays O(n) EXTRA space for the copy, for a problem that can
// actually be solved in O(1) extra space if you're willing to
// temporarily rearrange the list itself.
//
// ---------------------------------------------------------------------
// VERSION 1 - the honest O(n)-space baseline
// ---------------------------------------------------------------------
// Worth writing first, both because it's obviously correct and because
// it doesn't mutate the input - sometimes that matters more than the
// extra space.
use linked_list::{from_vec, ListNode};

pub fn is_palindrome_extra_space(head: &Option<Box<ListNode>>) -> bool {
    let mut values = Vec::new();
    let mut cursor = head;
    while let Some(node) = cursor {
        values.push(node.val);
        cursor = &node.next;
    }

    if values.is_empty() {
        return true; // an empty list is trivially its own palindrome
    }

    let mut left = 0;
    let mut right = values.len() - 1;
    while left < right {
        if values[left] != values[right] {
            return false;
        }
        left += 1;
        right -= 1;
    }
    true
}

// =====================================================================
// VERSION 2 - O(1) extra space: find the middle, reverse the second
// half, compare, then (for good citizenship) put the list back together
// =====================================================================
// This combines two techniques already built in this crate:
//   - the slow/fast middle-finding walk from
//     008_middle_of_the_linked_list.rs,
//   - the in-place reversal from 005_reverse_linked_list.rs,
// applied to just the second half. Once the second half is reversed,
// its front-to-back order is the ORIGINAL list's back-to-front order -
// so walking the first half and the reversed second half in lockstep is
// exactly comparing the list against its own reverse, without ever
// allocating a second list or a Vec.
//
//     1 -> 2 -> 3 -> 2 -> 1
//     find middle (slow/fast):      1 -> 2 -> [3] -> 2 -> 1
//     reverse from the middle on:   1 -> 2 -> 3 <- 2 <- 1
//     compare first half against reversed second half, walking both
//     forward: (1,1) (2,2) match -> palindrome
//
// Complexity: O(n) time, O(1) extra space. This does temporarily mutate
// the list's link structure (reversing the second half) - reversing it
// back at the end restores the original list, at the cost of a bit more
// code, purely so the function is side-effect-free from the caller's
// perspective. Whether that restoration is worth the extra code is a
// legitimate judgment call; it's included here because "does this
// function mutate its input" is exactly the kind of thing worth being
// asked about, and worth having a considered answer to either way.
pub fn is_palindrome_in_place(head: &mut Option<Box<ListNode>>) -> bool {
    // Count the length first - simpler and just as O(n) as a slow/fast
    // walk, and it sidesteps the slow/fast walk's usual off-by-one
    // fuss around odd vs. even length.
    let len = {
        let mut n = 0;
        let mut cursor = head.as_ref();
        while let Some(node) = cursor {
            n += 1;
            cursor = node.next.as_ref();
        }
        n
    };

    // An empty or single-node list is trivially its own palindrome,
    // and `len - 1` below would underflow for len == 0 - handle both
    // up front rather than folding them into the general walk.
    if len <= 1 {
        return true;
    }

    // Small helper: walk `(len - 1) / 2` steps from `head` and return a
    // fresh mutable borrow of the node just before the second half.
    // Re-deriving this (rather than holding one long-lived reference
    // across the whole function) is what lets the comparison walk below
    // borrow `head` immutably in between without the two borrows
    // overlapping - the split-half boundary is a fixed step count, so
    // re-walking it is cheap and keeps each borrow's lifetime short and
    // non-overlapping.
    fn first_half_tail(head: &mut Option<Box<ListNode>>, steps: i32) -> &mut Box<ListNode> {
        let mut node = head.as_mut().unwrap();
        for _ in 0..steps {
            node = node.next.as_mut().unwrap();
        }
        node
    }
    let half_steps = (len - 1) / 2;

    // Detach the second half (for odd length, the true middle element
    // stays in the FIRST half - it never needs comparing against
    // anything, being its own mirror).
    let second_half = first_half_tail(head, half_steps).next.take();

    // Reverse the detached second half (same walk as 206).
    let mut reversed_second_half: Option<Box<ListNode>> = None;
    let mut remaining = second_half;
    while let Some(mut node) = remaining {
        remaining = node.next.take();
        node.next = reversed_second_half;
        reversed_second_half = Some(node);
    }

    // Walk the first half and the reversed second half in lockstep.
    let mut is_palindrome = true;
    let mut left = head.as_ref();
    let mut right = reversed_second_half.as_ref();
    while let (Some(l), Some(r)) = (left, right) {
        if l.val != r.val {
            is_palindrome = false;
            break;
        }
        left = l.next.as_ref();
        right = r.next.as_ref();
    }

    // Restore: reverse the second half back, and reattach it.
    let mut restored: Option<Box<ListNode>> = None;
    let mut remaining = reversed_second_half;
    while let Some(mut node) = remaining {
        remaining = node.next.take();
        node.next = restored;
        restored = Some(node);
    }
    first_half_tail(head, half_steps).next = restored;

    is_palindrome
}

fn main() {
    let a = from_vec(&[1, 2, 2, 1]);
    println!("[1,2,2,1] extra-space: {}", is_palindrome_extra_space(&a));

    let mut b = from_vec(&[1, 2, 2, 1]);
    println!("[1,2,2,1] in-place:    {}", is_palindrome_in_place(&mut b));
}

#[cfg(test)]
mod tests {
    use super::*;
    use linked_list::to_vec;

    fn check(values: &[i32], expected: bool) {
        assert_eq!(
            is_palindrome_extra_space(&from_vec(values)),
            expected,
            "extra-space version, input {values:?}"
        );
        let mut list = from_vec(values);
        assert_eq!(
            is_palindrome_in_place(&mut list),
            expected,
            "in-place version, input {values:?}"
        );
        // The in-place version must leave the list exactly as it found
        // it - this is the whole point of the restoration step.
        assert_eq!(to_vec(&list), values, "in-place version mutated its input");
    }

    #[test]
    fn even_length_palindrome() {
        check(&[1, 2, 2, 1], true);
    }

    #[test]
    fn odd_length_palindrome() {
        check(&[1, 2, 3, 2, 1], true);
    }

    #[test]
    fn not_a_palindrome() {
        check(&[1, 2], false);
    }

    #[test]
    fn single_node_is_trivially_a_palindrome() {
        check(&[7], true);
    }

    #[test]
    fn empty_list_is_trivially_a_palindrome() {
        check(&[], true);
    }

    #[test]
    fn odd_length_middle_never_needs_a_match() {
        // The middle element (5) has no counterpart to compare against
        // - it must not accidentally participate in the comparison.
        check(&[3, 5, 3], true);
        check(&[3, 9, 3], true); // middle value is irrelevant either way
    }
}
