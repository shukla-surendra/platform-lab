# NumPy

**Category:** numerical computing (the array/memory foundation pandas, scikit-learn, and
most of the Python ML stack are built on)

## What it is, and why it exists

Python's built-in `list` is a dynamically-typed array of *pointers* — each element can be
any type, which means each element is a separate Python object living somewhere else in
memory, and every operation on it goes through Python's interpreter loop, one element at a
time. That flexibility has a real, direct cost: iterating a million-element list in a Python
`for` loop pays the interpreter's per-element overhead a million times over.

NumPy's core object, the **`ndarray`**, gives that up on purpose: every element is the
**same fixed type** (a `dtype`), stored **contiguously** in one raw block of memory — much
closer to a C array than a Python list. That single design decision is what makes two things
possible at once: **vectorized operations** (a whole array processed by one call into
compiled C/Fortran code, not a Python loop) and **broadcasting** (operating on
differently-shaped arrays without manually replicating data) — both covered below with real
timing and real output, not just claimed.

Verified on this machine, everything below was actually run against NumPy 2.2.6.

## The `ndarray`: shape, dtype, and what they cost

```python
import numpy as np

a = np.array([1, 2, 3])
b = np.array([1.0, 2.0, 3.0])
c = np.array([[1, 2], [3, 4]])

print(a.dtype, b.dtype)          # int64 float64
print(c.shape, c.ndim, c.size)   # (2, 2) 2 4
print(a.itemsize, b.itemsize)    # 8 8   (bytes per element)
print(a.nbytes)                  # 24    (3 elements * 8 bytes)
```

Every array has a **`dtype`** (the fixed element type — `int64`, `float64`, `bool`, and
narrower/wider variants like `int8`/`float32`), a **`shape`** (a tuple giving the size along
each dimension), and `nbytes` that follows directly and predictably from
`size * itemsize` — because every element is the same fixed width, NumPy knows exactly how
much memory an array needs before allocating it, unlike a Python list of arbitrary objects.

## The physical layout: strides, and why `.T` is (almost) free

An array's **strides** are the number of bytes to step, per axis, to reach the next element
— this is the literal mechanism underneath indexing and reshaping, not an implementation
detail to skip past:

```python
d = np.arange(12).reshape(3, 4)
print(d)
# [[ 0  1  2  3]
#  [ 4  5  6  7]
#  [ 8  9 10 11]]

print(d.strides)                        # (32, 8)
print(d.flags['C_CONTIGUOUS'])          # True

e = d.T
print(e.strides)                        # (8, 32)   <- same underlying memory, different strides
print(e.flags['C_CONTIGUOUS'], e.flags['F_CONTIGUOUS'])  # False True
```

`d`'s strides `(32, 8)` mean: move 32 bytes (4 elements × 8 bytes) to go to the next *row*,
and 8 bytes to go to the next *column* — exactly the row-major ("C-order") layout NumPy
uses by default. `d.T` (the transpose) has strides `(8, 32)` — **the exact same underlying
bytes in memory, just reinterpreted with the two strides swapped.** This is why transposing a
NumPy array is (almost) instant regardless of size: it's not copying or rearranging a single
byte, just changing how the existing bytes are walked. It's also why `e` is no longer
`C_CONTIGUOUS` (its rows are no longer contiguous runs of memory) but is
`F_CONTIGUOUS` (Fortran/column-major order) instead — some operations (certain BLAS calls
under the hood of `np.dot`/`@`) are meaningfully faster on contiguous memory, which is the
practical reason contiguity is worth being aware of rather than pure trivia.

## Views vs. copies: the single most common source of a real NumPy bug

Whether an operation returns a **view** (shares the same underlying memory as the original)
or a **copy** (a genuinely new, independent block of memory) is not obvious from the syntax
alone, and getting it wrong is a real, recurring bug — modifying what you believe is an
independent array silently corrupts the original:

```python
arr = np.arange(10)
view = arr[2:5]          # basic slicing -> a VIEW
view[0] = 999
print(arr)                # [  0   1 999   3   4   5   6   7   8   9]  <- arr changed!

arr2 = np.arange(10)
fancy = arr2[[2, 3, 4]]   # fancy (list/array) indexing -> a COPY
fancy[0] = 999
print(arr2)                # [0 1 2 3 4 5 6 7 8 9]  <- arr2 is untouched

print(view.base is arr)    # True  — view shares arr's memory
print(fancy.base is arr2)  # False — fancy owns independent memory
```

