// Problem: LeetCode 142 - Linked List Cycle II.
//
// Given the head of a linked list, return the node where the cycle
// BEGINS (not just whether one exists, as in 141), or null if there is
// no cycle. Same `RawNode` representation as 003, for the same reason -
// see `src/lib.rs`.
//
// ---------------------------------------------------------------------
// PICKING UP WHERE 003 LEFT OFF
// ---------------------------------------------------------------------
// Run the exact same tortoise-and-hare loop from
// 003_linked_list_cycle.rs to find a meeting point INSIDE the cycle (if
// one exists). That answers "is there a cycle," but the meeting point
// itself is usually NOT the start of the cycle - it's just wherever the
// two pointers happened to collide. Finding the actual start needs one
// more piece of reasoning.
//
// ---------------------------------------------------------------------
// THE SECOND PHASE: WHY RESETTING ONE POINTER TO THE HEAD WORKS
// ---------------------------------------------------------------------
// Let `a` = distance from the head to the cycle's start, `b` = distance
// from the cycle's start to the meeting point, and `c` = the remaining
// cycle length back around to the start (so the cycle's total length is
// `b + c`). By the time slow and fast meet: slow has traveled `a + b`
// steps; fast has traveled twice as far, `2(a + b)`, and every step
// fast took beyond `a + b` was spent going around the cycle some whole
// number of extra times. Working through that equality (2(a+b) = a+b +
// k*(b+c) for some whole number of extra laps k) reduces to:
//
//     a = (k-1)(b+c) + c
//
// Read the right side as "some whole number of full laps around the
// cycle, plus `c`." That means walking `a` steps from the HEAD lands on
// the exact same node as walking `c` steps from the MEETING POINT
// (extra full laps don't change which node you're on). And `c` is
// precisely the remaining distance from the meeting point back around
// to the cycle's start. So: reset one pointer to the head, leave the
// other at the meeting point, advance BOTH one step at a time - they
// are now guaranteed to reach the cycle's start at the same moment.
//
// This is the kind of proof worth being able to sketch the shape of
// (two pointers, one relationship, solve for where they must coincide)
// rather than recite from memory - the shape recurs across cycle-
// finding problems generally, not just this one.
//
// Complexity: O(n) time, O(1) space - same budget as 003, one extra
// pass instead of an extra data structure.

use linked_list::{build_raw_chain, RawNode};

pub fn detect_cycle(head: *mut RawNode) -> *mut RawNode {
    let mut slow = head;
    let mut fast = head;

    // Phase 1: find a meeting point inside the cycle, if one exists.
    let meeting_point = loop {
        if fast.is_null() {
            return std::ptr::null_mut(); // no cycle at all
        }
        fast = unsafe { (*fast).next };
        if fast.is_null() {
            return std::ptr::null_mut();
        }
        fast = unsafe { (*fast).next };
        slow = unsafe { (*slow).next };

        if slow == fast {
            break slow;
        }
    };

    // Phase 2: walk one pointer from the head and one from the meeting
    // point, one step each - they converge exactly at the cycle start.
    let mut p1 = head;
    let mut p2 = meeting_point;
    while p1 != p2 {
        p1 = unsafe { (*p1).next };
        p2 = unsafe { (*p2).next };
    }
    p1
}

fn main() {
    // 3 -> 2 -> 0 -> -4 -> back to index 1 (value 2) - cycle starts at
    // value 2.
    let mut nodes = build_raw_chain(&[3, 2, 0, -4]);
    unsafe {
        (*nodes[3]).next = nodes[1];
    }
    let start = detect_cycle(nodes[0]);
    println!("cycle starts at value: {}", unsafe { (*start).val }); // expected: 2
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn cycle_starts_at_second_node() {
        let mut nodes = build_raw_chain(&[3, 2, 0, -4]);
        unsafe {
            (*nodes[3]).next = nodes[1];
        }
        assert_eq!(detect_cycle(nodes[0]), nodes[1]);
    }

    #[test]
    fn cycle_starts_at_the_head_itself() {
        let mut nodes = build_raw_chain(&[1, 2]);
        unsafe {
            (*nodes[1]).next = nodes[0]; // whole list is the cycle
        }
        assert_eq!(detect_cycle(nodes[0]), nodes[0]);
    }

    #[test]
    fn single_node_self_cycle() {
        let mut nodes = build_raw_chain(&[1]);
        unsafe {
            (*nodes[0]).next = nodes[0];
        }
        assert_eq!(detect_cycle(nodes[0]), nodes[0]);
    }

    #[test]
    fn no_cycle_returns_null() {
        let nodes = build_raw_chain(&[1, 2, 3]);
        assert!(detect_cycle(nodes[0]).is_null());
        unsafe {
            linked_list::free_raw_chain(nodes);
        }
    }

    #[test]
    fn empty_list_returns_null() {
        assert!(detect_cycle(std::ptr::null_mut()).is_null());
    }
}
