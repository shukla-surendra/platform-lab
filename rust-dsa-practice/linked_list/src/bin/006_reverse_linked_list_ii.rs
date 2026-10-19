// Problem: LeetCode 92 - Reverse Linked List II.
//
// Given a list and two 1-indexed positions `left <= right`, reverse
// only the nodes from position `left` to `right`, in place, and return
// the (possibly unchanged) head.
//
// ---------------------------------------------------------------------
// WHY THIS ISN'T JUST 206 WITH EXTRA BOOKKEEPING
// ---------------------------------------------------------------------
// The genuinely new difficulty versus 005_reverse_linked_list.rs (206,
// whole-list reversal) is the two SEAMS: the node just before the
// reversed section needs its `next` re-pointed at what will become the
// new start of that section, and the node that was originally FIRST in
// the section (which ends up LAST after reversing) needs its `next`
// re-pointed at whatever comes after the section. Get either seam
// wrong and the front or back half of the list silently falls off -
// this is a problem where "the algorithm is right but a pointer is one
// node off" is the dominant failure mode, so the seams deserve to be
// handled as their own explicit step, not interleaved with the
// reversal itself.
//
// ---------------------------------------------------------------------
// THE STRATEGY: DETACH, REVERSE STANDALONE, RE-SPLICE
// ---------------------------------------------------------------------
// Rather than reversing in place while simultaneously tracking both
// seams (tempting, but easy to get subtly wrong - an earlier draft of
// this exact file did, by letting the "still needs its next taken"
// pointer silently drift to the wrong node after the first swap),
// separate the concerns completely:
//
//   1. Walk to `before`, the node just preceding position `left` (a
//      dummy node standing in for "before" when left == 1 - see
//      002_merge_two_sorted_lists.rs for the same trick, used for the
//      same reason: it removes a head-of-list special case).
//   2. Detach the whole `[left..=right]` section as its OWN standalone
//      chain, and separately detach `rest` (everything after position
//      `right`) from the end of it.
//   3. Reverse the now-standalone section with the exact same
//      three-pointer walk as 206 - it's a complete, ordinary list at
//      this point, so nothing about that reversal needs to know it was
//      ever part of something bigger.
//   4. Re-splice both seams: `before.next` = the reversed section's new
//      head; the reversed section's new TAIL (found by walking to the
//      end) `.next` = `rest`.
//
// Complexity: O(n) time - each of the four steps is a single linear
// walk bounded by the list's length - O(1) extra space, since every
// node is relinked in place, never copied.

use linked_list::{from_vec, to_vec, ListNode};

pub fn reverse_between(
    head: Option<Box<ListNode>>,
    left: i32,
    right: i32,
) -> Option<Box<ListNode>> {
    let mut dummy = Box::new(ListNode::new(0));
    dummy.next = head;

    // Step 1: find the node just before the section.
    let mut before = &mut dummy;
    for _ in 0..left - 1 {
        before = before.next.as_mut().unwrap();
    }

    // Step 2: detach the section, then detach `rest` from its far end.
    let mut section = before.next.take();
    let mut cursor = section.as_mut().unwrap();
    for _ in 0..right - left {
        cursor = cursor.next.as_mut().unwrap();
    }
    let rest = cursor.next.take();

    // Step 3: reverse the now-standalone section - identical to 206.
    let mut reversed: Option<Box<ListNode>> = None;
    while let Some(mut node) = section {
        section = node.next.take();
        node.next = reversed;
        reversed = Some(node);
    }

    // Step 4: re-splice. Walk to the reversed section's new tail (the
    // original first node of the section) to reattach `rest`.
    let mut tail = reversed.as_mut().unwrap();
    while tail.next.is_some() {
        tail = tail.next.as_mut().unwrap();
    }
    tail.next = rest;
    before.next = reversed;

    dummy.next
}

// =====================================================================
// LeetCode signature adapter
// =====================================================================
pub fn reverse_between_leetcode(
    head: Option<Box<ListNode>>,
    left: i32,
    right: i32,
) -> Option<Box<ListNode>> {
    reverse_between(head, left, right)
}

fn main() {
    let list = from_vec(&[1, 2, 3, 4, 5]);
    println!("reversed [2,4]: {:?}", to_vec(&reverse_between(list, 2, 4)));
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn example_1_middle_section() {
        assert_eq!(
            to_vec(&reverse_between(from_vec(&[1, 2, 3, 4, 5]), 2, 4)),
            vec![1, 4, 3, 2, 5]
        );
    }

    // left == 1: the reversed section touches the head, exercising the
    // "before is the dummy" path specifically.
    #[test]
    fn section_starts_at_the_head() {
        assert_eq!(
            to_vec(&reverse_between(from_vec(&[1, 2, 3, 4, 5]), 1, 3)),
            vec![3, 2, 1, 4, 5]
        );
    }

    // right == len: the reversed section touches the tail, exercising
    // the "rest is None" path.
    #[test]
    fn section_ends_at_the_tail() {
        assert_eq!(
            to_vec(&reverse_between(from_vec(&[1, 2, 3, 4, 5]), 3, 5)),
            vec![1, 2, 5, 4, 3]
        );
    }

    #[test]
    fn left_equals_right_is_a_no_op() {
        assert_eq!(
            to_vec(&reverse_between(from_vec(&[1, 2, 3]), 2, 2)),
            vec![1, 2, 3]
        );
    }

    #[test]
    fn whole_list_is_the_section() {
        assert_eq!(
            to_vec(&reverse_between(from_vec(&[1, 2, 3, 4]), 1, 4)),
            vec![4, 3, 2, 1]
        );
    }

    #[test]
    fn single_node_list() {
        assert_eq!(to_vec(&reverse_between(from_vec(&[5]), 1, 1)), vec![5]);
    }
}