**The rule**: basic slicing (`arr[start:stop:step]`, a single integer, or `...`) always
returns a view — cheap (no data copied) but shares memory with the original, so writing to it
writes through to the original. **Fancy indexing** (a list or array of indices, or a boolean
mask) always returns a copy — safe to mutate independently, but costs real memory and time
proportional to the selected data's size. `.base` is the direct, checkable way to confirm
which one you actually have rather than guessing — `arr.base is None` for an array that owns
its own memory, or a reference to the original array for a view. When in doubt, `.copy()`
explicitly rather than relying on which indexing style happened to be used.

## Broadcasting: operating on different shapes without replicating data

```python
a = np.array([[1], [2], [3]])    # shape (3, 1)
b = np.array([10, 20, 30])       # shape (3,)

print(a + b)
# [[11 21 31]
#  [12 22 32]
#  [13 23 33]]
```

Two shapes as different as `(3, 1)` and `(3,)` combined into a `(3, 3)` result — nothing was
manually tiled or repeated to make the shapes match. **Broadcasting's actual rule**: line up
the two shapes by their *trailing* (rightmost) dimension; any dimension missing on the
shorter shape is treated as an implicit leading `1`. Then, axis by axis, the two dimensions
are compatible if they're equal, or if either one is `1` (a size-`1` dimension stretches to
match the other, conceptually — not literally copied in memory). Walking through `a`'s
`(3, 1)` against `b`'s `(3,)` here: `b` is first treated as `(1, 3)` (its missing leading
dimension padded to `1`). Trailing axis: `a` has `1`, `b` has `3` — compatible, `a`'s `1`
stretches to `3`. Leading axis: `a` has `3`, `b` has `1` — compatible, `b`'s `1` stretches to
`3`. Both axes resolve to `3`, giving the `(3, 3)` result. When shapes are genuinely
incompatible, NumPy says so directly rather than guessing:

```python
np.array([1, 2, 3]) + np.array([1, 2])
# ValueError: operands could not be broadcast together with shapes (3,) (2,)
```

Broadcasting is the mechanism behind an enormous amount of idiomatic NumPy/pandas code —
"subtract the column means from every row," "normalize every row by its own max" — all done
without an explicit loop or an explicitly-replicated array, by shaping one operand with a
strategic size-`1` axis (`col_means[np.newaxis, :]` or `.reshape(1, -1)`) and letting
broadcasting do the rest.

## Vectorization: why looping in Python is the thing to avoid

```python
import time

n = 1_000_000
x_list = list(range(n))
x_np = np.arange(n)

start = time.perf_counter()
result_loop = [v * 2 + 1 for v in x_list]
loop_time = time.perf_counter() - start

start = time.perf_counter()
result_vec = x_np * 2 + 1
vec_time = time.perf_counter() - start

print(f"pure python loop: {loop_time*1000:.2f} ms")
print(f"numpy vectorized: {vec_time*1000:.2f} ms")
print(f"speedup: {loop_time/vec_time:.1f}x")
```
```
pure python loop: 26.67 ms
numpy vectorized: 3.18 ms
speedup: 8.4x
```

Real, measured — and this comparison is actually **stacked in Python's favor**: a list
comprehension is already one of the faster ways to loop in pure Python; a naive `for` loop
with `.append()` would lose by a noticeably larger margin, and the gap widens further on
more complex per-element math or larger arrays. The mechanism is the same one behind the
strides/contiguity section above: `x_np * 2 + 1` isn't a Python loop calling `*` and `+` a
million times each — it's a single call into a compiled C loop (a **ufunc**, universal
function) that walks the array's contiguous memory directly, with none of the Python
interpreter's per-element bookkeeping. **The practical rule this implies**: any Python `for`
loop touching a NumPy array element-by-element is very likely leaving most of NumPy's actual
performance on the table — the fix is almost always finding the vectorized/broadcasted
equivalent expression instead.

### ufuncs: element-wise operations, with more control than the operators alone

```python
a = np.array([1, -2, 3, -4])
print(np.abs(a))                 # [1 2 3 4]
print(np.where(a > 0, a, 0))     # [1 0 3 0]  -- vectorized "if/else" per element
```

`np.where(condition, if_true, if_false)` is the vectorized equivalent of an `if/else`
branch evaluated per element — genuinely necessary once "loop and check a condition" would
otherwise be the only way to express the logic, and exactly the tool that keeps conditional
logic inside the fast, vectorized path instead of falling back to a Python loop.

## Linear algebra (`np.linalg`)

```python
A = np.array([[2., 1.], [1., 3.]])
b = np.array([3., 5.])

x = np.linalg.solve(A, b)
print(x)              # [0.8 1.4]
print(A @ x)           # [3. 5.]  -- verifies Ax = b

eigvals, eigvecs = np.linalg.eig(A)
print(eigvals)          # [1.38196601 3.61803399]
```

