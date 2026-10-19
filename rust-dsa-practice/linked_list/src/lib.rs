//! Shared node types and test-construction helpers for the linked-list
//! problem set in `src/bin/`.
//!
//! ## Two node types, on purpose - not an accident
//!
//! Most of these problems use [`ListNode`], the representation LeetCode
//! itself uses: `next: Option<Box<ListNode>>`. A `Box` is UNIQUE
//! ownership - exactly one thing in the world owns it, and it is freed
//! the instant its owner is dropped. That maps perfectly onto an
//! ordinary singly linked list, where each node really does have
//! exactly one "owner" (the node before it).
//!
//! It maps **badly** onto two of these problems:
//!
//! - **Cycle detection (141, 142)**: a cycle means some node's `next`
//!   eventually points back to a node that is ALREADY owned by someone
//!   earlier in the chain. `Box` ownership forms a tree (every node has
//!   at most one owner); a cycle is a graph with a back-edge. You
//!   cannot build one out of `Option<Box<ListNode>>` in safe Rust at
//!   all - the compiler will not let two things own the same box, and a
//!   node cannot be its own ancestor's owner.
//! - **Intersection of two lists (160)**: two independently-headed
//!   lists that share a common TAIL - the shared suffix would need to
//!   be owned by both lists' last unique node simultaneously. Same
//!   problem, same reason.
//!
//! Rather than force an awkward `Rc<RefCell<..>>` representation onto
//! every problem just to accommodate these two, this crate uses
//! [`ListNode`] for the nine problems where a tree-shaped owned list is
//! the natural fit, and a second, minimal [`RawNode`] type - built on
//! raw pointers - for the three where the underlying structure is
//! genuinely not a tree. This split is itself the lesson: Rust's
//! ownership model isn't a syntax tax, it's telling you something true
//! about which of these structures IS a tree and which isn't.

// =====================================================================
// ListNode - the standard (tree-shaped, owned) representation
// =====================================================================

#[derive(PartialEq, Eq, Clone, Debug)]
pub struct ListNode {
    pub val: i32,
    pub next: Option<Box<ListNode>>,
}

impl ListNode {
    #[inline]
    pub fn new(val: i32) -> Self {
        ListNode { val, next: None }
    }
}

/// Builds an owned list from a slice, head first.
pub fn from_vec(values: &[i32]) -> Option<Box<ListNode>> {
    let mut head: Option<Box<ListNode>> = None;
    // Build back-to-front so each new node's `next` is already the
    // correctly-linked remainder - the natural direction for `Box`
    // ownership, which always points from a node to what comes after it.
    for &v in values.iter().rev() {
        let mut node = Box::new(ListNode::new(v));
        node.next = head;
        head = Some(node);
    }
    head
}

/// Walks an owned list into a Vec, for asserting against expected output.
pub fn to_vec(mut head: &Option<Box<ListNode>>) -> Vec<i32> {
    let mut out = Vec::new();
    while let Some(node) = head {
        out.push(node.val);
        head = &node.next;
    }
    out
}

// =====================================================================
// RawNode - for cycle detection (141, 142) and intersection (160)
// =====================================================================

/// A node whose links are raw pointers rather than owned `Box`es -
/// deliberately the "unsafe, but honest about it" representation for
/// the two shapes `ListNode` structurally cannot express: a cycle, and
/// two lists sharing a tail. Floyd's cycle-detection algorithm itself
/// never needs to OWN a node, only to compare and follow pointers, so
/// working in raw pointers costs nothing algorithmically - the `unsafe`
/// here is confined to construction/traversal, not the core logic.
#[derive(Debug)]
pub struct RawNode {
    pub val: i32,
    pub next: *mut RawNode,
}

/// Builds a chain of heap-allocated `RawNode`s from `values`, returning
/// raw pointers to every node (index-aligned with `values`) so the
/// caller can wire up a cycle or a shared tail by hand afterward.
/// Leaks intentionally - these are short-lived test binaries, and
/// managing manual frees for a handful of small allocations would add
/// ceremony without teaching anything the leak itself doesn't already
/// make clear: SOMETHING has to own these nodes once ordinary Box
/// ownership no longer applies, and here that something is "nobody,
/// deliberately."
pub fn build_raw_chain(values: &[i32]) -> Vec<*mut RawNode> {
    let mut nodes: Vec<*mut RawNode> = values
        .iter()
        .map(|&val| {
            Box::into_raw(Box::new(RawNode {
                val,
                next: std::ptr::null_mut(),
            }))
        })
        .collect();

    for i in 0..nodes.len().saturating_sub(1) {
        unsafe {
            (*nodes[i]).next = nodes[i + 1];
        }
    }

    // Reborrow so the returned pointers are distinct from `nodes`'
    // internal storage location, which is about to be dropped - the
    // pointers themselves (addresses of the heap-allocated nodes) stay
    // valid, since Vec dropping only frees ITS OWN buffer, not what the
    // pointers inside it point to.
    std::mem::take(&mut nodes)
}

/// Frees a chain built by [`build_raw_chain`]. Call this only on a
/// non-cyclic, non-shared chain - walking off the end of a cycle or
/// double-freeing a shared tail is exactly the class of bug raw
/// pointers reintroduce, which is the whole reason `ListNode` is the
/// default for every problem that doesn't need this.
///
/// # Safety
/// Every pointer in `nodes` must have come from `Box::into_raw` (as
/// `build_raw_chain` guarantees), must not already have been freed, and
/// must not be part of a cycle or shared with another still-live chain.
pub unsafe fn free_raw_chain(nodes: Vec<*mut RawNode>) {
    for p in nodes {
        unsafe {
            drop(Box::from_raw(p));
        }
    }
}
