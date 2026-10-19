# `nn.Module` and Losses

Part of the [PyTorch Fundamentals companion docs](README.md). Paired with the
`# nn.Module and Losses` section of
[`../torch_hands_on_reference.ipynb`](../torch_hands_on_reference.ipynb). Builds on
[Chapter 2](02_autograd.md) — a model's weights are exactly the leaf tensors autograd
tracks; `nn.Module` is the organizing structure around them.

## In Plain English

A real model has many weight tensors — one set per layer — that all need to be created,
tracked, moved to the right device together, saved, and loaded together. `nn.Module` is
PyTorch's base class for organizing that: subclass it, register your layers/parameters in
`__init__`, define the forward computation in `forward()`, and PyTorch handles the
bookkeeping (finding every parameter for the optimizer, moving them all to a device with
one `.to()` call, saving/loading them all together) automatically.

## The First-Principles Explanation

### The two things every `nn.Module` subclass does

```python
class TinyMLP(nn.Module):
    def __init__(self, in_features, hidden, out_features):
        super().__init__()
        self.fc1 = nn.Linear(in_features, hidden)
        self.fc2 = nn.Linear(hidden, out_features)

    def forward(self, x):
        x = F.relu(self.fc1(x))
        return self.fc2(x)
```

`__init__` **registers** submodules — assigning an `nn.Module` (like `nn.Linear`) to
`self.anything` triggers `nn.Module`'s overridden `__setattr__`, which recognizes it's a
module and adds it to an internal registry. This is *why* `model.parameters()` can find
every weight in a deep, nested model without you manually listing them — it recursively
walks that registry. `forward()` defines what actually happens to an input — the one
method every subclass must implement.

### `model(x)`, not `model.forward(x)` — a real, checkable difference

```python
model(x)          # correct, standard usage
model.forward(x)  # works here too, but silently skips hooks
```

`nn.Module.__call__` (which is what actually runs when you write `model(x)`) does
bookkeeping around `forward()` — most importantly, firing any registered forward hooks
(used for things like activation inspection, debugging, or feature extraction in larger
projects). Calling `.forward()` directly bypasses `__call__` entirely, so those hooks
silently never fire — confirmed directly: registering a forward hook and calling
`model(x)` fires it; calling `model.forward(x)` with the identical input does not. This is
why `model(x)` is the convention, not a stylistic preference — `.forward(x)` is a real,
different (more limited) code path.

### `parameters()` and `state_dict()` — what the optimizer sees vs. what gets saved

```python
model.named_parameters()  # -> fc1.weight (8,4), fc1.bias (8,), fc2.weight (2,8), fc2.bias (2,)
model.state_dict()        # same tensors, keyed the same way, as an ordered dict
```

`parameters()` (or `named_parameters()`, same thing plus names) is what you hand to an
optimizer (`torch.optim.AdamW(model.parameters(), lr=...)` — see
[Chapter 4](04_optimizers_and_training_loop.md)) — every leaf tensor the optimizer is
allowed to update. `state_dict()` is the save/load format: the exact same tensors, as a
plain dict, which is what `torch.save(model.state_dict(), path)` writes to disk and
`model.load_state_dict(torch.load(path))` restores — this is the *only* thing
`from_scratch/tinystories-gpt-6m/train.py`'s checkpointing (elsewhere in this workspace)
actually persists, not the whole Python object.

### Losses: what they compute, and the CrossEntropyLoss gotcha that trips almost everyone up once

`nn.MSELoss()` computes exactly what the name says — mean squared error between prediction
and target, elementwise. `nn.CrossEntropyLoss()` is the one worth being precise about,
because its *input* format is easy to get wrong:

```python
logits = torch.randn(5, 3)               # raw, unnormalized scores — NOT softmax'd
target = torch.tensor([0, 2, 1, 1, 0])   # class INDICES — NOT one-hot vectors

loss = nn.CrossEntropyLoss()(logits, target)
# internally identical to:
manual = F.nll_loss(F.log_softmax(logits, dim=1), target)
# confirmed: torch.allclose(loss, manual) is True
```

