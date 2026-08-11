# Rust syntax notes - `arrays_hashing` crate

Running notes on Rust language features encountered while solving problems
in this crate, for reference. (See also
[recursion-rust-syntax-notes.md](recursion-rust-syntax-notes.md),
[dynamic-programming-rust-syntax-notes.md](dynamic-programming-rust-syntax-notes.md),
and [binary-search-tree-rust-syntax-notes.md](binary-search-tree-rust-syntax-notes.md)
for more.)

## `use std::collections::HashSet;`

From the top of `001_valid_sudoku.rs`. Every Rust file starts with lines like
this, which is exactly why it gets copied without being understood.

### It does not import anything

The single most useful thing to know: **`use` does not bring code into your
program.** It is not Python's `import` (which executes a module and binds a
name at runtime) and it is not C's `#include` (which pastes text). It creates a
**local shortcut for a path that already resolves**.

`std::collections::HashSet` is reachable from any Rust file with no `use` at
all. This compiles and runs as-is:

```rust
fn main() {
    let mut s: std::collections::HashSet<i32> = std::collections::HashSet::new();
    s.insert(1);
    println!("no `use` needed: len = {}", s.len());
}
```

So the line buys you nothing but the ability to write `HashSet` instead of
`std::collections::HashSet`. There is no runtime cost, no code-size cost, and
nothing is "pulled in" — `std` is linked either way. Deleting the `use` and
fully qualifying every mention produces a byte-identical binary.

Frame it as **"introduce this name into this scope,"** not "load this library."
Everything else about `use` follows from that one sentence.

### Reading the path

```
std      ::  collections  ::  HashSet
 |             |                |
 |             |                +-- the item (here, a struct)
 |             +------------------- a module inside that crate
 +--------------------------------- the crate root
```

`std` is the standard library. Since the 2018 edition it is available
implicitly — no `extern crate std;`, which is why you'll see that line only in
pre-2018 code and in `#![no_std]` projects.

### So why is the line needed at all?

Because `HashSet` is **not in the prelude**. Rust auto-imports a small set of
names into every module — `Vec`, `String`, `Option`, `Result`, `Box`, `Some`,
`None`, `Iterator`, and a handful more. Those need no `use`:

```rust
let _v: Vec<i32> = Vec::new();     // fine, no use
let _s: String = String::new();    // fine, no use
```

`HashSet`, `HashMap`, `BTreeMap`, `VecDeque`, and `BinaryHeap` are deliberately
left out. The prelude is kept small because every name in it is a name you
can't reuse freely — put `HashSet` in the prelude and nobody can define their
own type called `HashSet` without shadowing. The cost of that restraint is one
`use` line per file, which is judged the better trade.

That's the whole answer to "why do I have to import this but not `Vec`?"

### `use` is scoped to a *module*, not a file

This one actually bites. A `mod` block does **not** inherit the enclosing
module's imports:

```rust
use std::collections::HashSet;

fn outer() -> HashSet<i32> { HashSet::new() }   // fine

mod inner {
    fn f() -> HashSet<i32> { HashSet::new() }   // ERROR
}
```

```
error[E0425]: cannot find type `HashSet` in this scope
help: consider importing one of these structs
  |
5 +     use std::collections::HashSet;
```

Each module is its own namespace, and a file only *looks* like the unit of
scoping because most files contain exactly one module. This is precisely why
every test block in this repo opens with:

```rust
#[cfg(test)]
mod tests {
    use super::*;   // pull in everything from the parent module
    ...
}
```

`super::*` is not boilerplate noise — without it the test module can't see the
functions it is testing, nor any of the parent's imports. Three path keywords
show up in this position:

| Keyword | Means |
|---|---|
| `crate::` | from this crate's root |
| `super::` | from the parent module |
| `self::` | from the current module |

### The other flavour: traits must be in scope to call their methods

Everything above is about *convenience*. There is one case where `use` is
**mandatory** and no amount of path-qualifying replaces it: calling a trait
method requires the trait itself to be in scope.

```rust
fn main() {
    let mut out = std::io::stdout();
    out.write_all(b"hi\n").unwrap();   // ERROR, despite the full path above
}
```

```
error[E0599]: no method named `write_all` found for struct `Stdout`
     = help: items from traits can only be used if the trait is in scope
```

The fix is `use std::io::Write;` — importing a trait you never mention by name,
purely to unlock `.write_all()`. That's why real code has imports that look
unused but aren't, and it's the reason a "helpfully" deleted import sometimes
breaks a build in a way that seems unrelated. `Read`, `Write`, `FromStr`, and
`Rng` are the ones you'll hit most.

