# Fine-tuning an LLM

## The layman version

A pretrained model already "knows" a lot — it read a huge slice of the internet during
pretraining. Fine-tuning doesn't start over; it takes that already-knowledgeable model and
keeps teaching it, using a much smaller, purpose-built set of examples, so it gets better at
one specific thing (a task, a style, a domain) without relearning everything from scratch.
Think of it like a generalist doctor doing a specialty fellowship — they don't forget general
medicine, they build a narrower, deeper skill on top of what they already know (and, same as a
real fellowship, doing it badly can make them worse at the general stuff too — that's
catastrophic forgetting, covered below).

## What it is, mechanically

Continue gradient descent on a pretrained model's weights, using a smaller, task/domain-specific
dataset, instead of training from random init. The pretrained weights are the starting point;
backprop still runs the same way (forward pass → loss → backward pass → optimizer step) — the
only things that change are the data distribution, the learning rate (much lower), and usually
which weights are allowed to move.

## The real decision: which weights move

This is the fork that separates a junior answer from a senior one — "fine-tuning" is not one
technique.

- **Full fine-tuning** — every parameter is trainable. Needs optimizer state (Adam: ~2 extra
  copies of every param for momentum/variance) + gradients + activations in memory alongside the
  weights themselves. For a 7B model in fp32 that's roughly weights (28GB) + gradients (28GB) +
  Adam states (56GB) before activations — multi-GPU territory even at 7B. Rarely justified
  outside cases where the target domain is far from pretraining data (e.g., a biomedical model
  from a general-purpose base) and you have the budget.
- **LoRA (Low-Rank Adaptation)** — freeze the base weights, inject small trainable low-rank
  matrices (rank `r`, typically 8–64) into specific layers (usually attention Q/K/V/O
  projections, sometimes MLP). Trainable params drop to <1% of the model. Optimizer state shrinks
  proportionally. The update is `W + BA` where `B`, `A` are the low-rank pair — at inference you
  either merge them into `W` (zero extra latency, but locks in one adapter) or keep them separate
  (small latency cost, but lets you hot-swap adapters per tenant/task on one base model).
- **QLoRA** — LoRA on top of a 4-bit quantized frozen base (NF4 quantization + double
  quantization + paged optimizers). This is what makes fine-tuning a 65B-class model feasible on
  a single 48GB GPU. The quantization only touches the frozen base; the LoRA adapters still train
  in bf16, so quality loss vs full LoRA is small.
- **Adapters / prefix-tuning / prompt-tuning** — other parameter-efficient fine-tuning (PEFT)
  variants, less common now than LoRA/QLoRA but same underlying motivation: touch few parameters,
  keep the base frozen and reusable.
- **RLHF / DPO** — a different *stage*, not a different mechanism for the fine-tune step itself.
  SFT (supervised fine-tuning on instruction/response pairs) usually comes first; RLHF (reward
  model + PPO) or DPO (direct preference optimization, no separate reward model) comes after, to
  align behavior to preferences rather than just imitate demonstrations.

## Before touching weights at all: is fine-tuning even the right lever

A senior-level answer opens with this, not with LoRA hyperparameters:

- **New facts / frequently-changing knowledge** → RAG, not fine-tuning. Fine-tuning bakes
  knowledge into weights; it doesn't cheaply update, and models are generally worse at *reciting*
  injected facts than at *using* facts placed in context.
- **Style, format, domain vocabulary, task behavior, reasoning pattern** → fine-tuning is the
  right lever; this is behavior the model should exhibit unprompted, not something you want to
  pay context-window cost to re-supply every request.
- **A narrow, well-specified task with high-quality few-shot examples and low request volume** →
  prompting/few-shot may get you 90% of the way for a fraction of the engineering cost. Fine-tune
  when you need that behavior at high volume without paying the few-shot token tax every call, or
  when few-shot in-context isn't reliably steering behavior.
- **Distillation** is a related but distinct lever: training a smaller model to mimic a larger
  one's outputs, usually for latency/cost, not for adapting to new behavior per se.

## The production pipeline

1. **Data curation** — the actual bottleneck in most real fine-tunes, not compute. Format as
   instruction/response pairs matching the chat template the base model expects (mismatched
   special tokens/chat template is a common silent failure). Dedup, quality-filter, check for
   eval-set leakage into training data.
2. **Method selection** — LoRA/QLoRA by default unless you have a specific reason (deep domain
   shift, or you need the adapter fully merged with no adapter-serving infra). Pick target
   modules and rank based on task complexity — higher `r` for tasks needing broader behavioral
   change, low `r` (8–16) is often enough for style/format adaptation.