`CrossEntropyLoss` **applies `log_softmax` internally** — it expects raw logits straight
out of your model's last linear layer, not probabilities you've already softmax'd
yourself. Softmaxing your logits before passing them in is a real, common bug: it doesn't
error, it just silently applies softmax *twice*, producing an over-flattened distribution
and a subtly wrong (usually too-small, slower-to-learn-from) loss signal.

## Grounded in the Notebook

The `# nn.Module and Losses` section builds `TinyMLP` exactly as shown above, confirms the
hook-firing difference directly (not just described), and verifies `CrossEntropyLoss`
against the manual `log_softmax` + `nll_loss` computation for real, on real random data.

## Deep-Dive: Why `__setattr__` Magic, Instead of an Explicit `register_module()` Call

It would be more "explicit" for `nn.Module` to require `self.register_module("fc1",
nn.Linear(...))` instead of the plain `self.fc1 = nn.Linear(...)` that actually works. The
overridden `__setattr__` trades a small amount of "magic" for a large ergonomics win:
model definitions read exactly like ordinary Python attribute assignment (because they
are), with zero extra ceremony, while still giving `nn.Module` everything it needs
(iterating `self.__dict__`'s registered-modules bucket) to implement `parameters()`,
`.to(device)`, `state_dict()`, and `.train()`/`.eval()` mode-switching recursively across
an arbitrarily deep, nested model — all without the model author writing any of that
bookkeeping by hand.

## Try It Yourself

- Add a third `nn.Linear` layer to `TinyMLP` and confirm `model.parameters()` picks it up
  automatically with no other code changes.
- Deliberately pass already-softmax'd probabilities into `nn.CrossEntropyLoss()` instead of
  raw logits, and compare the resulting loss value to the correct (logits-in) version on
  the same data — see the silent difference for yourself.
- Register a **forward pre-hook** (`register_forward_pre_hook`) instead of a forward hook,
  and confirm when it fires relative to `forward()` actually running.

## Common Misconceptions

- **"You should call `model.forward(x)` since that's the method you defined."** Call
  `model(x)` — `.forward()` skips PyTorch's own bookkeeping (hooks), a real, verifiable
  behavioral difference, not just a style preference.
- **"`nn.CrossEntropyLoss` expects probabilities (post-softmax) as input."** It expects raw
  logits — it applies `log_softmax` internally itself.
- **"`state_dict()` and `parameters()` return different data."** Same underlying tensors,
  different framing: `parameters()` for the optimizer (an iterable, or named iterable),
  `state_dict()` for serialization (a dict, matching what `torch.save`/`load_state_dict`
  need).

## Practice Questions

1. Why does assigning `self.fc1 = nn.Linear(...)` inside `__init__` make `fc1` show up in
   `model.parameters()` automatically — what mechanism makes this work?
2. What specifically goes wrong, numerically, if you pass softmax'd probabilities into
   `nn.CrossEntropyLoss()` instead of raw logits? (Hint: think about what `log_softmax`
   does to an input that's already a valid probability distribution.)
3. You save a model with `torch.save(model.state_dict(), "model.pt")`. What do you need
   *besides* that file to correctly restore a usable model later?

## Key Terms

- **`nn.Module`**: PyTorch's base class for a layer or model; subclasses register
  parameters/submodules in `__init__` and define computation in `forward()`.
- **Logits**: raw, unnormalized model outputs — what `nn.CrossEntropyLoss` expects as
  input, before any softmax is applied.
- **`state_dict()`**: an ordered dict of a model's parameter/buffer tensors, the format
  used for saving and loading.
- **Forward hook**: a function registered to run automatically whenever `model(x)` (via
  `__call__`) executes — silently skipped if `.forward()` is called directly instead.