### Syntax variants

```rust
use std::collections::HashSet;                  // one item
use std::collections::{HashMap, HashSet};       // several from one module
use std::collections::HashSet as Set;           // rename (disambiguate clashes)
use std::collections::*;                        // glob - avoid outside tests/preludes
pub use crate::grid::Grid;                      // re-export as part of YOUR public API
                                                // (hypothetical - see note below)

// nested, as in grids/src/lib.rs:
use std::{cmp::Reverse, collections::{BinaryHeap, VecDeque}, fmt};
```

Two notes. A glob import makes it impossible to tell where a name came from, so
it's confined by convention to `use super::*` in tests and to prelude modules.
And `pub use` is the tool for flattening a deep module tree. The `grids` crate
doesn't need it today — everything is defined directly in `lib.rs`, so
`grids::Grid` already works. If it were later split into `grid.rs`, `bfs.rs`,
and `dijkstra.rs`, a few `pub use` lines in `lib.rs` would keep
`grids::Grid` working for callers instead of forcing them to `grids::grid::Grid`.

`cargo fmt` sorts imports and groups them std / external / local; let it.

### While you're here: what else is in `std::collections`

| Type | Reach for it when |
|---|---|
| `HashMap<K, V>` / `HashSet<T>` | O(1) average lookup, order irrelevant — the default |
| `BTreeMap<K, V>` / `BTreeSet<T>` | you need **sorted** iteration or range queries; O(log n) |
| `VecDeque<T>` | push/pop at both ends — **the BFS queue** |
| `BinaryHeap<T>` | max-heap; wrap in `Reverse` for a min-heap — Dijkstra, top-K |
| `LinkedList<T>` | essentially never; `Vec` or `VecDeque` wins in practice |

`Vec<T>` lives in `std::vec` and is in the prelude, which is why it's the one
collection you never import.

### Summary

| Claim | Reality |
|---|---|
| "`use` imports the library" | No. It's a local name shortcut; `std` is linked regardless |
| "I can't use `HashSet` without it" | You can — write `std::collections::HashSet` in full |
| "Why not `Vec`?" | `Vec` is in the prelude; `HashSet` deliberately isn't |
| "One `use` covers the file" | It covers the *module*; nested `mod` blocks need their own |
| "An unused import is dead code" | Not if it's a trait — trait methods need the trait in scope |

## `let mut seen: HashSet<(char, usize, char)> = HashSet::new();`

From `001_valid_sudoku.rs` (version 3, the single-set encoding). One line,
six separate ideas stacked on top of each other. Taken apart:

```
let      mut      seen  :  HashSet < (char, usize, char) >  =  HashSet::new();
 |        |        |            |            |                      |
 |        |        |            |            |                      +-- associated function
 |        |        |            |            +------------------------- tuple type (the key)
 |        |        |            +-------------------------------------- generic parameter
 |        |        +--------------------------------------------------- binding name
 |        +------------------------------------------------------------ binding is mutable
 +--------------------------------------------------------------------- introduce a binding
```

### `mut` describes the *binding*, not the type

This is the piece that most often confuses people coming from Python,
where mutating a `set` needs no declaration at all. In Rust, `mut` is not
a property of `HashSet` — it is a property of the *name* `seen`. It grants
two things:

1. you may reassign `seen` to a different `HashSet`, and
2. you may take a `&mut` reference to it.

Point 2 is the one that actually matters here. `HashSet::insert` has the
signature `fn insert(&mut self, value: T) -> bool` — it needs a mutable
borrow of the set. Without `mut` on the binding, there is nothing to
borrow mutably:

```
error[E0596]: cannot borrow `seen` as mutable, as it is not declared as mutable
 --> t2.rs:4:5
  |
4 |     seen.insert(('r', 3, '5'));
  |     ^^^^ cannot borrow as mutable
  |
help: consider changing this to be mutable
  |
3 |     let mut seen: HashSet<(char, usize, char)> = HashSet::new();
  |         +++
```

Read that error as "you asked for a `&mut`, and this binding can't produce
one" rather than "the set is frozen." The distinction matters once you hit
`&mut` in function arguments, where the same rule shows up without a `let`
in sight.

### The type annotation is optional here — and worth writing anyway

`HashSet::new()` on its own is genuinely ambiguous: it returns
`HashSet<T>` for *any* `T`, and nothing in that expression pins `T` down.
But Rust's inference is not line-by-line — it looks at the whole function
body. The later `seen.insert(('r', row, value))` unifies `T` with
`(char, usize, char)`, so this compiles fine:

