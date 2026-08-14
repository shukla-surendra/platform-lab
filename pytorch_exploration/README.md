# PyTorch Exploration

A from-first-principles PyTorch tutorial: tensors → autograd → `nn.Module` → losses →
optimizers → a full, minimal, real training loop. Three parts that stay in sync:

- **[`pytorch_notes.ipynb`](pytorch_notes.ipynb)** — personal working notes: built up
  live, in your own words, at your own pace — the primary place to actually learn by
  doing.
- **[`torch_hands_on_reference.ipynb`](torch_hands_on_reference.ipynb)** — a complete
  reference run-through (Tensors → Autograd → `nn.Module`/Losses → Optimizers/Training
  Loop), companion to `docs/`, useful to compare against or pull from when extending your
  own notes.
- **[`docs/`](docs/)** — the companion first-principles explanations: the math/mechanism
  behind each topic, why PyTorch's API is shaped the way it is, common misconceptions, and
  practice questions. Same house style as
  [`mini-llms-playground/docs/llm-engineering/`](../../mini-llms-playground/docs/llm-engineering/) —
  see [`docs/README.md`](docs/README.md) for the full chapter list and reading order.

## Why this exists, and how it relates to the rest of the workspace

This is the **mechanics-of-PyTorch-itself** layer — tensors, autograd, `nn.Module`,
training loops — underneath everything else already built on PyTorch elsewhere in this
workspace:
[`mini-llms-playground/from_scratch/`](../../mini-llms-playground/from_scratch/)'s
from-scratch GPT models,
[`local_llms/vit/`](../local_llms/vit/)'s ViT experiments, and the fine-tuning scripts
under `mini-llms-playground/fine_tuning/` all assume the fundamentals covered here. Where
useful, docs here cross-link to those real, larger examples so a mechanism isn't just
explained in the abstract — you can see the exact same API used at production-model scale
elsewhere in this workspace.

## Quickstart

```bash
cd platform-lab/pytorch_exploration
uv sync
uv run jupyter lab   # opens pytorch_notes.ipynb
```

Read [`docs/README.md`](docs/README.md) for the reading order, then work through
`pytorch_notes.ipynb` — each section links to its docs chapter (and, where useful, to
`torch_hands_on_reference.ipynb`) at the point where a concept needs the full explanation.

## What's here

- `pytorch_notes.ipynb` — personal working notes, actively evolving.
- `torch_hands_on_reference.ipynb` — a complete, executed reference notebook (Tensors →
  Autograd → `nn.Module`/Losses → Optimizers/Training Loop).
- `docs/` — first-principles companion chapters, one per topic.
- `src/pytorch_exploration/` — empty project scaffold from `uv init`, not part of the
  tutorial itself.
