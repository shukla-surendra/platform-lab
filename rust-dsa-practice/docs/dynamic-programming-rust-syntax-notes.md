# Rust syntax notes - `dynamic_programming` crate

Running notes on Rust language features encountered while solving problems
in this crate, for reference. (See also
[recursion-rust-syntax-notes.md](recursion-rust-syntax-notes.md) and
[binary-search-tree-rust-syntax-notes.md](binary-search-tree-rust-syntax-notes.md)
and
[arrays-hashing-rust-syntax-notes.md](arrays-hashing-rust-syntax-notes.md)
for more.)

## `&` in a pattern (dereferencing pattern) vs. `&` in an expression

From `001_nth_fibonacci_memoization.rs`:

```rust
if let Some(&cached) = memo.get(&n) {
    return cached;
}
```

This trips people up because `&` means close to the OPPOSITE thing here
compared to its more familiar use.

**`&` in expression position** (the usual case, e.g. `&n` a few
characters later on the same line) means "give me a reference to this" -
it creates a borrow. `memo.get(&n)` passes a `&u64` (a reference to `n`)
because `HashMap::get` wants a reference to the key, not ownership of it.

**`&` in pattern position** (the `&cached` inside `Some(&cached)`) means
the opposite: "I expect to be matching against a reference here - strip
it off, and bind the name to the value it points to." It's a
*dereferencing pattern*.

Why it's needed here: `HashMap::get` returns `Option<&V>`, a reference
into the map, not an owned value - the map still owns the actual `u64`,
it's just lending a look at it. So `memo.get(&n)` has type
`Option<&u64>`. Matching that against:

- `Some(cached) => ...` binds `cached: &u64` (still a reference).
- `Some(&cached) => ...` binds `cached: u64` (the `&` in the pattern
  peels off one layer of reference, copying out the value it points to).

The code uses the second form because `fib` returns `u64`, not `&u64` -
`return cached;` needs `cached` to already be an owned `u64`. This only
works cheaply because `u64` implements `Copy` (copying a `u64` out from
behind a reference is just copying 8 bytes); for a type that isn't
`Copy`, you'd need `.cloned()`/`.copied()` on the `Option<&V>` instead of
a `&` pattern, since you can't casually copy an arbitrary type out from
behind a shared reference.

Equivalent alternative, without the pattern trick:

```rust
if let Some(cached) = memo.get(&n) {
    return *cached; // explicit deref, same effect as `&cached` in the pattern
}
```

Both are idiomatic; `&cached` in the pattern is slightly more common
because it moves the "this is a reference, dereference it" concern into
the match itself rather than needing a separate `*` at every use site
inside the arm.