```rust
let mut seen = HashSet::new();          // T unknown at this point...
seen.insert(('r', row, value));         // ...and resolved by this line
```

The annotation becomes *mandatory* only when nothing downstream constrains
`T` — an empty set that is returned, passed to a generic function, or
never inserted into. You'll meet the error as
`type annotations needed for HashSet<T>`.

Two reasons to write it even when it's optional:

- **Readability.** The key encoding *is* the algorithm in this problem. A
  reader who sees `(char, usize, char)` immediately asks "why three
  fields?" — which is exactly the question the code wants them asking.
- **Better errors.** With the annotation, a wrong `insert` call is
  reported at the `insert`. Without it, inference can propagate the wrong
  `T` and surface the failure somewhere less obvious.

The equivalent without a separate annotation is the **turbofish**, which
supplies the generic parameter directly to the call:

```rust
let mut seen = HashSet::<(char, usize, char)>::new();
```

Same thing. The `::<>` is needed because `HashSet<(char, usize, char)>::new()`
would be parsed as a comparison — `<` is ambiguous in expression position,
so Rust requires the extra `::` to disambiguate. In type position (after
the `:` in a `let`) there's no ambiguity, which is why the annotated form
doesn't need it.

### `HashSet<T>` has a second, hidden generic parameter

The real signature is:

```rust
pub struct HashSet<T, S = RandomState> { .. }
```

`S` is the *hasher builder*, defaulting to `RandomState` — SipHash 1-3,
seeded randomly per process. That default is a security decision, not a
performance one: it makes hash-collision DoS attacks impractical against
web services that hash untrusted input.

For DSA work you're paying for a threat model you don't have. If a hash
set ever shows up in a profile, swapping in `FxHashMap`/`FxHashSet` (from
`rustc-hash`) or `ahash` typically buys 2-3x on small keys. Worth knowing
the parameter exists; not worth adding a dependency for an 81-cell board.
For *this* problem the better answer isn't a faster hasher at all — it's
the bitmask version, which eliminates hashing entirely (see version 2 in
`001_valid_sudoku.rs`).

### `(char, usize, char)` — a tuple as a composite key

A tuple type is an **anonymous product type**: a fixed-length, ordered,
heterogeneous group with no name and no field labels. `(char, usize, char)`
is a distinct type from `(char, char, usize)` — position is meaning.

The reason a tuple can be a `HashSet` element at all is that Rust
implements `Hash`, `Eq`, `Ord`, `Clone`, and `Copy` for tuples
**structurally** — a tuple gets the trait exactly when all of its elements
have it. Nothing needs deriving; it comes for free.

That rule is easiest to see when it *fails*. Swap `usize` for `f64`:

```
error[E0599]: the method `insert` exists for struct `HashSet<(char, f64)>`,
              but its trait bounds were not satisfied
  = note: the following trait bounds were not satisfied:
          `f64: Eq`
          which is required by `(char, f64): Eq`
          `f64: Hash`
          which is required by `(char, f64): Hash`
```

The "which is required by" lines are the structural rule stated out loud.
(`f64` isn't `Eq` because `NaN != NaN` breaks reflexivity, and it isn't
`Hash` because `Hash` and `Eq` must agree — `+0.0 == -0.0` yet they have
different bit patterns.)

### What the three fields actually encode

```rust
seen.insert(('r', row, value));         // row `row` already contains `value`?
seen.insert(('c', col, value));         // column `col`?
seen.insert(('b', box_index, value));   // 3x3 box `box_index`?
```

- **field 0, the tag** — `'r'` / `'c'` / `'b'`. This is the load-bearing
  part. Without it, `(0, '5')` would mean both "row 0 holds a 5" and
  "column 0 holds a 5", and a legal board with a 5 in row 0 and a
  different 5 in column 0 would be rejected. The tag partitions one set
  into three disjoint namespaces.
- **field 1, the group index** — `usize`, 0..=8.
- **field 2, the value** — the digit, kept as `char` to match the board.

This is the **canonical key** idea from
`fundamentals/dsa_prep/arrays_hashing/PATTERN.md`, made literal: choose a
derived key such that everything that must not coexist collides, and
nothing else does.

### `char` is four bytes, not one

A Rust `char` is a **Unicode scalar value** — a 32-bit code point, not a
byte. `'5'` is 4 bytes wide; `b'5'` is a `u8` byte literal, 1 byte, and a
different type entirely. That's why the bitmask version writes
`value as u8 - b'1'`: it casts down to a byte to do ASCII arithmetic. The
cast is only safe because digits are contiguous in ASCII and we know the
input alphabet.

