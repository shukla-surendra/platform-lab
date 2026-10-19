// Problem: LeetCode 19 - Remove Nth Node From End of List.
//
// Remove the n-th node counting from the END of the list (1-indexed:
// n=1 means the last node), and return the head.
//
// ---------------------------------------------------------------------
// THE TEXTBOOK ANSWER, AND WHY IT DOESN'T TRANSLATE DIRECTLY HERE
// ---------------------------------------------------------------------
// The classic language-agnostic answer is a two-pointer "gap" trick:
// advance a `fast` pointer n+1 nodes ahead of a `slow` pointer first,
// then move both one step at a time - when `fast` falls off the end,
// `slow` sits exactly on the node just before the one to remove, in a
// single pass.
//
// That trick needs `fast` and `slow` to be two INDEPENDENT live cursors
// into the same chain at the same time, with `slow` eventually needing
// to MUTATE the node it's parked on. In this crate's `ListNode`
// representation (`Option<Box<ListNode>>`, one owner per node - see
// `src/lib.rs`), that's exactly the shape safe Rust won't allow: two
// simultaneous references into one owned chain, one of them mutable, is
// the aliasing safe Rust exists to prevent. (This is the same wall
// 001/003/004 hit for a different reason - there, the DATA itself
// wasn't tree-shaped; here, the ALGORITHM wants two independent cursors
// over data that genuinely is tree-shaped. `RawNode` would sidestep it
// the same way it does there, at the same cost: correctness becomes
// the programmer's job again, not the compiler's.)
//
// ---------------------------------------------------------------------
// THE SAFE-RUST-NATIVE ANSWER: COUNT FIRST, THEN WALK ONCE WITH ONE
// CURSOR
// ---------------------------------------------------------------------
// Count the list's length with a read-only pass (only ever needs `&`,
// never aliases anything). The node to remove is then at a known,
// fixed position - `length - n` from the head (0-indexed) - so a
// SECOND pass walks a single `&mut` cursor there directly and unlinks
// it. Only one live mutable reference exists at any moment, which is
// exactly what keeps this simple, safe, and boring - it trades "one
// pass" for "two passes, each trivial," which is still O(n) time
// overall, not a real cost.
//
// The dummy head (same trick as 002, 006, and the array/gap trick's own
// off-by-one) removes the "n equals the whole list's length, so the
// HEAD itself needs removing" special case - counting from the dummy
// means position 0 is always legally "the node before the one being
// removed," even when that's the real head.
//
// Complexity: O(n) time (two linear passes), O(1) space.

use linked_list::{from_vec, to_vec, ListNode};

pub fn remove_nth_from_end(head: Option<Box<ListNode>>, n: i32) -> Option<Box<ListNode>> {
    let mut dummy = Box::new(ListNode::new(0));
    dummy.next = head;

    let length = {
        let mut len = 0;
        let mut cursor = dummy.next.as_ref();
        while let Some(node) = cursor {
            len += 1;
            cursor = node.next.as_ref();
        }
        len
    };

    // Walk to the node just before the one to remove: `length - n`
    // steps from the dummy (0-indexed position of "one before target").
    let mut before = &mut dummy;
    for _ in 0..length - n {
        before = before.next.as_mut().unwrap();
    }

    let to_remove = before.next.take().unwrap();
    before.next = to_remove.next;

    dummy.next
}

fn main() {
    let list = from_vec(&[1, 2, 3, 4, 5]);
    println!(
        "remove 2nd from end of [1..5]: {:?}",
        to_vec(&remove_nth_from_end(list, 2))
    );
}

#[cfg(test)]
mod tests {
    use super::*;

    fn check(values: &[i32], n: i32, expected: &[i32]) {
        assert_eq!(to_vec(&remove_nth_from_end(from_vec(values), n)), expected);
    }

    #[test]
    fn example_1_middle_removal() {
        check(&[1, 2, 3, 4, 5], 2, &[1, 2, 3, 5]);
    }

    // n equals the list length: the HEAD itself must be removed - the
    // exact case the dummy node exists to handle without a branch.
    #[test]
    fn remove_the_head_when_n_equals_length() {
        check(&[1, 2, 3], 3, &[2, 3]);
    }

    #[test]
    fn remove_the_last_node_n_equals_one() {
        check(&[1, 2, 3], 1, &[1, 2]);
    }

    #[test]
    fn single_node_list_becomes_empty() {
        check(&[1], 1, &[]);
    }
}
