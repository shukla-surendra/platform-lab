#!/usr/bin/env python3
"""LeetCode 206 - Reverse Linked List, recursive solution.

    python3 005_reverse_linked_list.py

This is a WORKED reference, not a scaffold - the Rust version
(005_reverse_linked_list.rs, sitting next to this file) is the one
you're actually meant to write yourself. Python has no borrow checker,
so the recursion here is exactly the algorithm with none of the
ownership bookkeeping Rust forces on you - useful for confirming your
mental model before fighting `.take()` and `Option<Box<..>>` in Rust.
The mapping, once you're stuck there:

    Python                          Rust
    ---------------------------     ------------------------------------
    head.next  (just a reference)   current.next.take()  (must MOVE the
                                     value out before you can use it, or
                                     the old owner still "holds" it)
    head.next.next = head           head.next = Some(prev)  after prev
                                     has been reassigned to the previous
                                     node
"""

# ===========================================================================
# THE SOLUTION
# ===========================================================================


class ListNode:
    def __init__(self, val, next=None):
        self.val = val
        self.next = next


def reverse_list(head: ListNode | None) -> ListNode | None:
    """Reverse a singly linked list and return the new head.

    Base case: 0 or 1 nodes is already its own reversal.

    Otherwise: recursively reverse everything AFTER head first.
    `new_head` comes back as the correct head of that reversed
    sub-list - but `head.next` still points FORWARD, at the node that
    is now the LAST node of that reversed sub-list. Two things fix
    that: point that now-last node's `.next` back at `head` (grafting
    head onto the tail), then clear `head.next` so head - now the true
    tail - doesn't also still point forward and create a cycle.
    """
    if head is None or head.next is None:
        return head

    new_head = reverse_list(head.next)

    head.next.next = head
    head.next = None

    return new_head


# ===========================================================================
# TEST DATA AND RUNNER
# ===========================================================================


def from_list(values: list[int]) -> ListNode | None:
    head = None
    for v in reversed(values):
        head = ListNode(v, head)
    return head


def to_list(head: ListNode | None) -> list[int]:
    out = []
    while head:
        out.append(head.val)
        head = head.next
    return out


CASES: list[tuple[str, list[int], list[int]]] = [
    ("example: five nodes", [1, 2, 3, 4, 5], [5, 4, 3, 2, 1]),
    ("two nodes", [1, 2], [2, 1]),
    ("single node is its own reverse", [1], [1]),
    ("empty list", [], []),
]


def main() -> int:
    failed = 0
    for name, values, expected in CASES:
        got = to_list(reverse_list(from_list(values)))
        status = "ok  " if got == expected else "FAIL"
        if got != expected:
            failed += 1
        print(f"  {status} {name:<28} {values} -> {got}  (want {expected})")

    print(f"\n  {len(CASES) - failed}/{len(CASES)} passed")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
