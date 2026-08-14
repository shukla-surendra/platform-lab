# PyTorch Fundamentals: Companion Docs

Four chapters, each paired with a section of
[`../torch_hands_on_reference.ipynb`](../torch_hands_on_reference.ipynb) — and, where the
same topic comes up, cross-linked from [`../pytorch_notes.ipynb`](../pytorch_notes.ipynb),
the personal working-notes notebook.
Same house style as
[`mini-llms-playground/docs/llm-engineering/`](../../../mini-llms-playground/docs/llm-engineering/00_roadmap.md):
**In Plain English** (a jargon-free first pass) → **The First-Principles Explanation**
(the actual mechanism, precisely) → **Grounded in the Notebook** (the exact cell/code) →
**Deep-Dive** (why it's built this way, the trade-offs) → **Try It Yourself** → **Common
Misconceptions** → **Practice Questions** → **Key Terms**.

| # | Chapter | Notebook section |
|---|---|---|
| 1 | [Tensors](01_tensors.md) | `# Tensors` |
| 2 | [Autograd](02_autograd.md) | `# Autograd` |
| 3 | [`nn.Module` and Losses](03_nn_module_and_losses.md) | `# nn.Module and Losses` |
| 4 | [Optimizers and the Training Loop](04_optimizers_and_training_loop.md) | `# Optimizers and the Training Loop` |

## Reading order

Straight through, 1 → 4 — each chapter builds on the last: tensors are what autograd
tracks, autograd is what makes `nn.Module`'s parameters learnable, and the training loop
is where all three finally come together into the four-step cycle (forward → loss →
backward → step) that trains every model in this workspace, from the tiny examples here to
the from-scratch GPTs in
[`mini-llms-playground/from_scratch/`](../../../mini-llms-playground/from_scratch/).

## How to use this alongside the notebooks

Work through `torch_hands_on_reference.ipynb` top to bottom. Each section has a short
markdown intro and runnable cells; when a concept needs the full mechanism explanation
(the math, the "why," the common misconceptions), it links to the matching chapter here
rather than repeating it inline — keeping the notebook itself lean and exploratory, and
the deep explanation in one place you can return to later. `pytorch_notes.ipynb` links
here too, at the same points, since it covers largely the same ground in your own words.
