# Rust syntax notes - `recursion` crate

Running notes on Rust language features encountered while solving problems
in this crate, for reference. (See also
[binary-search-tree-rust-syntax-notes.md](binary-search-tree-rust-syntax-notes.md)
and
[dynamic-programming-rust-syntax-notes.md](dynamic-programming-rust-syntax-notes.md),
and
[arrays-hashing-rust-syntax-notes.md](arrays-hashing-rust-syntax-notes.md).)

## `todo!()`

From `010_print_subsequences.rs`:

```rust
fn subsequences(chars: &[char], i: usize, current: &mut String) {
    todo!("base case: i == chars.len() -> print current; else recurse twice (include/exclude chars[i])")
}
```

`todo!()` is a standard-library macro used as a placeholder for code you
haven't written yet. It compiles fine no matter what the function's
signature promises (here, returning `()`) because its return type is the
special "never type" `!`, which Rust lets coerce into any expected type -
the compiler trusts that this branch never actually produces a value,
because calling it panics.

- At compile time: acts like a stub with any type, so the surrounding
  function type-checks even though there's no real implementation yet.
- At run time: if actually called, it panics with the message
  `not yet implemented: <your string>`.
- The argument is optional and, when present, follows the same
  `format!`-style syntax as `println!` - so both `todo!()` and
  `todo!("did x = {}", x)` are valid.
- Siblings: `unimplemented!()` is essentially identical (conventionally
  used for "deliberately not implementing this branch," vs. `todo!()` for
  "not implemented yet, but will be"); `panic!()` is the more general form
  both are built on.

This is why the scaffolds in this crate compile (`cargo build` succeeds)
even before you've filled in the logic - `todo!()` satisfies the type
checker and only fails when you actually run the binary and execution
reaches that line.

## `match`

From `008_nth_fibonacci_recursion.rs`:

```rust
fn fib(n: u64) -> u64 {
    match n {
        0 => 0,
        1 => 1,
        _ => fib(n - 1) + fib(n - 2),
    }
}
```

`match` is Rust's pattern-matching control-flow expression - similar in
spirit to a `switch` statement in C/Java/JS, but stricter and more
powerful. It compares `n` against a series of *patterns*, top to bottom,
and runs the code for the first one that matches.

- `0 => 0` - a *pattern*: if `n` equals the literal `0`, the arm evaluates
  to `0`.
- `1 => 1` - same idea: if `n` equals `1`, the arm evaluates to `1`.
- `_ => fib(n - 1) + fib(n - 2)` - `_` is the *wildcard pattern*, matching
  anything not caught by an earlier arm (here, any `n >= 2`, since `u64`
  can't be negative). It plays the role of `default:` in a `switch`.

Key properties that make `match` different from `switch`:

- **Exhaustive**: the compiler requires every possible value of `n` to be
  covered by some arm. This `match` compiles only because `_` catches
  everything else - remove it and the compiler rejects the code with a
  "non-exhaustive patterns" error. This is what prevents the equivalent of
  an accidentally-unhandled `switch` case.
- **No fallthrough**: unlike C's `switch`, execution never "falls through"
  from one arm to the next. Each arm is self-contained; only one arm runs.
- **It's an expression, not a statement**: the whole `match` evaluates to a
  value (whichever arm ran), which is why `match n { ... }` can be the last
  line of `fib` with no `return` or trailing `;` - its value is the
  function's implicit return value, the same convention used for the
  `if`/`else` versions in `003_recursive_factorial.rs` and
  `005_return_recursion_sum.rs`.
- **Patterns can be much richer than literals**: ranges (`2..=10`), multiple
  values per arm (`0 | 1 => ...`), destructuring of tuples/structs/enums,
  and binding with guards (`n if n > 100 => ...`) are all valid - literal
  values and `_` are just the simplest case, shown here because that's all
  `fib` needs.

Compare with the `if`/`else` form used in earlier problems
(`003_recursive_factorial.rs`, `006_reverse_array_recursion.rs`,
`007_palindrome_string_recursion.rs`):

```rust
fn factorial(n: u32) -> u32 {
    if n == 0 {
        1
    } else {
        n * factorial(n - 1)
    }
}
```

Both compile to equivalent code for a simple two-way branch; `match`
becomes the better fit once there are 3+ distinct cases (like `fib`'s two
base cases plus the recursive case) since it reads as a flat list of
cases instead of a nested `if`/`else if`/`else` chain.