`np.linalg.solve(A, b)` solves `Ax = b` directly via LU decomposition — meaningfully more
numerically stable and faster than computing `np.linalg.inv(A) @ b` explicitly (computing a
full matrix inverse is both more expensive and less numerically stable than solving the
system directly; reach for `solve` unless the inverse itself is genuinely needed for
something else). `@` is Python's matrix-multiplication operator (equivalent to
`np.matmul`, and distinct from `*`, which is *element-wise* multiplication — a very common
early mistake). Eigendecomposition (`np.linalg.eig`) underlies PCA, covered directly in
[`../scikit-learn/ml-fundamentals-deep-dive.md`](../scikit-learn/ml-fundamentals-deep-dive.md#dimensionality-reduction-pca)
— PCA's principal components literally *are* the eigenvectors of the data's covariance
matrix, which is why understanding `eig` here pays off directly there.

## Random number generation: use `default_rng`, not the legacy global state

```python
rng = np.random.default_rng(seed=42)
sample = rng.normal(loc=0, scale=1, size=5)
print(sample)
# [ 0.30471708 -1.03998411  0.7504512   0.94056472 -1.95103519]
```

`np.random.default_rng(seed=...)` (the modern `Generator` API, standard since NumPy 1.17) is
the correct entry point for new code — it creates an explicit, independent random state
object you pass around and control directly. The older, still-common `np.random.seed(42)` +
`np.random.rand(...)` pattern mutates a single **global, shared** random state — which is a
real, concrete problem in anything beyond a quick script: two unrelated pieces of code (a
data-loading step and a model's internal randomness, say) silently interfere with each
other's random sequence through that shared global state, making results depend on *what
else ran before them and in what order* — exactly the kind of hard-to-reproduce bug an
explicit, scoped `Generator` object avoids by construction.

## Two real gotchas worth knowing before they cause a production bug

### Fixed-width integer types wrap around silently on arithmetic overflow

```python
x = np.array([120], dtype=np.int8)   # int8 range: -128 to 127
y = np.array([10], dtype=np.int8)
print(x + y)
# [-126]
```

`120 + 10 = 130`, which doesn't fit in `int8`'s `-128..127` range — and NumPy doesn't raise
an error or warn, it silently **wraps around** (`130 - 256 = -126`), exactly like fixed-width
integer overflow in C. (NumPy 2.0+ *does* now raise `OverflowError` if you try to
*construct* an array from a Python integer literal that's already out of range for the
target dtype — `np.array([200], dtype=np.int8)` errors immediately — but that stricter check
only guards construction, not arithmetic performed afterward on values that were valid at
creation time, as shown above.) The practical implication: choosing a narrow dtype
(`int8`/`int16`/`float32`) to save memory on a large array is a real, valid optimization, but
it's only safe once you've confirmed the actual value range in play can't exceed that dtype's
range during any computation performed on it, not just at load time.

### Mixed-dtype arithmetic promotes to a wider type — sometimes more aggressively than expected

```python
i = np.array([1, 2, 3], dtype=np.int32)
f = np.array([1.5, 2.5, 3.5], dtype=np.float32)
print((i + f).dtype)
# float64
```

Adding an `int32` array to a `float32` array produces **`float64`**, not `float32` — a real,
easy-to-miss surprise if the goal was keeping everything in 32-bit precision (common when
memory or GPU-transfer bandwidth matters). The reason: NumPy's type-promotion rules pick a
result type that can represent both inputs *without losing precision* — `float32` cannot
exactly represent every possible `int32` value (`float32` has 24 bits of mantissa; `int32`
needs up to 32 bits to represent exactly), so NumPy promotes to `float64` rather than
silently lose precision on the integer side. If 32-bit precision throughout is a real
requirement (common in ML pipelines to control memory), the fix is being explicit
(`.astype(np.float32)` immediately after any operation that might upcast) rather than
assuming a mixed-dtype expression stays in the narrower type.

## Where this connects to the rest of the ML stack

- **[pandas](../pandas/README.md)** — a `DataFrame` is, underneath its labels and mixed
  column dtypes, built from NumPy arrays column-by-column; pandas's own vectorization story
  is NumPy's, with labeling and heterogeneous-dtype handling layered on top.
- **[scikit-learn](../scikit-learn/README.md)** — every estimator's `.fit(X, y)` expects `X`
  as a 2D NumPy array (or something that converts cleanly to one, like a DataFrame of
  numeric columns) — the shape/dtype rules on this page are literally the input contract
  scikit-learn's entire API is built around.
- **[ml-fundamentals-deep-dive.md](../scikit-learn/ml-fundamentals-deep-dive.md)** — gradient
  descent, regularization, and PCA are all, mechanically, sequences of vectorized NumPy
  array operations under the hood; this page is the substrate that makes those pages'
  algorithms fast enough to be practical at all.
