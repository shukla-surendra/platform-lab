// Problem: LeetCode 876 - Middle of the Linked List.
//
// Return the middle node of a singly linked list. If there are two
// middle nodes (even length), return the SECOND one.
//
// ---------------------------------------------------------------------
// WHY THE OBVIOUS APPROACH IS AWKWARD
// ---------------------------------------------------------------------
// Without indexing, "the middle" needs the length first - the natural
// instinct is a two-pass approach: walk once to count the nodes, then
// walk again to `length / 2`. That's correct and O(n), but it reads the
// list twice for information that a single, cleverer pass can extract
// directly.
//
// ---------------------------------------------------------------------
// THE SLOW/FAST WALK
// ---------------------------------------------------------------------
// The same pointer pattern as Floyd's cycle detection
// (003_linked_list_cycle.rs), repurposed: advance `slow` one node per
// step and `fast` two nodes per step, starting both at the head. By the
// time `fast` runs off the end, `slow` has covered exactly half the
// distance `fast` did - which means `slow` is sitting on the middle
// node. Whether `slow` lands on the first or second middle of an
// even-length list falls out of exactly how the loop's stopping
// condition is phrased - see the walkthrough below.
//
//     odd length (5 nodes):   1 -> 2 -> [3] -> 4 -> 5
//       slow: 1  2  3        fast: 1  3  5 (null next) -> stop, slow=3
//
//     even length (4 nodes):  1 -> 2 -> 3 -> [4]
//       slow: 1  2  3  4      fast: 1  3 (null) -> stop, slow=4
//       (fast becomes null exactly when checking fast.next.next for the
//        SECOND of the two middle nodes - see the loop condition)
//
// The stopping condition below is `while fast.is_some() &&
// fast.next.is_some()`: it advances `slow`/`fast` only when `fast` can
// still take a FULL two-step hop. The moment that's no longer possible
// (fast is null, or fast has no next), the loop stops with `slow` on
// the correct middle - already the SECOND middle for even lengths,
// exactly as this problem asks for, with no separate case needed.
//
// Complexity: O(n) time, one pass, O(1) space.

use linked_list::{from_vec, ListNode};

pub fn middle_node(head: Option<Box<ListNode>>) -> Option<Box<ListNode>> {
    // Walk with borrowed references while searching - nothing needs to
    // be taken or mutated to find the middle. Only once it's located do
    // we clone that node onward, since the signature (matching
    // LeetCode's own) returns an owned sub-list, not a borrow.
    let mut slow = head.as_ref();
    let mut fast = head.as_ref();

    while fast.is_some() && fast.unwrap().next.is_some() {
        slow = slow.unwrap().next.as_ref();
        fast = fast.unwrap().next.as_ref().unwrap().next.as_ref();
    }

    slow.cloned()
}

fn main() {
    let list = from_vec(&[1, 2, 3, 4, 5]);
    println!("middle of [1..5]:   {:?}", middle_node(list).map(|n| n.val));

    let list = from_vec(&[1, 2, 3, 4, 5, 6]);
    println!(
        "middle of [1..6]:   {:?} (second of the two middles)",
        middle_node(list).map(|n| n.val)
    );
}

#[cfg(test)]
mod tests {
    use super::*;
    use linked_list::to_vec;

    // Compares the REST of the list from the middle onward, since
    // `middle_node` returns the middle and everything after it (its
    // `next` chain is still intact via `.cloned()`).
    fn middle_values(values: &[i32]) -> Vec<i32> {
        to_vec(&middle_node(from_vec(values)))
    }

    #[test]
    fn odd_length_single_middle() {
        assert_eq!(middle_values(&[1, 2, 3, 4, 5]), vec![3, 4, 5]);
    }

    #[test]
    fn even_length_returns_the_second_middle() {
        assert_eq!(middle_values(&[1, 2, 3, 4, 5, 6]), vec![4, 5, 6]);
    }

    #[test]
    fn two_nodes() {
        assert_eq!(middle_values(&[1, 2]), vec![2]);
    }

    #[test]
    fn single_node() {
        assert_eq!(middle_values(&[1]), vec![1]);
    }
}
