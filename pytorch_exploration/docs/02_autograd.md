# Autograd

Part of the [PyTorch Fundamentals companion docs](README.md). Paired with the `# Autograd`
section of [`../torch_hands_on.ipynb`](../torch_hands_on.ipynb). Builds on
[Chapter 1](01_tensors.md) — everything below is about what PyTorch does *with* tensors
that have `requires_grad=True`.

## In Plain English

Training a model means adjusting its weights to reduce a loss — and knowing *which
direction* to adjust each weight requires the loss's gradient (derivative) with respect to
that weight. Computing that by hand for a model with millions of parameters is not
feasible. Autograd is PyTorch's system for computing every one of those gradients
automatically, by recording every operation performed on a tensor as it happens, then
walking that recording backward once you ask for gradients.

## The First-Principles Explanation

### The computation graph is built as you go, not declared in advance

Every time you do an operation on a tensor with `requires_grad=True`, PyTorch records that
operation as a node in a graph — dynamically, during the actual Python execution (this is
called "eager mode" / "define-by-run," as opposed to older frameworks that required
declaring the whole computation graph upfront before running anything). Each resulting
tensor gets a `grad_fn` pointing back to the operation that created it — except **leaf**
tensors (ones you created directly, not as the result of an operation on other
tracked tensors), which have `grad_fn = None` and are where gradients actually accumulate.

```python
a = torch.tensor(1.0, requires_grad=True)
b = a * 2
a.is_leaf   # True  — created directly
b.is_leaf   # False — the result of an operation
b.grad_fn   # <MulBackward0 object at ...> — remembers "b came from a multiplication"
```

### `.backward()`: walking the graph in reverse, applying the chain rule

Calling `.backward()` on a scalar tensor triggers **reverse-mode automatic
differentiation**: starting from that scalar, PyTorch walks the recorded graph backward,
applying the chain rule at every node, accumulating `d(loss)/d(x)` into `x.grad` for every
leaf tensor `x` with `requires_grad=True` that the graph passed through.

**A hand-verified example** — worth actually checking by hand once, so the mechanism
isn't a black box:

```python
x = torch.tensor(2.0, requires_grad=True)
y = torch.tensor(3.0, requires_grad=True)
z = (x * y) + x**2
z.backward()
```

By hand: `z = xy + x²`, so `∂z/∂x = y + 2x` and `∂z/∂y = x`. At `x=2, y=3`:
`∂z/∂x = 3 + 2(2) = 7`, `∂z/∂y = 2`. Running the code above: `x.grad == 7.0`,
`y.grad == 2.0` — autograd's answer matches the calculus exactly, because that's precisely
what it's doing under the hood, mechanically, not approximately.

### Gradients accumulate — `.backward()` never resets `.grad` for you

```python
x2 = torch.tensor(1.0, requires_grad=True)
for i in range(3):
    loss = x2 ** 2
    loss.backward()
    print(x2.grad)   # 2.0, then 4.0, then 6.0 — adding up, not overwriting
```

Each `.backward()` call **adds** the newly computed gradient into `.grad`, rather than
replacing it. This is a deliberate design choice (it's what makes gradient accumulation
across multiple mini-batches possible, as a feature — see
[Chapter 13 of the LLM curriculum](../../../mini-llms-playground/docs/llm-engineering/13_the_training_loop_mechanism_by_mechanism.md)
for a real, worked instance of exploiting exactly this). It's also the single most common
real training bug: forgetting to call `optimizer.zero_grad()` before the next
`.backward()`, silently mixing gradients from unrelated batches together.

### In-place operations can break the graph — this is enforced, not just a warning

```python
e = torch.tensor(2.0, requires_grad=True)
f = e * e
e.add_(1)       # modifying a leaf tensor that's needed for f's backward pass
f.backward()
# RuntimeError: a leaf Variable that requires grad is being used in an in-place operation.
```

