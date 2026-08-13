# PyTorch Exploration

A from-first-principles PyTorch tutorial: tensors → autograd → `nn.Module` → losses →
optimizers → a full, minimal, real training loop. Two halves that stay in sync:

- **[`torch_hands_on.ipynb`](torch_hands_on.ipynb)** — the hands-on notebook: runnable
  code, short inline commentary, and "Try It Yourself" prompts to extend once you're
  reading and re-running this on your own.
- **[`docs/`](docs/)** — the companion first-principles explanations: the math/mechanism
  behind each notebook section, why PyTorch's API is shaped the way it is, common
  misconceptions, and practice questions. Same house style as
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
uv run jupyter lab   # opens torch_hands_on.ipynb
```

Read [`docs/README.md`](docs/README.md) first for the reading order, then work through
`torch_hands_on.ipynb` top to bottom — each notebook section links back to its docs
chapter at the point where the concept needs the full explanation.

## What's here

- `torch_hands_on.ipynb` — the tutorial notebook (Tensors → Autograd → `nn.Module`/Losses
  → Optimizers/Training Loop).
- `docs/` — first-principles companion chapters, one per notebook section.
- `src/pytorch_exploration/` — empty project scaffold from `uv init`, not part of the
  tutorial itself.