`char` also isn't the same as a *grapheme* — `'é'` may be one `char` or
two depending on normalization, and an emoji with a skin-tone modifier is
several. Irrelevant for Sudoku, but it's the reason `String` indexing by
integer doesn't exist in Rust, which surprises people on string problems.

### `usize` — the index-shaped integer

`usize` is an unsigned integer the width of a pointer on the target
platform: 8 bytes on any machine you'll run this on. It is the type
required for indexing slices and `Vec`s, which is why array indices in
Rust are almost always `usize` rather than `u32` or `i32`.

Here `row` comes from `for row in 0..9`. Integer literals default to
`i32`, but inference overrides that default when the value is used
somewhere that demands a specific type — `board[row][col]` forces `usize`,
and the tuple then inherits it. That's why the annotation says `usize`
rather than `i32`.

### `HashSet::new()` — an associated function

`new` is an **associated function**, not a method: it's namespaced under
the type (`HashSet::new`) and takes no `self`, so there's no receiver to
call it on. Closest analogue is a static factory method in Java or a
`@classmethod` in Python. Methods use `.` (`seen.insert(..)`); associated
functions use `::` (`HashSet::new()`).

`new()` is a strong convention rather than a language rule — there's no
`New` trait. `HashSet::default()` does the same thing via the `Default`
trait, and `HashSet::with_capacity(n)` pre-allocates.

Note that `new()` does **not** allocate. `HashSet` defers its first heap
allocation until the first insert, so an empty set that never gets used
costs nothing beyond its stack footprint.

### Memory layout (a detail with a real payoff)

```
size_of::<char>()                       = 4
size_of::<usize>()                      = 8
size_of::<(char, usize, char)>()        = 16   align 8
```

4 + 8 + 4 = 16 exactly — no padding. That's not luck: unlike C, Rust does
**not** guarantee that struct or tuple fields are laid out in declaration
order, and the compiler reorders them to minimize padding. Force C's
ordering and you can watch it get worse:

```rust
#[repr(C)] struct CLayout(char, usize, char);   // 24 bytes
           struct RustLayout(char, usize, char); // 16 bytes
```

The C layout wastes 4 bytes padding the `char` up to the `usize`'s 8-byte
alignment, then 4 more tail-padding the whole struct. Rust just puts the
`usize` first.

The payoff is why the tuple key beats the obvious alternative. A `String`
key — `format!("r{}{}", row, value)` — is 24 bytes of stack *plus* a heap
allocation *plus* a `memcpy` *plus* hashing a variable-length byte string,
per insert, three times per cell. The tuple key is 16 stack bytes,
`Copy`, and hashed as three fixed-width fields. If you catch yourself
reaching for `format!` to build a composite hash key, reach for a tuple
instead — that's the transferable rule.

### Summary

| Fragment | What it is | Easy to get wrong |
|---|---|---|
| `let` | introduces a binding | — |
| `mut` | the *binding* is mutable | it's not a property of the type; needed because `insert` takes `&mut self` |
| `: HashSet<..>` | type annotation | optional here — inference resolves `T` from the later `insert` |
| `HashSet<T, S>` | `S` defaults to `RandomState` | the default hasher is DoS-resistant, i.e. deliberately not the fastest |
| `(char, usize, char)` | anonymous product type | gets `Hash`/`Eq` structurally, only if *every* element has them |
| `char` | 4-byte Unicode scalar | not a byte — that's `u8` / `b'5'` |
| `usize` | pointer-width unsigned int | the type slice indexing requires; why `row` isn't `i32` |
| `::new()` | associated function | `::` not `.`; convention, not a trait; doesn't allocate |

## `let mut boxes: Vec<HashSet<char>> = vec![HashSet::new(); 9];`

From `001_valid_sudoku.rs` (version 1). The `let mut` and the type-annotation
parts are covered above; what's new here is the `vec![expr; n]` macro — which
looks trivial and hides the single nastiest gotcha in this file.

### `vec!` has two different forms

```rust
vec![a, b, c]          // LIST form: three specific elements
vec![expr; n]          // REPEAT form: n copies of one element
```

The separator is the whole difference: comma = list, **semicolon = repeat**.
The repeat form mirrors array syntax (`[0u16; 9]`), which is where the
similarity to a "length" argument comes from.

### The repeat form evaluates the expression exactly once

This is the part worth proving rather than assuming. Instrument it:

```rust
static mut CALLS: u32 = 0;
fn make() -> HashSet<char> { unsafe { CALLS += 1; } HashSet::new() }

let _v = vec![make(); 9];
// prints: expression evaluated 1 time(s) for 9 elements
```

