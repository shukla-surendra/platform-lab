// Binary search tree: recursive insert and lookup for ordered values.
#[derive(Debug)]
struct Node<T: Ord> {
    val: T,
    left: Option<Box<Node<T>>>,
    right: Option<Box<Node<T>>>,
}

impl<T: Ord> Node<T> {
    fn new(val: T) -> Self {
        Node { val, left: None, right: None }
    }

    // BST invariant: smaller values go left, larger go right; walk down until
    // we hit an empty slot, then place the new node there.
    fn insert(&mut self, val: T) {
        if val < self.val {
            match self.left {
                Some(ref mut l) => l.insert(val),
                None => self.left = Some(Box::new(Node::new(val))),
            }
        } else if val > self.val {
            match self.right {
                Some(ref mut r) => r.insert(val),
                None => self.right = Some(Box::new(Node::new(val))),
            }
        }
    }

    // Same left/right invariant as insert(): each comparison eliminates
    // one whole subtree, giving O(log n) lookup on a balanced tree.
    fn contains(&self, val: T) -> bool {
        if val == self.val { return true; }
        if val < self.val {
            self.left.as_ref().map(|l| l.contains(val)).unwrap_or(false)
        } else {
            self.right.as_ref().map(|r| r.contains(val)).unwrap_or(false)
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn bst_insert_and_search() {
        let mut root = Node::new(5);
        root.insert(2);
        root.insert(8);
        root.insert(1);
        root.insert(7);

        assert!(root.contains(5));
        assert!(root.contains(1));
        assert!(root.contains(7));
        assert!(!root.contains(100));
        assert!(!root.contains(0));
    }
}
