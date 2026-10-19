# Rust syntax notes - `binary_search_tree` crate

Running notes on Rust language features encountered while solving problems
in this crate, for reference. (See also
[recursion-rust-syntax-notes.md](recursion-rust-syntax-notes.md) for
`match` and `todo!()`, and
[dynamic-programming-rust-syntax-notes.md](dynamic-programming-rust-syntax-notes.md),
and
[arrays-hashing-rust-syntax-notes.md](arrays-hashing-rust-syntax-notes.md).)

## `001_bst.rs`

```rust
#[derive(Debug)]
struct Node<T: Ord> {
    val: T,
    left: Option<Box<Node<T>>>,
    right: Option<Box<Node<T>>>,
}
```

### `#[derive(Debug)]` - the `Debug` trait

An *attribute* that auto-generates an implementation of the `Debug` trait
for `Node`. That's what lets a value be printed with the `{:?}` formatter
(e.g. in `println!("{:?}", node)`, or automatically in a failed `assert!`
message). Without it, `Node` has no way to be turned into text - `Debug`
isn't implemented for arbitrary structs by default, since Rust doesn't
assume every type should be printable.

`Debug` is meant for developer-facing output (debugging, logs, test
failures) - it's `#[derive]`-able because the compiler can mechanically
generate a reasonable dump of any struct's fields. Contrast with the
`Display` trait (not used in this file), which is for user-facing output
(what `{}` uses in `println!`) and is deliberately *not* derivable -
there's no sensible default for "how should this look to an end user," so
every type has to opt in with a hand-written `impl Display`.

### `struct Node<T: Ord>` - trait bounds, and the `Ord` trait

A *generic* struct. `T` is a placeholder type parameter - `Node` doesn't
commit to holding, say, `u32`; it can be `Node<u32>`, `Node<String>`,
`Node<char>`, etc., and the same struct/method definitions work for all of
them. `T: Ord` is a *trait bound*: it restricts `T` to types that
implement `Ord`. This bound is required because `insert`/`contains`
compare values with `<`/`>` - without it, the compiler would reject those
comparisons since an unconstrained `T` might not support them.

`Ord` itself means "this type has a *total* ordering" - every pair of
values is comparable, and one is definitively less than, equal to, or
greater than the other. It builds on two smaller traits:

- **`PartialEq`** - defines `==` and `!=`.
- **`PartialOrd`** - defines `<`, `>`, `<=`, `>=`, but allows pairs that
  are *incomparable* (its comparison method returns `Option<Ordering>`,
  where `None` means "can't say"). `f64`/`f32` are the standard example:
  they implement `PartialOrd` but `NaN < 1.0`, `NaN > 1.0`, and
  `NaN == 1.0` are all `false` - `NaN` is incomparable to everything,
  including itself.
