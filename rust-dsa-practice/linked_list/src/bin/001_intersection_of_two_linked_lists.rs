// Problem: LeetCode 160 - Intersection of Two Linked Lists.
//
// Given the heads of two singly linked lists, return the node at which
// they intersect - meaning they share a common TAIL (the same nodes by
// identity, not just equal values) - or a null/None if they never meet.
//
// ---------------------------------------------------------------------
// WHY THE OBVIOUS OWNED REPRESENTATION (ListNode) DOESN'T FIT
// ---------------------------------------------------------------------
// "Intersecting" here means two DIFFERENT head pointers eventually walk
// into the SAME sequence of nodes - the shared suffix is one piece of
// memory reachable from two independent starting points. `Box`
// ownership cannot express that: a `Box<ListNode>` has exactly one
// owner, so it is structurally impossible for two lists to legitimately
// share a tail of `Box`-owned nodes. This is exactly the reasoning
// documented on `RawNode` in `src/lib.rs` - this problem needs raw
// pointers for the same underlying reason cycle detection does: the
// true shape here isn't a tree.
//
// ---------------------------------------------------------------------
// WHY THE OBVIOUS APPROACH IS AWKWARD
// ---------------------------------------------------------------------
// "For every node in A, scan all of B looking for a pointer match" is
// O(n*m) and touches B repeatedly for no reason. "Put every node of A
// in a HashSet, then walk B checking membership" is O(n+m) time but
// pays O(n) extra space for the set - workable, but there's a genuinely
// nicer O(1)-space idea available here.
//
// ---------------------------------------------------------------------
// THE TWO-POINTER TRICK: WALK OFF THE END, THEN SWITCH LISTS
// ---------------------------------------------------------------------
// If list A has length `a` before the intersection and list B has
// length `b` before it, the two lists only differ in that "before the
// intersection" stretch - after the intersection point they're
// identical. The trick equalizes that difference for free: walk pointer
// pA down A, and when it hits the end, redirect it to B's HEAD (not
// null) and keep going; do the mirror thing for pB with A's head. Each
// pointer now travels exactly `a + b` total steps to reach the
// intersection (or the end, if there is none) - the redirect makes up
// exactly the length difference between the two lists, so both pointers
// arrive at the intersection node on the SAME step, without ever
// computing either length explicitly.
//
//     A: a1 -> a2 -> a3 \
//                         c1 -> c2 -> c3 -> null
//     B: b1 -> b2 -------/
//
//     pA: a1 a2 a3 c1 c2 c3 (null->B) b1 b2 c1  <- meets here, step 9
//     pB: b1 b2 c1 c2 c3 (null->A) a1 a2 a3 c1  <- meets here, step 9
//
// If the lists never intersect, both pointers still traverse `a + b`
// steps total and reach null AT THE SAME TIME (each having walked down
// both full lists once), which is exactly the "no intersection" answer
// falling out of the same loop with no special case needed.
//
// Complexity: O(a + b) time, O(1) extra space - the entire benefit over
// the hash-set approach.

use linked_list::{build_raw_chain, free_raw_chain, RawNode};

pub fn get_intersection_node(head_a: *mut RawNode, head_b: *mut RawNode) -> *mut RawNode {
    let mut p_a = head_a;
    let mut p_b = head_b;

    // Both pointers travel a+b steps total; if there's no intersection,
    // they both land on null on the very same step, ending the loop.
    while p_a != p_b {
        p_a = if p_a.is_null() {
            head_b
        } else {
            unsafe { (*p_a).next }
        };
        p_b = if p_b.is_null() {
            head_a
        } else {
            unsafe { (*p_b).next }
        };
    }

    p_a // either the shared node, or null (they're equal either way)
}

fn main() {
    // Shared tail c1 -> c2 -> c3, with A and B each having their own
    // private prefix before joining it.
    let tail = build_raw_chain(&[8, 4, 5]);
    let a_prefix = build_raw_chain(&[4, 1]);
    let b_prefix = build_raw_chain(&[5, 6, 1]);

    let a_last = a_prefix[a_prefix.len() - 1];
    let b_last = b_prefix[b_prefix.len() - 1];
    unsafe {
        (*a_last).next = tail[0];
        (*b_last).next = tail[0];
    }

    let result = get_intersection_node(a_prefix[0], b_prefix[0]);
    let value = if result.is_null() {
        None
    } else {
        Some(unsafe { (*result).val })
    };
    println!("intersection value: {value:?}"); // expected: Some(8)

    // Clean up: the shared tail is owned by both prefixes now, so free
    // each side exactly once.
    unsafe {
        free_raw_chain(a_prefix);
        free_raw_chain(b_prefix);
        free_raw_chain(tail);
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn lists_of_different_lengths_intersect() {
        let tail = build_raw_chain(&[8, 4, 5]);
        let a_prefix = build_raw_chain(&[4, 1]);
        let b_prefix = build_raw_chain(&[5, 6, 1]);
        let a_last = a_prefix[a_prefix.len() - 1];
        let b_last = b_prefix[b_prefix.len() - 1];
        unsafe {
            (*a_last).next = tail[0];
            (*b_last).next = tail[0];
        }

        let result = get_intersection_node(a_prefix[0], b_prefix[0]);
        assert_eq!(unsafe { (*result).val }, 8);
        // Identity, not just value equality - it must be the literal
        // shared node.
        assert_eq!(result, tail[0]);

        unsafe {
            free_raw_chain(a_prefix);
            free_raw_chain(b_prefix);
            free_raw_chain(tail);
        }
    }

    #[test]
    fn no_intersection_returns_null() {
        let a = build_raw_chain(&[2, 6, 4]);
        let b = build_raw_chain(&[1, 5]);

        let result = get_intersection_node(a[0], b[0]);
        assert!(result.is_null());

        unsafe {
            free_raw_chain(a);
            free_raw_chain(b);
        }
    }

    #[test]
    fn one_list_entirely_contains_the_other_from_the_head() {
        // B's head IS the intersection point - a full overlap.
        let shared = build_raw_chain(&[1, 2, 3]);
        let a_prefix = build_raw_chain(&[9, 9]);
        let a_last = a_prefix[a_prefix.len() - 1];
        unsafe {
            (*a_last).next = shared[0];
        }

        let result = get_intersection_node(a_prefix[0], shared[0]);
        assert_eq!(result, shared[0]);

        unsafe {
            free_raw_chain(a_prefix);
            free_raw_chain(shared);
        }
    }

    #[test]
    fn empty_lists_return_null() {
        let result = get_intersection_node(std::ptr::null_mut(), std::ptr::null_mut());
        assert!(result.is_null());
    }
}
