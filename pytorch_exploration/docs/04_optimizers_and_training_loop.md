# Optimizers and the Training Loop

Part of the [PyTorch Fundamentals companion docs](README.md). Paired with the
`# Optimizers and the Training Loop` section of
[`../torch_hands_on.ipynb`](../torch_hands_on.ipynb). Builds on
[Chapters 2](02_autograd.md) and [3](03_nn_module_and_losses.md) — gradients
(`.backward()`) plus a structured set of learnable parameters (`nn.Module`) are the two
ingredients this chapter finally assembles into an actual training loop.

## In Plain English

Autograd computes gradients; it doesn't *use* them. An optimizer is the piece that takes a
computed gradient and actually updates each parameter to reduce the loss. The training
loop is just that update, repeated: show the model some data, measure how wrong it is,
compute gradients, update the weights a little, repeat — the same four-step cycle from
[Chapter 3 of the LLM curriculum](../../../mini-llms-playground/docs/llm-engineering/03_how_neural_networks_learn.md),
now assembled from the actual PyTorch pieces instead of described abstractly.

## The First-Principles Explanation

### The loop, exactly

```python
for step in range(num_steps):
    optimizer.zero_grad()        # clear accumulated gradients (Chapter 2's accumulation!)
    pred = model(X)              # forward pass
    loss = loss_fn(pred, y)      # how wrong is the model right now
    loss.backward()              # compute gradients (autograd)
    optimizer.step()             # actually update the parameters
```