- **`Eq`** - a marker (no new methods) on top of `PartialEq` promising
  equality is *reflexive* (`x == x` always holds - true for `i32`, not
  true for `NaN` under IEEE 754, which is why floats don't implement it).

`Ord` requires both `Eq` and `PartialOrd`, and adds `cmp(&self, other: &Self)
-> Ordering` (returning `Less`/`Equal`/`Greater`, no `Option` - always a
definite answer). That's the whole point of using `Ord` as the bound here
instead of `PartialOrd`: it guarantees `val < self.val` always has a real
answer. `f64` deliberately doesn't implement `Ord` - if `Node<T: Ord>` had
used `PartialOrd` instead, someone could build a `Node<f64>`, insert a
`NaN`, and get an incomparable value silently corrupting the tree's
left/right invariant (it wouldn't reliably belong on either side).
Requiring `Ord` rules that out at compile time - `Node<f64>` simply
doesn't compile.

Types that already implement `Ord` and can be used as-is: `i32`, `u32`,
`char`, `String`, `bool`, and any `enum`/`struct` with `#[derive(Ord,
PartialOrd, Eq, PartialEq)]` (all four are usually derived together, since
`Ord` needs the other three).

### `Option<Box<Node<T>>>`

Two mechanisms stacked on top of each other:

- **`Box<Node<T>>`** - a heap-allocated pointer to a `Node`. Needed because
  `Node` contains itself (a node's children are more `Node`s of the same
  type). If `left`/`right` held a bare `Node<T>` instead of a `Box`, the
  compiler couldn't compute `Node`'s size - it would need to know the size
  of a `Node`, which needs the size of *its* `left`/`right` `Node`, forever
  (infinite recursion in the type's layout). `Box` breaks the cycle: it's
  always a fixed-size pointer, regardless of what it points to, so the
  outer `Node` has a well-defined size.
- **`Option<...>`** - a child may or may not exist. Rust has no `null`;
  instead, "a value that might be absent" is spelled out explicitly as
  `Option<T>` with two variants, `Some(value)` and `None`. This means the
  compiler forces every access to handle the "no child here" case (via
  `match`, `.map()`, `.unwrap_or()`, etc.) - you can't accidentally
  dereference a missing child the way you could accidentally dereference
  a null pointer in other languages.

### `impl<T: Ord> Node<T> { ... }`

An `impl` block attaches methods to a type. The `<T: Ord>` here mirrors the
struct's own generic parameter and bound - it says "for any `T` that
implements `Ord`, here are the methods `Node<T>` gets."

### `fn new(val: T) -> Self`

```rust
fn new(val: T) -> Self {
    Node { val, left: None, right: None }
}
```

`Self` is shorthand for "the type this `impl` block is for" - here,
`Node<T>`. Using `Self` instead of spelling out `Node<T>` again means the
code stays correct even if the type's name or generics change later.

`Node { val, left: None, right: None }` uses *field init shorthand*: since
there's a local variable/parameter named `val` and a field also named
`val`, writing just `val` is sugar for `val: val`. (`left: None` still
needs the full `field: value` form since the field name and the value
being assigned don't match.)

### `fn insert(&mut self, val: T)`

`&mut self` means this method borrows the `Node` it's called on
*mutably* - it's allowed to modify `self`'s fields (needed here, since
`insert` writes into `self.left`/`self.right`). Compare with
`fn contains(&self, val: T) -> bool`, which only reads and so takes an
immutable borrow `&self` - the signature itself documents whether a method
can mutate.

```rust
match self.left {
    Some(ref mut l) => l.insert(val),
    None => self.left = Some(Box::new(Node::new(val))),
}
```

- `Some(ref mut l)` - a pattern that, instead of *moving* the `Box` out of
  `self.left` (which isn't allowed here - `self` is only borrowed, not
  owned, so nothing can be moved out of it), binds `l` as a mutable
  reference reaching *into* the existing `Some`. `l.insert(val)` then
  recurses one level down the tree through that reference.
- `None => self.left = Some(Box::new(Node::new(val)))` - the base case:
  there's no child yet, so allocate a new node on the heap (`Box::new`)
  and place it in the empty slot.

Note there's no `else` branch for `val == self.val` in the surrounding
`if`/`else if` - inserting a duplicate is silently a no-op.

### `fn contains(&self, val: T) -> bool`

```rust
self.left.as_ref().map(|l| l.contains(val)).unwrap_or(false)
```

The same "recurse into a child that might not exist" logic as `insert`,
but written as a combinator chain instead of a `match`:

- `.as_ref()` - turns `&Option<Box<Node<T>>>` into `Option<&Box<Node<T>>>`,
  borrowing the contents rather than trying to move them out (same
  motivation as `ref mut` above, just for reading instead of writing).
- `.map(|l| l.contains(val))` - if the `Option` is `Some`, runs the
  closure on the inner value and wraps the result back in `Some`; if
  `None`, short-circuits to `None` without running the closure. Here it
  recurses into the child, producing `Option<bool>` - `Some(true)`,
  `Some(false)`, or `None` (no child to check).
- `.unwrap_or(false)` - unwraps a `Some(bool)` to the `bool` inside;
  if it was `None`, uses the fallback `false` instead - "no child there"
  correctly means "value not found."

`match` and this combinator style are both idiomatic Rust for the same
job; the combinator form reads more compactly once `Option`'s methods are
familiar, at the cost of being a bit more implicit about the control flow
than a `match`'s explicit arms.

### `#[cfg(test)] mod tests { ... }`

```rust
#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn bst_insert_and_search() { ... }
}
```

Rust's built-in unit-testing setup, no external framework needed:

- `#[cfg(test)]` - a *conditional compilation* attribute: this module is
  only compiled when running `cargo test`, and excluded entirely from
  normal `cargo build`/`cargo run` builds.
- `mod tests { ... }` - an inline module, a common convention for keeping
  a type's tests right next to its implementation in the same file.
- `use super::*;` - imports everything from the parent module (`Node` and
  friends) into `tests`' scope, so the test body can refer to `Node`
  directly instead of `super::Node`.
- `#[test]` - marks a function as a test case. `cargo test` runs every
  `#[test]`-annotated function and reports pass/fail based on whether it
  panics (e.g. via a failing `assert!`).
