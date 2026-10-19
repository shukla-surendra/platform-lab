// Problem: LeetCode 206 - Reverse Linked List.
//
// Reverse a singly linked list and return the new head.
//
// ---------------------------------------------------------------------
// THE MENTAL MODEL: THREE POINTERS, WALKING TOGETHER
// ---------------------------------------------------------------------
// Reversing an array is easy because you can index both ends and swap
// inward. A singly linked list only ever lets you look FORWARD - once
// you overwrite a node's `next` to point backward, you've destroyed
// your only way to reach whatever used to come after it, unless you
// saved it first. That's the whole difficulty, and the fix is exactly
// three pointers marching forward in lockstep: `prev` (the reversed
// portion built so far, starts as None), `current` (the node being
// flipped right now), and a temporary that remembers `current`'s
// original `next` BEFORE it gets overwritten.
//
//     None <- 1    2 -> 3 -> 4 -> None      (prev=None, current=1)
//      prev    current
//
//     None <- 1 <- 2    3 -> 4 -> None      (prev=1, current=2)
//             prev    current
//
//     ... continues until current runs out; prev is then the new head.
//
// ---------------------------------------------------------------------
// VERSION 1 - iterative
// ---------------------------------------------------------------------
// Complexity: O(n) time, O(1) space - the nodes are relinked in place,
// nothing is allocated.

use linked_list::{from_vec, to_vec, ListNode};

pub fn reverse_list(mut head: Option<Box<ListNode>>) -> Option<Box<ListNode>> {
    let mut prev: Option<Box<ListNode>> = None;

    while let Some(mut current) = head {
        head = current.next.take(); // save what came next BEFORE overwriting it
        current.next = prev; // flip this node's link backward
        prev = Some(current); // this node joins the reversed portion
    }

    prev
}

// =====================================================================
// VERSION 2 - recursive
// =====================================================================
// This is the same "prev, current" walk as the iterative version, just
// expressed as a call stack carrying `prev` forward instead of a `while`
// loop mutating it - a direct translation, not a different algorithm.
// At each step: detach `current`'s old `next`, point `current` back at
// `prev`, then recurse into whatever came next, now carrying `current`
// as the new `prev`. The base case - `next` is empty - means the node
// we're holding is the new head, so return it.
//
// Same O(n) time as the iterative version, but O(n) call-stack space
// instead of O(1) - worth being explicit that this is a real cost, not
// just "the recursive one" being interchangeable with the iterative one.
pub fn reverse_list_recursive(head: Option<Box<ListNode>>) -> Option<Box<ListNode>> {
    fn walk(mut current: Box<ListNode>, prev: Option<Box<ListNode>>) -> Option<Box<ListNode>> {
        let next = current.next.take();
        current.next = prev;
        match next {
            Some(following) => walk(following, Some(current)),
            None => Some(current), // current has no more "next" -> it's the new head
        }
    }

    match head {
        Some(node) => walk(node, None),
        None => None,
    }
}

fn main() {
    let list = from_vec(&[1, 2, 3, 4, 5]);
    println!("reversed: {:?}", to_vec(&reverse_list(list)));
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn example_1() {
        assert_eq!(to_vec(&reverse_list(from_vec(&[1, 2, 3, 4, 5]))), vec![
            5, 4, 3, 2, 1
        ]);
    }

    #[test]
    fn two_elements() {
        assert_eq!(to_vec(&reverse_list(from_vec(&[1, 2]))), vec![2, 1]);
    }

    #[test]
    fn empty_list() {
        assert_eq!(to_vec(&reverse_list(from_vec(&[]))), Vec::<i32>::new());
    }

    #[test]
    fn single_node_is_its_own_reverse() {
        assert_eq!(to_vec(&reverse_list(from_vec(&[42]))), vec![42]);
    }

    #[test]
    fn recursive_version_agrees() {
        for input in [vec![1, 2, 3, 4, 5], vec![1], vec![]] {
            let expected = to_vec(&reverse_list(from_vec(&input)));
            assert_eq!(
                to_vec(&reverse_list_recursive(from_vec(&input))),
                expected,
                "recursive disagreed on {input:?}"
            );
        }
    }
}
