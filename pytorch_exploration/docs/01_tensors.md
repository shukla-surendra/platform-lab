# Tensors

Part of the [PyTorch Fundamentals companion docs](README.md). Paired with the `# Tensors`
section of [`../torch_hands_on.ipynb`](../torch_hands_on.ipynb).

## In Plain English

A tensor is PyTorch's basic data container — a multi-dimensional array of numbers, like a
NumPy array, but with two extra abilities NumPy arrays don't have: it can live on a GPU
(or Apple Silicon's MPS), and PyTorch can automatically track the operations done to it so
it knows how to compute gradients later ([Chapter 2](02_autograd.md)). Every number a
PyTorch model touches — inputs, weights, activations, gradients — is a tensor.

## The First-Principles Explanation

### dtype, shape, device — a tensor's three defining properties

- **`dtype`**: what kind of number each element is (`torch.float32`, `torch.int64`, ...).
  `torch.tensor([1, 2, 3])` infers `int64`; `torch.tensor([1.0, 2.0, 3.0])` infers
  `float32` — the presence of a decimal point in the Python literals is what PyTorch uses
  to guess. Get this wrong (e.g., feeding integer-dtype data into a model expecting float)
  and you get either a hard error or, worse, silently wrong gradients.
- **`shape`**: the size along each dimension, e.g. `(2, 3)` for a 2-row, 3-column matrix.
- **`device`**: where the tensor's memory actually lives — `"cpu"`, `"cuda"` (NVIDIA GPU),
  or `"mps"` (Apple Silicon). Two tensors must be on the *same* device to interact — this
  is one of the most common real errors (`RuntimeError: Expected all tensors to be on the
  same device`), always fixed with an explicit `.to(device)`.

### Creation

`torch.tensor(data)` (from a Python list/nested list), `torch.zeros(shape)`,
`torch.ones(shape)`, `torch.randn(shape)` (standard normal random values — this is what
initializes a model's learnable weights before training even starts), `torch.arange(n)`.

### Indexing, slicing, reshaping — and the view/reshape distinction that actually matters

Tensors support NumPy-style indexing and slicing (`t[0]`, `t[:, 1]`, `t[1:3]`). Reshaping
is where a real mechanism is worth understanding, not just memorizing: a tensor's data
lives in one flat block of memory, and its `shape` plus its **stride** (how many elements
to skip, per dimension, to move to the next index) together describe how to interpret that
flat memory as a multi-dimensional array.

```python
a = torch.arange(6).reshape(2, 3)
# a: [[0, 1, 2], [3, 4, 5]], stride=(3, 1), contiguous=True
b = a.t()  # transpose — a VIEW, no data copied
# b: [[0, 3], [1, 4], [2, 5]], stride=(1, 3), contiguous=False
```

`a.t()` doesn't copy any data — it just returns a *new view* with a different stride,
reading the same underlying memory in a different order. That's fast and memory-cheap,
but it means `b` is no longer **contiguous** (its elements, read in the new shape's
natural order, aren't sequential in memory anymore). `.view()` requires the tensor to
already be contiguous, because it works purely by reinterpreting the existing memory
layout — it cannot rearrange memory itself:

```python
b.view(6)      # RuntimeError: view size is not compatible with input tensor's size and stride
b.reshape(6)   # works — falls back to actually copying/rearranging memory when needed
```

`.reshape()` is the safe default: it uses `.view()`'s cheap path when possible and
transparently copies when it isn't. `.view()` is worth reaching for specifically when you
want a hard guarantee that *no copy happens* — an explicit, checkable performance
assumption, not just a synonym for reshape.

### Broadcasting

Operations between tensors of different (but compatible) shapes automatically expand the
smaller one — no explicit copying needed, no memory actually duplicated:

```python
m = torch.ones(3, 4)
v = torch.tensor([1., 2., 3., 4.])   # shape (4,)
(m + v).shape   # (3, 4) — v is broadcast across every row
```

The rule, precisely: compare shapes from the *right*; two dimensions are compatible if
they're equal, or one of them is 1 (or missing entirely, treated as 1). This is exactly
what lets a single bias vector be added to every row of a batch of activations without
writing a loop — the mechanism underneath nearly every `+ bias` in every neural network
layer.

### NumPy interop — and a real shared-memory gotcha

`.numpy()` (tensor → array) and `torch.from_numpy()` (array → tensor) don't copy data on
CPU — they share the same underlying memory:

```python
t = torch.ones(3)
n = t.numpy()
t.add_(1)      # in-place op on the tensor
print(n)       # [2. 2. 2.] — the numpy array changed too, same memory
```

Convenient (genuinely free conversion, no copy cost) and a real footgun if you don't know
it's happening — mutating one silently mutates the other. This only applies to CPU
tensors; a GPU/MPS tensor has to be moved to CPU (`.cpu()`) before `.numpy()` works at
all, since NumPy has no concept of GPU memory.

## Grounded in the Notebook

The `# Tensors` section of `torch_hands_on.ipynb` runs every example above for real —
creation, the `view`-vs-`reshape` contiguity error (deliberately triggered, not just
described), broadcasting shapes, and the shared-memory NumPy interop demo.

## Deep-Dive: Why PyTorch Exposes Stride and Contiguity At All, Instead of Hiding It

It would be simpler, API-wise, for `.view()` to just silently do whatever `.reshape()`
does. PyTorch doesn't, on purpose: a silent copy is a silent *performance* cost, and for
large tensors (a batch of activations in a real model, not a toy 2×3 example) that cost is
real and sometimes significant. `.view()`'s strictness is a deliberate escape hatch for
performance-sensitive code to *assert* "this reshape must be free" and get a loud error
the moment that assumption breaks, rather than silently paying an unexpected memory-copy
cost deep inside a training loop.

## Try It Yourself

- Predict, then check: what's `torch.ones(3, 1) + torch.ones(1, 4)`'s resulting shape?
  Work out the broadcasting rule by hand first.
- Trigger the `.view()` contiguity error yourself with a different operation that also
  produces a non-contiguous tensor (hint: try slicing with a step, e.g. `t[::2]`, or
  `.permute()` on a 3D tensor) — confirm `.reshape()` still works there too.
- Move a tensor to `"mps"` (or `"cuda"` if available) and try to add it directly to a CPU
  tensor — read the actual error message PyTorch gives you.

## Common Misconceptions

- **"`.reshape()` and `.view()` are just two names for the same thing."** They overlap
  when the tensor is already contiguous, but `.view()` will error rather than copy, and
  `.reshape()` will copy rather than error — a real, load-bearing difference.
- **"A GPU tensor and CPU tensor can interact if PyTorch just converts automatically."**
  It won't, on purpose — device placement is always explicit (`.to(device)`), because an
  implicit cross-device copy hidden inside an operator would be a silent, hard-to-spot
  performance cost.
- **"`.numpy()`/`torch.from_numpy()` always copy data, like most conversions."** On CPU,
  they don't — shared memory, not a copy — which is exactly why mutating one can silently
  mutate the other.

## Practice Questions

1. Given `torch.zeros(2, 3, 4)`, what's its stride, assuming standard (row-major)
   contiguous layout? Work it out from the shape alone, without running code.
2. Why does `.t()` (transpose) produce a non-contiguous tensor, mechanically — what
   changes, and what doesn't?
3. You call `.numpy()` on a tensor, then later move that same tensor to `"mps"` with
   `.to("mps")`. Does the NumPy array still track the tensor's values after that move?
   Why or why not?

## Key Terms

- **dtype**: the element type of a tensor's data (`float32`, `int64`, ...).
- **Device**: where a tensor's memory physically lives (`cpu`, `cuda`, `mps`) — operations
  require matching devices.
- **Stride**: how many elements to skip, per dimension, to reach the next index along that
  dimension — together with shape, describes how flat memory maps to a multi-dimensional
  view.
- **Contiguous**: a tensor whose elements, in the order the current shape/stride imply,
  are laid out sequentially in memory — a precondition for `.view()`.
- **Broadcasting**: automatic, copy-free shape expansion allowing operations between
  tensors of compatible but different shapes.