3. **Training config** — learning rate 1–2 orders of magnitude below pretraining LR (roughly
   1e-5–2e-4 depending on method and model size), short schedule (1–3 epochs is typical; more
   risks overfitting on a dataset far smaller than pretraining corpus), warmup, gradient
   checkpointing to trade compute for memory when needed.
4. **Distributed strategy**, sized to what actually needs to fit: DeepSpeed ZeRO (stage 2/3) or
   FSDP for full fine-tuning at scale; often unnecessary for LoRA/QLoRA on models that fit a
   single node.
5. **Eval, not just loss** — held-out task metric, and just as importantly, a regression check
   against the base model's general capabilities. A fine-tune that improves the target task while
   quietly degrading everything else is the catastrophic-forgetting failure mode below.
6. **Serving decision** — merge adapter into base (simpler, faster, one model per task) vs. serve
   adapters separately and swap per request (one base model in memory, N adapters hot-loaded —
   the multi-tenant/multi-task pattern).
7. **Rollout** — canary/shadow against the current production model before full cutover, same as
   any model deployment; fine-tuned models are not exempt from the usual shadow-mode +
   drift-monitoring discipline.

## Failure modes worth having a ready answer for

- **Catastrophic forgetting** — the model gets better at the fine-tune task and worse at
  everything else. Mitigate with low LR, few epochs, LoRA (bounds how far weights can move by
  construction), or replaying a slice of general-purpose data alongside the task data.
- **Overfitting on a small fine-tune set** — fine-tune datasets are often thousands, not billions,
  of examples; the model can memorize rather than generalize. Watch train/val divergence, keep
  epochs low.
- **Reward hacking** (RLHF/DPO stage) — the model optimizes the reward signal in ways that don't
  reflect the actual intended behavior (e.g., verbosity as a proxy for "helpfulness" if the reward
  model wasn't controlled for length).
- **Tokenizer/chat-template mismatch** — fine-tuning with the wrong special tokens or prompt
  format silently produces a model that performs worse than the base at inference, even though
  training loss looked fine.

## Catastrophic forgetting across multiple instruction datasets, not just pretrain→fine-tune

The layman version: think of someone learning to give directions. Train them for a week using
only highway-driving examples and they get sharp at highway directions — but if you then
spend the next week training them only on subway-navigation examples, by the end of that
second week their highway skill has quietly eroded, even though nobody told them to forget it.
Nothing in week 2 rewards keeping week-1 behavior, so it just drifts away.

Mechanically this is the same mechanism as pretrain→fine-tune forgetting above, but sharper
for sequential *instruction* datasets specifically, because what erodes isn't just factual
recall — it's the model's learned response-format/behavior prior (tone, verbosity, when to
refuse, answer structure). Dataset2's gradients only ever see dataset2's shape; nothing in the
loss penalizes drifting off dataset1's behavior, so held-out dataset1 loss rises again by the
end of the dataset2 phase even though dataset1's data still physically exists on disk —
training *order*, not data availability, is the cause. Worked through with a concrete
tiny-GPT project in
`mini-llms-playground/from_scratch/custom-gpt-10m/docs/LLM_DEV_GUIDE.md` section 18.

Detecting it early: keep a held-out validation split *per source dataset*, not one combined
split — eval against each independently every N steps, so a rising dataset1 loss during the
dataset2 phase shows up immediately instead of being averaged away by the combined number.

Mitigations, same menu as fine-tuning forgetting: shuffle both datasets into one joint stream
instead of phase-by-phase training (removes the forgetting phase entirely, at the cost of
never getting a clean "task-1-only" checkpoint); low LR + few epochs per phase if sequential
is required by the workflow; replay a slice of dataset1 into dataset2's batches; LoRA/adapters
per task if both behaviors need to stay independently swappable rather than merged into one
set of weights.

## The follow-up an interviewer goes to next

- *"70B model, one GPU budget — what do you do?"* → QLoRA: 4-bit NF4 quantized frozen base +
  bf16 LoRA adapters + gradient checkpointing + gradient accumulation to simulate a larger batch.
- *"Fine-tune vs RAG — how do you actually decide, not just in theory?"* → What changes: is it
  the model's *behavior* (fine-tune) or its *knowledge* (RAG)? How often does the underlying
  information change? What's the cost of a wrong/stale answer vs. the cost of the fine-tune
  iteration loop?
- *"How do you know the fine-tune didn't break anything else?"* → Held-out eval on the target
  task *and* a fixed regression suite against general capability, before and after — not just
  before/after loss on the fine-tune's own validation split.