Autograd sometimes needs a tensor's *original* value later, during the backward pass,
to compute a gradient correctly (here, `d(e*e)/de = 2e` needs `e`'s value at the time `f`
was computed). An in-place operation overwrites that value before backward runs, so
PyTorch raises loudly rather than silently returning a wrong gradient computed from the
mutated value.

### `torch.no_grad()` and `.detach()`: two ways to step outside the graph

```python
with torch.no_grad():
    h = g * 2
h.requires_grad   # False — no graph was built for this block at all

i_ = g.detach()
i_.requires_grad   # False, but i_.data_ptr() == g.data_ptr() — shares memory, no graph
```

`torch.no_grad()` is a context — nothing inside it gets tracked, useful for an entire
block (evaluation/inference, where no `.backward()` will ever be called). `.detach()`
returns a new tensor sharing the same underlying data but severed from the graph — useful
for pulling a single value out of a computation without carrying its whole history
forward (e.g., logging a loss value without keeping its graph alive in memory).

## Grounded in the Notebook

The `# Autograd` section of `torch_hands_on.ipynb` runs every example above for real,
including deliberately triggering the leaf-in-place `RuntimeError` so it's seen once,
directly, rather than only described.

## Deep-Dive: Why "Leaf Tensors" Are the Ones That Actually Accumulate Gradients

A subtlety worth internalizing: `.grad` only ever populates on **leaf** tensors with
`requires_grad=True` by default — intermediate (non-leaf) tensors compute gradients
*through* them during backward, but don't retain `.grad` afterward unless you explicitly
call `.retain_grad()` on them first. This is a memory optimization: keeping every
intermediate gradient in a deep network (every activation, every layer) would multiply
memory use enormously for values that are, in the overwhelming majority of real training
loops, never actually inspected — only the leaf parameters' gradients are what
`optimizer.step()` needs.

## Try It Yourself

- Extend the hand-verified example: add a `w = torch.tensor(4.0, requires_grad=True)` and
  compute `z = w * x * y + x**2`. Work out `∂z/∂w`, `∂z/∂x`, `∂z/∂y` by hand first, then
  confirm against `.backward()`.
- Deliberately forget a `zero_grad()` in a two-step loop (no optimizer needed — just call
  `.backward()` twice on a fresh computation using the same leaf tensor) and observe the
  accumulated (wrong, if you intended two independent gradients) result.
- Call `.retain_grad()` on a non-leaf tensor before `.backward()`, then inspect its `.grad`
  afterward — confirm it's populated, unlike the leaf-only default.

## Common Misconceptions

- **"`.backward()` resets `.grad` before computing the new gradient."** It doesn't —
  gradients accumulate by design; resetting is `optimizer.zero_grad()`'s job, not
  `.backward()`'s.
- **"In-place operations are always fine as long as you don't get an error."** Some
  in-place ops silently succeed but still produce wrong results in edge cases the eager
  checker doesn't always catch — as a habit, prefer out-of-place ops on any tensor that
  participates in a graph you'll call `.backward()` on, rather than relying on the error
  checker to catch every case.
- **"`torch.no_grad()` and `.detach()` do the same thing."** Close, but not identical:
  `no_grad()` is a context affecting everything inside it; `.detach()` returns a specific
  new tensor severed from the graph, usable outside any context manager, still sharing
  memory with the original.

## Key Terms

- **Computation graph**: the record of operations connecting tensors, built dynamically as
  code runs (define-by-run), walked backward by `.backward()`.
- **`grad_fn`**: a non-leaf tensor's pointer back to the operation that produced it.
- **Leaf tensor**: a tensor created directly (not as the result of a tracked operation) —
  the only tensors that accumulate `.grad` by default.
- **Reverse-mode automatic differentiation**: computing gradients by walking the
  computation graph from output back to inputs, applying the chain rule at each step.
- **`torch.no_grad()` / `.detach()`**: two mechanisms for excluding computation from
  gradient tracking — a context manager, and a graph-severed tensor view, respectively.
