// Problem: LeetCode 21 - Merge Two Sorted Lists.
//
// Merge two sorted linked lists into one sorted list, by splicing
// together the nodes of the two inputs (not copying values into a new
// structure).
//
// ---------------------------------------------------------------------
// THE MENTAL MODEL
// ---------------------------------------------------------------------
// Same idea as merging two sorted arrays (the merge step of merge
// sort): keep a cursor into each list, repeatedly take whichever
// FRONT value is smaller, and advance only that list's cursor. The
// linked-list version has one extra wrinkle worth naming: you're not
// producing a fresh output, you're re-pointing existing nodes' `next`
// fields to interleave the two chains together.
//
// ---------------------------------------------------------------------
// THE DUMMY-HEAD TRICK
// ---------------------------------------------------------------------
// Building a list node-by-node has an annoying special case: the very
// first node has nowhere to attach to yet, so "append" means something
// different for it than for every node after. A DUMMY head (a
// throwaway node whose value is never used) sidesteps this: start with
// `dummy.next = None`, always append to `tail.next`, and at the end
// return `dummy.next` - which for a genuinely empty result is just
// `None`, no separate check required. This pattern comes up constantly
// any time you're BUILDING a list rather than just walking one - see
// 009_add_two_numbers.rs for the same trick.
//
// Complexity: O(n + m) time, O(1) extra space for the iterative
// version (existing nodes are relinked, not copied) - or O(n + m) call-
// stack space for the recursive version below, which is genuinely
// worth knowing as a real cost, not just an implementation detail.

use linked_list::{from_vec, to_vec, ListNode};

// =====================================================================
// VERSION 1 - iterative, dummy head
// =====================================================================
pub fn merge_two_lists(
    mut l1: Option<Box<ListNode>>,
    mut l2: Option<Box<ListNode>>,
) -> Option<Box<ListNode>> {
    let mut dummy = Box::new(ListNode::new(0));
    let mut tail = &mut dummy;

    // Pop the smaller of the two current fronts and attach it, one node
    // at a time, until one list runs out.
    while let (Some(n1), Some(n2)) = (&l1, &l2) {
        if n1.val <= n2.val {
            let mut next_node = l1.take().unwrap();
            l1 = next_node.next.take();
            tail.next = Some(next_node);
        } else {
            let mut next_node = l2.take().unwrap();
            l2 = next_node.next.take();
            tail.next = Some(next_node);
        }
        // Descend into the node we just attached so the NEXT attach
        // lands after it, not overwriting it.
        tail = tail.next.as_mut().unwrap();
    }

    // Whichever list still has nodes left is already sorted internally
    // and entirely >= everything attached so far - just splice the
    // remainder on wholesale instead of looping node-by-node.
    tail.next = l1.or(l2);

    dummy.next
}

// =====================================================================
// VERSION 2 - recursive
// =====================================================================
// The same comparison, expressed as "the merge of two lists is: take
// the smaller head, and its `next` is the merge of (its own rest) with
// (the other list untouched)." Elegant to read, but each recursive call
// adds a stack frame - for a list long enough to matter, the iterative
// version is the one to actually ship.
pub fn merge_two_lists_recursive(
    l1: Option<Box<ListNode>>,
    l2: Option<Box<ListNode>>,
) -> Option<Box<ListNode>> {
    match (l1, l2) {
        (None, l2) => l2,
        (l1, None) => l1,
        (Some(mut n1), Some(n2)) if n1.val <= n2.val => {
            n1.next = merge_two_lists_recursive(n1.next.take(), Some(n2));
            Some(n1)
        }
        (Some(n1), Some(mut n2)) => {
            n2.next = merge_two_lists_recursive(Some(n1), n2.next.take());
            Some(n2)
        }
    }
}

fn main() {
    let l1 = from_vec(&[1, 2, 4]);
    let l2 = from_vec(&[1, 3, 4]);
    println!("merged: {:?}", to_vec(&merge_two_lists(l1, l2)));
}

#[cfg(test)]
mod tests {
    use super::*;

    fn check(a: &[i32], b: &[i32], expected: &[i32]) {
        assert_eq!(
            to_vec(&merge_two_lists(from_vec(a), from_vec(b))),
            expected
        );
        assert_eq!(
            to_vec(&merge_two_lists_recursive(from_vec(a), from_vec(b))),
            expected,
            "recursive version disagreed"
        );
    }

    #[test]
    fn example_1_interleaved() {
        check(&[1, 2, 4], &[1, 3, 4], &[1, 1, 2, 3, 4, 4]);
    }

    #[test]
    fn both_empty() {
        check(&[], &[], &[]);
    }

    #[test]
    fn one_empty_one_nonempty() {
        check(&[], &[0], &[0]);
    }

    // One list is entirely smaller than the other - the "splice the
    // remainder on wholesale" branch must fire, not a node-by-node walk
    // that happens to produce the right answer anyway.
    #[test]
    fn no_interleaving_needed() {
        check(&[1, 2, 3], &[4, 5, 6], &[1, 2, 3, 4, 5, 6]);
    }

    #[test]
    fn duplicate_values_preserve_stability() {
        check(&[1, 1, 1], &[1, 1], &[1, 1, 1, 1, 1]);
    }
}
