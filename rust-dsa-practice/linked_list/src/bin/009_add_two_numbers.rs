// Problem: LeetCode 2 - Add Two Numbers.
//
// Two numbers are given as linked lists, each digit a node, stored in
// REVERSE order (the ones digit is the head) - e.g. 342 is represented
// as 2 -> 4 -> 3. Add the two numbers and return the sum, in the same
// reversed-digit representation.
//
// ---------------------------------------------------------------------
// WHY "REVERSE ORDER" IS A GIFT, NOT AN OBSTACLE
// ---------------------------------------------------------------------
// This is exactly how you add two numbers by hand on paper - ones digit
// first, carrying into the next column - except long addition starts
// from the RIGHTMOST (least significant) digit, which for a normal
// left-to-right written number means starting from the END. Storing the
// least-significant digit at the HEAD means the list is already in
// "the order arithmetic actually wants to process it" - no reversing,
// no recursion-to-reach-the-end, just walk forward through both lists
// at once, exactly like adding two columns of digits on paper.
//
// ---------------------------------------------------------------------
// THE ALGORITHM: DIGIT-BY-DIGIT, CARRYING FORWARD
// ---------------------------------------------------------------------
// Walk both lists together. At each position: sum the two digits (0 if
// one list has run out - the lists can have different lengths) plus
// whatever carried in from the previous position. The digit to emit is
// that sum mod 10; the new carry is that sum divided by 10 (integer
// division - it's always 0 or 1, since two digits 0-9 plus a carry of
// at most 1 never exceeds 19). Stop once BOTH lists are exhausted AND
// there's no carry left to emit - a trailing carry (e.g. 5 + 5 = 10)
// needs one more digit that neither input list has a node for.
//
//     342 + 465  (stored as 2->4->3  and  5->6->4)
//     pos 0: 2+5+0=7   -> emit 7, carry 0
//     pos 1: 4+6+0=10  -> emit 0, carry 1
//     pos 2: 3+4+1=8   -> emit 8, carry 0
//     result: 7 -> 0 -> 8   (= 807, correct: 342+465=807)
//
// Complexity: O(max(n, m)) time - one pass, bounded by the longer
// input - O(max(n, m)) space for the output list (unavoidable - the
// output IS a linked list of comparable length).

use linked_list::{from_vec, to_vec, ListNode};

pub fn add_two_numbers(
    mut l1: Option<Box<ListNode>>,
    mut l2: Option<Box<ListNode>>,
) -> Option<Box<ListNode>> {
    let mut dummy = Box::new(ListNode::new(0));
    let mut tail = &mut dummy;
    let mut carry = 0;

    while l1.is_some() || l2.is_some() || carry != 0 {
        let d1 = l1.as_ref().map_or(0, |n| n.val);
        let d2 = l2.as_ref().map_or(0, |n| n.val);

        let sum = d1 + d2 + carry;
        carry = sum / 10;

        tail.next = Some(Box::new(ListNode::new(sum % 10)));
        tail = tail.next.as_mut().unwrap();

        l1 = l1.and_then(|n| n.next);
        l2 = l2.and_then(|n| n.next);
    }

    dummy.next
}

fn main() {
    // 342 + 465 = 807
    let l1 = from_vec(&[2, 4, 3]);
    let l2 = from_vec(&[5, 6, 4]);
    println!("342 + 465 -> {:?}", to_vec(&add_two_numbers(l1, l2)));
}

#[cfg(test)]
mod tests {
    use super::*;

    fn check(a: &[i32], b: &[i32], expected: &[i32]) {
        assert_eq!(to_vec(&add_two_numbers(from_vec(a), from_vec(b))), expected);
    }

    #[test]
    fn example_1_no_final_carry() {
        check(&[2, 4, 3], &[5, 6, 4], &[7, 0, 8]); // 342 + 465 = 807
    }

    #[test]
    fn example_2_all_zeros() {
        check(&[0], &[0], &[0]);
    }

    // A carry that ripples all the way through and produces one MORE
    // digit than either input - the "keep going while carry != 0" loop
    // condition, not just "while either list has nodes," is what this
    // guards against.
    #[test]
    fn carry_propagates_into_a_new_leading_digit() {
        // 9999999 + 9999 = 10009998
        check(
            &[9, 9, 9, 9, 9, 9, 9],
            &[9, 9, 9, 9],
            &[8, 9, 9, 9, 0, 0, 0, 1],
        );
    }

    #[test]
    fn different_lengths() {
        // 1 + 999 = 1000
        check(&[1], &[9, 9, 9], &[0, 0, 0, 1]);
    }

    #[test]
    fn simple_carry_at_the_final_position() {
        // 5 + 5 = 10
        check(&[5], &[5], &[0, 1]);
    }
}
