// Problem: LeetCode 141 - Linked List Cycle.
//
// Given the head of a linked list, determine whether it contains a
// cycle (some node's `next` eventually points back to an earlier node
// in the list, so following `next` forever never reaches a null end).
//
// See `src/lib.rs` for why this problem uses `RawNode` (raw pointers)
// rather than the usual `ListNode` (`Box`-owned): a cycle means a node
// is reachable from an earlier "owner," which `Box`'s unique-ownership
// model cannot represent at all.
//
// ---------------------------------------------------------------------
// WHY THE OBVIOUS APPROACH IS AWKWARD
// ---------------------------------------------------------------------
// "Keep a HashSet of every node visited; if you see one twice, it's a
// cycle" works, and it's O(n) time - but it pays O(n) EXTRA space for
// the set, for a question that only needs a yes/no answer. There is an
// O(1)-space way to answer the same question, and it's one of the
// handful of "just know this" classic algorithms.
//
// ---------------------------------------------------------------------
// FLOYD'S TORTOISE AND HARE
// ---------------------------------------------------------------------
// Walk two pointers from the head: `slow` advances one node per step,
// `fast` advances two. If the list is acyclic, `fast` simply reaches
// the end first (null) and you're done - no cycle. If there IS a
// cycle, `fast` enters it first, and once BOTH pointers are inside the
// cycle, `fast` is gaining on `slow` by exactly one node per step (it
// moves 2, slow moves 1, net gain 1) - on a finite loop, a pointer
// gaining ground by 1 each step is GUARANTEED to eventually land on the
// exact same node as the one it's chasing, the same way a faster runner
// on a circular track eventually laps a slower one. They cannot skip
// past each other by exactly landing on the same node, because the gap
// between them shrinks by exactly 1 every step - it must hit 0 at some
// point, not jump over it.
//
//     no cycle:  fast reaches null -> false
//
//     cycle:     head -> 1 -> 2 -> 3 -> 4
//                              ^         |
//                              +---------+
//                slow: 1  2  3  4  3  4  3   <- meets fast here
//                fast: 2  4  3  3  ...
//                (fast enters the loop first, then gets lapped by the
//                 closing gap, then they coincide)
//
// Complexity: O(n) time, O(1) space - the entire benefit over the
// hash-set version.

use linked_list::{build_raw_chain, RawNode};

pub fn has_cycle(head: *mut RawNode) -> bool {
    let mut slow = head;
    let mut fast = head;

    loop {
        if fast.is_null() {
            return false;
        }
        fast = unsafe { (*fast).next };
        if fast.is_null() {
            return false;
        }
        fast = unsafe { (*fast).next };
        slow = unsafe { (*slow).next };

        if slow == fast {
            return true;
        }
    }
}

fn main() {
    // 3 -> 2 -> 0 -> -4 -> (back to node index 1, value 2)
    let mut nodes = build_raw_chain(&[3, 2, 0, -4]);
    unsafe {
        (*nodes[3]).next = nodes[1]; // wire the cycle: tail points back to index 1
    }
    println!("has_cycle: {}", has_cycle(nodes[0])); // expected: true

    // Deliberately not freeing `nodes` here - it's a genuine cycle, and
    // `free_raw_chain` (a linear walk) would either double-free or loop
    // forever on one; see `src/lib.rs`'s note on why that helper is
    // documented as unsafe to call on non-acyclic chains.
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn cycle_back_to_second_node() {
        let mut nodes = build_raw_chain(&[3, 2, 0, -4]);
        unsafe {
            (*nodes[3]).next = nodes[1];
        }
        assert!(has_cycle(nodes[0]));
    }

    #[test]
    fn cycle_of_length_one_node_points_to_itself() {
        let mut nodes = build_raw_chain(&[1]);
        unsafe {
            (*nodes[0]).next = nodes[0];
        }
        assert!(has_cycle(nodes[0]));
    }

    #[test]
    fn no_cycle_plain_list() {
        let nodes = build_raw_chain(&[1, 2]);
        assert!(!has_cycle(nodes[0]));
        unsafe {
            linked_list::free_raw_chain(nodes);
        }
    }

    #[test]
    fn empty_list_has_no_cycle() {
        assert!(!has_cycle(std::ptr::null_mut()));
    }

    #[test]
    fn single_node_no_cycle() {
        let nodes = build_raw_chain(&[1]);
        assert!(!has_cycle(nodes[0]));
        unsafe {
            linked_list::free_raw_chain(nodes);
        }
    }
}