So `vec![HashSet::new(); 9]` does **not** call `HashSet::new()` nine times. It
calls it once and **clones the result eight times**. That's why the repeat form
requires `T: Clone` — and it's the mechanism behind everything below.

### The gotcha: `Clone` does not mean the same thing for every type

Because the elements are clones, what you get depends entirely on what `Clone`
*does* for that type. For `HashSet` it's a deep copy, so the nine sets are
independent — exactly what Sudoku needs:

```rust
let mut sets = vec![HashSet::new(); 3];
sets[0].insert('a');
// sets[0]={'a'}  sets[1]={}     <- independent
```

Now change the element type to something whose `Clone` shares instead of
copies:

```rust
let shared = vec![Rc::new(RefCell::new(HashSet::new())); 3];
shared[0].borrow_mut().insert('a');
// shared[0]={'a'}  shared[1]={'a'}   <- ALIASED
```

Identical syntax. Completely different meaning. `Rc::clone` copies the *handle*
and bumps a refcount; all three entries point at one object. The same applies to
`Arc`, and to any type whose `Clone` is a shallow/shared copy.

**The rule:** `vec![x; n]` gives you `n` independent values only if `x`'s `Clone`
is a deep copy. Before writing it, ask what `Clone` means for that element type.

### Rust gets this right where Python gets it wrong

If that trap feels familiar, it's the classic Python bug:

```python
a = [set()] * 3
a[0].add('x')
# [{'x'}, {'x'}, {'x'}]   <- ALIASED, one set referenced three times

b = [set() for _ in range(3)]
b[0].add('x')
# [{'x'}, set(), set()]   <- independent
```

Python's `*` always aliases, because a `list` holds references and `set` has
reference semantics. The correct Python spelling is the comprehension.

Rust's `vec![HashSet::new(); 9]` is the *safe* one by default — `HashSet` has
value semantics and its `Clone` is deep. You only reproduce the Python bug by
explicitly opting into shared ownership with `Rc`/`Arc`. Worth noticing that the
language makes the aliasing visible in the type rather than hiding it in the
container's behaviour.

### The always-safe alternative

When `T` isn't `Clone` — or when you want a genuinely fresh value per slot
regardless of what `Clone` does — build it from an iterator:

```rust
let boxes: Vec<HashSet<char>> = (0..9).map(|_| HashSet::new()).collect();
```

The closure runs nine times, so nine independent values, no `Clone` bound.
Slightly noisier; immune to the trap above.

### For a fixed size, prefer an array

`9` here is a compile-time constant, so `Vec` is the wrong container by reflex
rather than by reasoning:

```rust
let mut boxes: [HashSet<char>; 9] = std::array::from_fn(|_| HashSet::new());
```

`array::from_fn` calls the closure once per index — fresh values, no `Clone`
needed, size encoded in the type so it can never be wrong at runtime.

Measured sizes:

```
size_of::<Vec<HashSet<char>>>()  = 24    (just ptr + len + cap)
size_of::<[HashSet<char>; 9]>()  = 432   (9 x 48, inline)
size_of::<HashSet<char>>()       = 48
```

The `Vec` is 24 bytes on the stack **plus** a 432-byte heap allocation for the
nine `HashSet` structs. The array is 432 bytes on the stack and allocates
nothing. Note that `HashSet::new()` itself doesn't allocate — each set defers its
first heap allocation until its first insert — so the `Vec` version costs one
allocation up front and up to nine more lazily.

And for *this* problem, both are still the wrong answer. Nine possible values
means the whole registry fits in `[0u16; 9]` — 18 bytes, no allocation, no
hashing. See the bitmask version in `001_valid_sudoku.rs`.

### The type annotation is optional here too

Same reasoning as the section above — inference resolves `T` from the later use:

```rust
let mut boxes = vec![HashSet::new(); 9];
boxes[0].insert('5');                    // compiles; T inferred as char
```

Keep the annotation for readability, not necessity.

### Summary

| Fragment | What it is | Easy to get wrong |
|---|---|---|
| `vec![a, b, c]` | list form | comma = list |
| `vec![x; n]` | repeat form | semicolon = repeat; `n` is a count, not an index |
| the repeat form | evaluates `x` **once**, clones it `n-1` times | it does *not* run `HashSet::new()` nine times |
| `T: Clone` bound | required by the repeat form | **`Clone` on `Rc`/`Arc` shares** — you get `n` aliases, not `n` values |
| `Vec<HashSet<char>>` | heap-allocated, runtime length | `9` is compile-time; `[HashSet<char>; 9]` is the better fit |
| `(0..n).map(..).collect()` | fresh value per slot | the always-safe form when `Clone` semantics are unclear |
