// Binary search tree: recursive insert and search.
//
// This is a beginner-friendly rewrite of 001_bst.rs, trading generality
// for readability:
//   - Fixed to i32 instead of generic <T: Ord> - one less concept to hold
//     in your head while learning the tree logic itself.
//   - Every branch uses plain if/else and match - no combinator chains
//     (.as_ref().map().unwrap_or(), etc.) like 001_bst.rs's `contains`.
//   - No #[test] module - just a `main` that inserts some values and
//     prints what `contains` finds, so you can read top-to-bottom and see
//     output directly instead of jumping to a separate test block.
//
// See docs/binary-search-tree-rust-syntax-notes.md for a deep dive into
// generics, Box, and Option/combinator syntax if you want the full
// picture later - this file intentionally skips over that ceremony.

// A node in the tree. Every node owns two optional children:
//   - `left` holds all values SMALLER than `val`
//   - `right` holds all values LARGER than `val`
// This "smaller left, larger right" rule is the entire BST invariant -
// everything else in this file just walks the tree while obeying it.
struct Node {
    val: i32,
    left: Option<Box<Node>>,
    right: Option<Box<Node>>,
}

impl Node {
    // Make a new node with no children yet.
    fn new(val: i32) -> Self {
        Node { val, left: None, right: None }
    }

    // Insert `val` somewhere under this node, keeping the BST invariant.
    //
    // Walk down: if `val` is smaller, it belongs in the left subtree; if
    // bigger, the right subtree. Keep walking in that direction until we
    // fall off the tree (hit a `None`), then plant the new node there.
    fn insert(&mut self, val: i32) {
        if val < self.val {
            // val belongs on the left. Is there already a left child?
            match &mut self.left {
                // Yes - there's more tree down there, so hand the
                // insert off to that child and let IT decide where
                // val goes next (same logic, one level deeper).
                Some(left_child) => left_child.insert(val),
                // No - we've found the empty spot. Plant a new node here.
                None => self.left = Some(Box::new(Node::new(val))),
            }
        } else if val > self.val {
            // Mirror image of the left case, but for the right subtree.
            match &mut self.right {
                Some(right_child) => right_child.insert(val),
                None => self.right = Some(Box::new(Node::new(val))),
            }
        }
        // if val == self.val: it's already in the tree, do nothing.
    }

    // Search for `val` starting at this node. Returns true if found.
    //
    // Same "smaller -> left, bigger -> right" walk as insert, except
    // instead of planting a new node when we run out of tree, running
    // out of tree means the value just isn't here.
    fn contains(&self, val: i32) -> bool {
        if val == self.val {
            return true;
        }

        if val < self.val {
            // Look on the left, if there is a left.
            match &self.left {
                Some(left_child) => left_child.contains(val),
                None => false, // ran out of tree, val isn't in it
            }
        } else {
            // Look on the right, if there is a right.
            match &self.right {
                Some(right_child) => right_child.contains(val),
                None => false,
            }
        }
    }
}

fn main() {
    // Build this tree by inserting in this order:
    //
    //         5
    //        / \
    //       2   8
    //      /     \
    //     1       9
    //
    let mut root = Node::new(5);
    root.insert(2);
    root.insert(8);
    root.insert(1);
    root.insert(9);

    for val in [5, 1, 9, 100, 0] {
        println!("contains({}) = {}", val, root.contains(val));
    }
}