Each line does exactly one job, and the order matters: `zero_grad()` must come before
`backward()` (otherwise this step's gradient adds onto whatever was left from before —
[Chapter 2](02_autograd.md)'s accumulation behavior, here as a bug rather than a feature);
`backward()` must come before `step()` (there's nothing to apply yet without it).

**A real, worked example** — linear regression on synthetic data, `y = 2x + 3 + noise`,
fit with plain SGD:

```python
model = nn.Linear(1, 1)
optimizer = torch.optim.SGD(model.parameters(), lr=0.01)
loss_fn = nn.MSELoss()
# ... 200 steps of the loop above ...
```

Actually run: loss starts at **76.98** (a freshly-initialized, untrained linear layer is
just guessing) and drops to **0.235** after 200 steps; the learned weight/bias end up at
**w=1.984, b=2.927** — closely matching the true `w=2.0, b=3.0` the synthetic data was
generated from. This is the entire mechanism, genuinely, at the smallest possible scale:
the same loop trains every larger model in this workspace.

### SGD vs. AdamW — what actually differs, mechanically

- **SGD**: the update is literally `param -= lr * grad` (optionally with momentum, a
  running average of past gradients that smooths the update direction). Simple, one
  hyperparameter (`lr`) to get right, but sensitive to that choice and slow to converge on
  many real problems.
- **Adam / AdamW**: maintains a per-parameter running average of both the gradient
  (momentum) *and* the squared gradient (an adaptive, per-parameter effective learning
  rate — parameters with historically large/noisy gradients get smaller effective steps,
  and vice versa). **AdamW** specifically decouples weight decay (L2-style regularization)
  from the gradient-based update itself, applying it as a separate, direct shrink of the
  weights each step rather than folding it into the gradient the adaptive averaging
  operates on — a fix for a real, once-common bug in plain Adam+L2, where the adaptive
  scaling and the regularization interacted in an unintended way. This is why
  `torch.optim.AdamW`, not `Adam`, is the default choice in nearly every modern training
  script in this workspace (including `mini-llms-playground/from_scratch/tinystories-gpt-6m/train.py`).

### `model.train()` / `model.eval()` — not about gradients, about layer *behavior*

A common confusion: this mode switch has nothing to do with `torch.no_grad()` — it's a
separate concern, and some layers (`nn.Dropout`, `nn.BatchNorm*`) genuinely *behave
differently* depending on it:

```python
dm = DropoutDemo()   # a single nn.Dropout(0.5)
x = torch.ones(10)
dm.train(); dm(x)   # tensor([2., 0., 2., 0., 2., 0., 2., 2., 2., 0.]) — randomly zeroed, survivors scaled by 1/(1-p)=2
dm.eval();  dm(x)   # tensor([1., 1., 1., 1., 1., 1., 1., 1., 1., 1.]) — dropout OFF entirely, unscaled passthrough
```

In training mode, dropout randomly zeroes ~50% of activations and scales the survivors up
by `1/(1-p)` (so the *expected* output magnitude stays the same either way — this is
"inverted dropout," the standard implementation) — a regularization technique that
prevents the network from over-relying on any single unit. In eval mode, dropout does
nothing at all — you want the model's actual, deterministic best guess at inference time,
not an artificially noised one. Forgetting `.eval()` before evaluation/inference is a real,
common bug that silently makes eval-time predictions noisy and non-deterministic for no
good reason.

### The memorization sanity check — a real debugging technique, not just an exercise

A genuinely useful habit before trusting a larger training run: can the model perfectly
memorize a *tiny* slice of the data (8-16 examples) if you train on nothing else for long
enough? If it can't, something is wrong in the model/loss/data pipeline *before* you spend
time worrying about generalization at all.

```python
Xtiny = torch.randn(8, 4)
ytiny = torch.randint(0, 2, (8,))
tiny_model = nn.Sequential(nn.Linear(4, 16), nn.ReLU(), nn.Linear(16, 2))
optimizer = torch.optim.AdamW(tiny_model.parameters(), lr=0.01)
# ... 300 steps ...
```

Actually run: final accuracy on those same 8 examples reaches **1.0** (perfect
memorization), final loss **0.0012** — confirming the model/loss/optimizer wiring is
correct before ever worrying about whether it generalizes to new data, a distinct, later
concern.

## Grounded in the Notebook

The `# Optimizers and the Training Loop` section runs the full linear-regression example
above for real (including plotting the loss curve — the "visual" step worth doing, not
just trusting a single final number), the dropout train/eval demonstration, and the
memorization sanity check on a tiny classification model.

## Deep-Dive: Why `zero_grad()` Isn't Automatic

Given how often forgetting `zero_grad()` is the actual bug, why doesn't PyTorch just clear
gradients automatically before every `backward()`? Because accumulation is a genuine,
intentional feature, not just an unfortunate default — it's exactly the mechanism gradient
*accumulation* (simulating a larger batch than fits in memory, by summing several
micro-batches' gradients before one `optimizer.step()`) depends on, a real technique used
throughout this workspace's larger training scripts. Making the *default* loop's most
common bug possible is the cost of keeping that legitimate, more advanced use case simple
to express — the same one-line mechanism serves both, and which one you get is entirely
determined by *when* you choose to call `zero_grad()`.

## Try It Yourself

- Rerun the linear regression example with `torch.optim.AdamW` instead of `SGD` (same
  `lr`) and compare how many steps each needs to reach a similar loss — a direct,
  hands-on feel for the "adaptive per-parameter step size" difference described above.
- Add an `nn.BatchNorm1d` layer to a small model and inspect its behavior difference
  between `.train()` and `.eval()` mode the same way the dropout demo does — BatchNorm's
  train/eval difference is mechanically different from dropout's (running statistics vs.
  randomness) even though the *API* (`.train()`/`.eval()`) is identical.
- Deliberately break the memorization sanity check (e.g., use a learning rate far too
  small, or too few training steps) and confirm accuracy stays low — get a feel for what
  "this pipeline has a real bug" looks like versus "this just needs more steps."

## Common Misconceptions

- **"`loss.backward()` updates the model's weights."** It only computes gradients and
  stores them in `.grad` — `optimizer.step()` is the line that actually changes any
  weight.
- **"`model.eval()` disables gradient computation."** It doesn't — that's `torch.no_grad()`
  or `.requires_grad_(False)`, a separate concern. `.eval()` only changes *layer behavior*
  (dropout, batchnorm); it's common, and often correct, to combine `model.eval()` with
  `torch.no_grad()` together, but they're not the same mechanism.
- **"AdamW is just Adam with a bit of L2 regularization added on."** The "decoupled" part
  of the name is the actual point — AdamW's weight decay is deliberately *not* folded into
  the gradient the adaptive averaging operates on, a specific fix for a specific
  interaction bug in plain Adam+L2.

## Practice Questions

1. Trace through what happens, step by step, if `optimizer.zero_grad()` is accidentally
   called *after* `loss.backward()` instead of before it, in a loop that runs for several
   steps.
2. Why does dropout scale surviving activations by `1/(1-p)` during training instead of
   leaving them unscaled?
3. A model achieves near-zero loss on 8 memorized examples but the loss never drops below
   a high plateau on the full real dataset. Is the memorization check result reassuring
   or concerning here, and why — what has it actually ruled out, and what hasn't it?

## Key Terms

- **Optimizer**: the object that applies computed gradients to update parameters
  (`SGD`, `Adam`, `AdamW`, ...) — distinct from autograd, which only computes gradients.
- **Momentum**: a running average of past gradients used to smooth/accelerate an
  optimizer's update direction.
- **Decoupled weight decay (AdamW)**: applying weight decay as a direct shrink of the
  weights, separate from the adaptive gradient-based update — the fix AdamW makes over
  plain Adam + L2 regularization.
- **Train/eval mode**: a model-wide switch (`.train()`/`.eval()`) changing the behavior of
  specific layers (`Dropout`, `BatchNorm`) — unrelated to gradient tracking.
- **Memorization sanity check**: training on a tiny data subset to confirm the
  model/loss/optimizer pipeline is wired correctly, before trusting results on the full
  dataset.
