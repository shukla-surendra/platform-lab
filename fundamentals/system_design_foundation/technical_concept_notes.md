# Technical Concept Notes — Index

Running concept notes, added as questions come up. Mechanism first, layman explanation before
the mechanics — not phrased as Q&A, not labeled by source. Companion to `mlops-question-bank.md`
(that one is a rep source with answers withheld on purpose; these are reference material you
actually read).

Split into per-topic files once a topic accumulates enough sub-questions to earn its own file —
small/one-off topics stay here until they do.

## Topics with their own file

- [`finetuning_concept_notes.md`](finetuning_concept_notes.md) — fine-tuning methods (full,
  LoRA, QLoRA, RLHF/DPO), when to fine-tune vs. RAG/prompting, the production pipeline, failure
  modes (catastrophic forgetting, reward hacking, tokenizer mismatch).
- [`model_file_internals_concept_notes.md`](model_file_internals_concept_notes.md) — what's
  literally inside a checkpoint file (`.pth`/`state_dict`), reading/modifying it, the pickle
  security risk and why `.safetensors` exists, the wider format landscape (`.bin`, `.ckpt`,
  `.h5`, `.onnx`, `.gguf`, `.msgpack`), splitting a model across files (storage sharding vs.
  tensor/pipeline parallelism), what fine-tuning does to the file on disk, and the anatomy of a
  real downloaded HuggingFace model folder.
- **PostgreSQL, principal-engineer depth** — lives in `platform-lab/mlops_aiops/docs/tools/postgresql/`
  (not this folder, since it's paired with runnable query examples rather than being pure
  reference prose): joins and physical join/distributed-join algorithms, the query optimizer
  and planner cost model, indexing, window functions and recursive CTEs
  (`README.md`); physical storage — pages, tuples, TOAST, visibility/freeze maps, WAL,
  checkpoints (`storage-internals.md`); MVCC, isolation levels, write skew, locking, deadlocks,
  `VACUUM`/bloat, XID wraparound (`concurrency-and-locking.md`); logical vs. physical backups,
  PITR, streaming replication, replication slots, `synchronous_commit`, Patroni/repmgr/pgpool
  HA orchestration (`backup-recovery-and-replication.md`); roles/RBAC, row-level security,
  `pg_hba.conf`, encryption boundaries, auditing (`security-and-access-control.md`); a
  40-scenario query-pattern library (`query-patterns.md`); and RDS vs. Aurora, connection
  pooling, schema lifecycle at scale, zero-downtime migrations (`production-and-scaling.md`).
- **Microservices, production edge cases** — lives in
  `platform-lab/mlops_aiops/docs/tools/microservices/`, complementary to (not a duplicate
  of) `00_prerequisite_concepts/20_microservices_architecture_patterns.md`'s architectural
  patterns (service discovery, strangler fig, event sourcing, CQRS): the core
  function-call-vs-network-call trade-off, timeouts, idempotency keys, retry storms and
  exponential-backoff-with-jitter, circuit breakers/bulkheads/backpressure/load shedding
  (`README.md`); the dual-write problem, the outbox pattern, and sagas (choreography vs.
  orchestration) for cross-service consistency (`README.md`); API contract versioning and
  consumer-driven contract testing, distributed tracing/correlation IDs, deployment safety
  (canary/blue-green/feature flags), service-to-service auth (mTLS) and secret sprawl,
  Conway's Law and the distributed-monolith anti-pattern, a concrete anti-pattern catalog
  (shared database, chatty services, config drift), and a principal-engineer checklist for
  when *not* to use microservices at all (`production-pitfalls-and-operations.md`).
- **ML fundamentals, NumPy, scikit-learn, distributed classical ML** — lives in
  `platform-lab/mlops_aiops/docs/tools/{numpy,scikit-learn}/` and
  `platform-lab/mlops_aiops/docs/tools/spark/distributed-ml-with-mllib.md`, all live-verified
  against real code, not duplicated from `01_ml_system_design/07_distributed_training_serving.md`
  (that one is distributed *deep learning* — DDP/FSDP/Ray; this is distributing *classical* ML
  and the classical-ML theory itself, genuinely different territory): ndarray memory layout
  (strides, views vs. copies), broadcasting, vectorization, dtype promotion gotchas
  (`numpy/README.md`); the Estimator/Pipeline/ColumnTransformer API and a hands-on tour of
  core algorithms (`scikit-learn/README.md`); bias-variance made concrete via a real
  underfit/good-fit/overfit run, L1 vs. L2 regularization's exact-zero-vs-shrinkage mechanism,
  gradient descent from scratch (including a real divergence at too-high a learning rate),
  why a single train/test split can swing 17 points of accuracy, the imbalanced-data accuracy
  trap (a 93.8%-accurate model with 0.0 recall), and grid vs. random hyperparameter search
  (`scikit-learn/ml-fundamentals-deep-dive.md`); and how classical algorithms actually
  distribute across a Spark cluster — linear models via distributed gradient sums, trees via
  distributed histogram split-finding, and why exact k-NN/non-linear SVMs don't distribute at
  all (`spark/distributed-ml-with-mllib.md`).
- **Ray Core (tasks and actors)** — lives in `platform-lab/mlops_aiops/docs/tools/ray/`,
  live-verified, the layer beneath what `01_ml_system_design/07_distributed_training_serving.md`
  already covers architecturally (Ray Train/Serve, parallelism strategies, the object-store
  disk-spill failure mode): `@ray.remote` tasks/futures and `ray.get` (a real 3.82x speedup
  on 8 tasks over 4 cores), `ray.put` and the shared-memory object store (why a large shared
  input should be put once, not re-serialized per task), actors as single-threaded
  long-lived state (safe concurrent counters with no explicit lock), two real positive use
  cases (parallel hyperparameter search, 1.8x; an embarrassingly-parallel Monte Carlo
  simulation, 3.25x) and — the more valuable half — a real *negative* result: a small-model
  actor-pool "serving" pattern that was 2x **slower** than calling `.predict()` locally,
  used to derive the actual rule (per-task dispatch overhead has to be smaller than the work
  being distributed, or distributing it only adds cost). Alternatives table vs. Dask/Spark/
  `concurrent.futures`/Celery/K8s Jobs also lives there.

## Everything else

New standalone topics get added here directly.

### RAG chunking strategies and knowledge staleness

Chunking exists because an embedding model compresses a block of text into one fixed-size
vector — too big a chunk and the vector blurs several ideas together (fuzzy retrieval); too
small and a chunk loses the context it needs to make sense on its own (a pronoun or referent
with nothing to point to). Every chunking strategy is a tradeoff knob between those two
failure modes.

In roughly increasing sophistication: fixed-size/sliding-window splitting with ~10-20%
overlap (cheap, ignores structure); recursive splitting that tries paragraph breaks, then
sentences, then words until a size target is hit; semantic chunking, walking sentence by
sentence and starting a new chunk when embedding similarity to the running chunk drops below
a threshold, which keeps topically coherent text together; structure-aware chunking that
splits on document structure itself (headers, tables, code blocks) so a table row or function
body never gets cut across two chunks; parent-child (small-to-big) retrieval, where small
chunks are indexed for precise vector matching but each points to a larger parent section
that's what actually gets sent to the LLM, solving "small chunk retrieves precisely but lacks
context" vs. "big chunk has context but retrieves imprecisely"; and late chunking (2024/2025),
which embeds the *whole document* first with a long-context embedding model and only slices
the resulting token embeddings afterward — because attention ran over the full document before
slicing, a chunk keeps context for pronouns/referents that plain pre-chunking would lose.
Production default most teams converge on: structure-aware recursive splitting at ~256-512
tokens with ~10-15% overlap, each chunk metadata-tagged with source/section/timestamp/version,
plus parent-document retrieval when answers need broader context.

Knowledge staleness is two separate mechanisms with different fixes, and the model itself
solves neither on its own. Parametric knowledge (baked into weights at training time) has no
internal clock or versioning — whatever the model saw during training is just "true" to it,
with no flag for "this may have changed since." The mild "as of my last update..." hedge in
newer models is a learned RLHF response pattern, not the model actually knowing what changed.
Retrieved knowledge (RAG context injected at inference) is where staleness is actually
solvable, but entirely in the pipeline, not the model: metadata at ingestion (created_at/
updated_at/version/status stored alongside the vector, not inside it), retrieval-time
filtering (the vector DB query excludes or downranks deprecated/superseded chunks before the
LLM ever sees them), recency-weighted ranking (blending semantic similarity with a time-decay
factor), superseding logic (a re-ingested doc marks the old chunk `replaced_by` the new one, so
retrieval never serves both and hands the model contradictory context), explicit "as of"
prompting (system prompt states today's date and which source wins on conflict — this only
works because the pipeline handed that fact to the model in-context), and freshness pipelines
(scheduled re-crawl or change-data-capture from the source system so the index doesn't rot).
The mental model: staleness detection is a retrieval-pipeline responsibility, not a model
capability — RAG exists to convert "hope the frozen weights are still right" into "look up
current truth every time."

### Pretraining/fine-tuning data chunking (packing) — distinct from RAG chunking above

This is a different problem from RAG chunking despite the shared word: not preserving
semantic coherence per chunk, but packing variable-length documents into fixed-length
training sequences for GPU efficiency. Training batches need uniform tensor shapes, but real
documents range from a 20-token tweet to a 200k-token book. Padding every document to the
context length wastes enormous compute (a 50-token doc padded to 4096 wastes ~98% of that
sequence). The standard fix, used by GPT-3, LLaMA, Pythia, OLMo and effectively every
production pretraining pipeline, is packing: concatenate many documents back-to-back into
one long token stream with a special `<EOS>`/`<|endoftext|>` token between them, then slice
the stream into fixed-length chunks with no regard for document boundaries. A single
training sequence can legitimately contain the tail of one document, an EOS token, then the
start of an unrelated one — the model isn't asked to reason coherently across the window,
it's doing next-token prediction everywhere, and EOS itself is a training signal for "content
changed here."

Nuance that's a real architecture decision, not a detail: naive packing lets a token attend
backward across the EOS boundary into the previous unrelated document (attention leakage).
More careful pipelines (LLaMA and most modern ones) apply document-level attention masking
inside the packed sequence so a token can only attend to earlier tokens from its own
document.

Pipeline order: exact/near-duplicate deduplication at the document level (MinHash/LSH,
suffix-array methods — skipping this causes memorization and wastes compute) happens before
tokenization (BPE/SentencePiece/tiktoken — chunking operates on token counts, not
characters), which happens before packing. Different sources (web, code, books, Wikipedia)
get different sampling/repetition weights at the dataset level (the data mixture), not the
chunk level. Many runs also use a sequence-length curriculum — shorter sequences early for
cheaper/faster training, then a dedicated later-stage long-context extension phase on longer
documents to reach the advertised 32k-128k context window, rather than that being baked in
from the start. Fine-tuning/SFT packing adds one more wrinkle: instruction examples packed
together are usually loss-masked, so the loss for one example's tokens isn't computed over
an unrelated example sharing the same packed sequence.

**Training-time knowledge staleness is a genuinely unsolved gap, not a handled case.**
Pretraining is next-token prediction over a mixture of text from many time periods with old
and new versions of facts co-mingled — there is no conflict-resolution step. What the model
ends up confidently predicting is driven by frequency in the training distribution, not
recency: if an old API was documented on 50,000 pages and the new one on 500 recent ones, the
old pattern wins by sheer statistical weight even though it's wrong now — this is the actual
mechanism behind confidently-outdated answers, not a reasoning failure the model could
correct. Some research pipelines experiment with prepending temporal metadata (source date,
"as of" tags) to documents so the model can weakly associate facts with a timeframe, but this
isn't universal across major labs. The corpus itself has a natural snapshot date (e.g. a
Common Crawl cutoff) which becomes the model's training cutoff — a hard dataset-level
boundary, not a per-fact recency signal the model reasons over. Fixing staleness at the
weights level is what continual/incremental pretraining (continue training on a fresher
snapshot so new patterns statistically overwhelm old ones) and research-stage knowledge
editing (ROME, MEMIT — surgically editing specific weight subsets for one fact) attempt;
continual pretraining risks catastrophic forgetting of still-valid older knowledge, and
direct weight editing is too fragile at production scale today. This is exactly why RAG and
tool-use/web-search grounding exist as a separate layer: pretraining has no mechanism to
*know* recency, only to reflect how heavily something was documented, so the practical fix
isn't making the model understand time — it's not relying on frozen weights for
time-sensitive facts at all.

### tiktoken (OpenAI's BPE tokenizer)

LLMs don't read text as words or characters — they read a sequence of integers called
tokens. tiktoken is OpenAI's library that turns text into that exact integer sequence (and
back again), so you know precisely what a model like GPT-4o will see, and precisely how
many units you're billed on. It matters because "1 token ≈ 4 characters" is only an
estimate — exact counts matter for context-window budgeting, RAG chunking, and pre-call
cost estimation.

Mechanism: it implements byte-pair encoding (BPE). The vocabulary — a fixed table mapping
token strings to integer IDs, built by repeatedly merging the most frequent adjacent symbol
pair — was learned once, offline, from a large corpus. tiktoken doesn't learn anything at
runtime; `.encode()` just replays that fixed merge table against new text (core is written
in Rust, wrapped for Python), which is why it's deterministic and fast.

Encodings, matched to model family: `o200k_base` (GPT-4o and newer), `cl100k_base`
(GPT-3.5-turbo, GPT-4 pre-4o), `p50k_base` (older GPT-3: text-davinci-003, Codex),
`r50k_base`/`gpt2` (original GPT-2/GPT-3).

```python
import tiktoken

enc = tiktoken.encoding_for_model("gpt-4o")   # or tiktoken.get_encoding("o200k_base")

tokens = enc.encode("Tokenization is fun!")
print(tokens)          # e.g. [3404, 2065, 374, 2523, 0]
print(len(tokens))     # exact token count — what you'd actually be billed for

print(enc.decode(tokens))              # "Tokenization is fun!" — round-trips exactly
for t in tokens:
    print(t, repr(enc.decode([t])))    # inspect each token's text
```

Gotchas: token boundaries don't follow word boundaries — a leading space usually fuses into
the next token (`" is"` is one token, not `" "` + `"is"`); non-English text tokenizes less
efficiently (more tokens per character), especially languages without spaces or with heavy
Unicode; and this is OpenAI-specific — Claude uses a different vocabulary, so a tiktoken
count is not a Claude token count and shouldn't be reused for Claude context/cost math.

### Tokenizing a raw corpus into a `.bin` token stream (what a "tokenization" pretraining
job is actually doing)

It is not counting tokens — counting is just the progress readout printed along the way.
The actual job is **translation**: every chunk of raw text gets converted into its
sequence of integer token IDs (per the BPE vocabulary — see the tiktoken entry above for
how that vocabulary itself works), and those integers are the thing that gets written to
disk. Think of it like translating an entire shelf of books into a private numbered code
and writing *only the number sequence* onto tape, discarding the original wording — future
readers of the tape don't re-translate anything, they just read numbers back.

Mechanism, for a corpus-building run (not a single API call like tiktoken's `.encode()`):
raw text is read in fixed-size chunks (streaming — a 15GB source file is never loaded into
RAM whole), each chunk is fed through the trained tokenizer to get a list of integer IDs,
and those IDs are appended straight to a flat binary file, 2 bytes per token (`uint16`,
since a 32,768-entry vocabulary fits in that range). A special document-separator token
(`<|endoftext|>`) gets inserted at real document boundaries so the model can learn "this
document ended" instead of the text of one book bleeding straight into the next as if it
were one continuous sentence. The printed "N tokens" line during the run is just a running
tally of how many integers have been written so far — useful for tracking progress on a
multi-hour job, not the deliverable itself.

Why bother writing a separate `.bin` file instead of just keeping the `.txt` and tokenizing
on the fly during training: training samples millions of random windows from the same
corpus over the course of a run, and re-running BPE's merge logic every single time would
waste enormous compute redoing identical work. Tokenize once, store the resulting integers,
and the training loop just memory-maps that file — the OS pages in only the byte ranges a
given random window actually touches, so a 10B-token corpus never needs to fully live in
RAM even though training reads from it constantly.

Production reality / gotchas: token count is not proportional to word count or byte count —
it depends entirely on how well *that specific* vocabulary compresses *that specific* text.
A tokenizer trained mostly on English prose will produce noticeably more tokens per
character on text in a script it rarely saw (e.g. Hindi Devanagari against an
English-majority BPE vocabulary), because byte-level BPE falls back toward near-raw-byte
encoding wherever it never learned useful merges. This is also why a multi-source corpus
build reports per-source token counts rather than per-source file sizes or document counts:
training budgets and mixture ratios ("70% source A, 25% source B, 5% source C") are defined
in tokens, since that's the unit the model actually consumes, and raw byte size is only a
rough proxy for it.

### Chinchilla-optimal training budget

Think of it like a student and a textbook: a huge textbook (lots of parameters) is wasted on
someone who only skims a few pages (few training tokens) before the exam — but re-reading a
thin pamphlet a thousand times also caps how much they can actually learn. For a fixed amount
of study effort, there's a sweet spot between "book size" and "how much you actually read,"
and it's not automatically at either extreme.

Mechanism: DeepMind's 2022 Chinchilla paper (Hoffmann et al., *"Training Compute-Optimal Large
Language Models"*) trained hundreds of models at different (parameter count, token count)
pairs under matched compute budgets and fit power-law curves to how loss falls as each scales.
The finding: earlier LLMs (GPT-3, Gopher, ...) were **over-parameterized and under-trained** —
for a fixed compute budget, loss drops further by training a *smaller* model on *more* tokens
than by training a bigger model on the same fixed data. The empirical optimum lands close to
**~20 training tokens per parameter** (this falls out of the compute identity
`FLOPs ≈ 6 × params × tokens` for one forward+backward pass per token).

`tokens_optimal ≈ 20 × params`

Concrete check, `mini-llms-playground/from_scratch/custom-gpt-50m`: 51,475,968 params →
~1.03B tokens optimal. That project's `TrainConfig.steps=1_000_000` × `context_length=1024` ×
`batch_size=1` = 1.024B tokens processed over a full run — landing almost exactly on the
Chinchilla number, which is why that step count is a deliberate, well-sized default rather
than an arbitrary round number.

Production reality / failure modes:
- The token count is assumed **unique/fresh**. Hitting the target by repeating a small corpus
  for many epochs is a weaker substitute — fine for a few epochs while the model is still
  data-underfit (small model, comparatively large corpus), but the Chinchilla math itself
  doesn't hold once repetition dominates and overfitting risk climbs.
- The ~20:1 ratio was fit on one corpus (MassiveText) and one architecture family — it's a
  strong prior, not a physical law. Production labs deviate from it on purpose: Chinchilla
  optimizes for lowest loss per unit of *training* compute, and says nothing about *inference*
  cost. A smaller model deliberately **overtrained** well past its Chinchilla-optimal point
  (more tokens per parameter than 20:1) costs more to train but is cheaper to serve at scale —
  exactly the trade Llama and most later open-weight model families made once inference volume,
  not training FLOPs, became the dominant cost.

### Distributed data-parallel training (splitting one training run across machines)

Two people cramming for the same exam by splitting the flashcard deck between them, each
going through their own half independently, then meeting up periodically to compare notes and
make sure they both end up knowing the same material — instead of one person going through the
whole deck alone.

Mechanism: **data parallelism** copies the identical model onto every worker, gives each worker
a different slice of the batch to compute gradients on, then **all-reduces** (averages) those
gradients across all workers before anyone applies an optimizer step — so every replica stays
bit-identical after each update, but the gradient-computation work was split. (This is a
different technique from *model/tensor* parallelism — splitting one model's layers or weights
across machines because it doesn't fit on one device — which solves a memory problem, not a
throughput one.) PyTorch's implementation is `torch.distributed` +
`DistributedDataParallel`(DDP), over one of three backends: `nccl` (NVIDIA GPUs only), `gloo`
(CPU, plain TCP, cross-platform), or `mpi`. Two Macs, no NVIDIA GPU anywhere → `gloo` is the
only real option, and MPS tensors have to be moved to CPU for the collective `all_reduce` call
and back, since gloo doesn't operate on MPS tensors directly.

Grounding example — `mini-llms-playground/from_scratch/custom-gpt-50m`, asked in a real session
whether its ~2-day single-Mac training run could be split across two MacBooks:
`TrainConfig.grad_accum_steps=32` already accumulates gradients over 32 micro-batches before
`optimizer.step()` fires once (`src/gpt/training/trainer.py`'s `is_accum_boundary` check) —
that existing accumulation boundary is exactly where an all-reduce belongs if this were made
distributed: each machine processes its own share of the 32 micro-batches with zero
communication, then one `all_reduce` averages the accumulated gradients right before the shared
optimizer step. Communication amortizes over 32 steps, not every single step — the reason this
particular codebase's structure is a reasonably good fit for it, network-overhead-wise, even
though it has zero distributed code today.

What building it would actually take (checklist, not yet implemented anywhere in that repo):
1. `torch.distributed.init_process_group(backend="gloo", ...)` on both machines, one designated
   rank 0, both reachable on the same LAN/Wi-Fi with a shared rendezvous address:port.
2. At the existing `is_accum_boundary` check, replace the direct `optimizer.step()` with a
   `dist.all_reduce` on each parameter's `.grad` (divided by world_size) before stepping.
3. Only rank 0 should run `estimate_loss`/eval, write checkpoints, and print progress — otherwise
   both machines duplicate all of it redundantly.
4. A **live single-process run can't be split mid-flight** — it has to stop and resume from a
   checkpoint (e.g. `checkpoints/50m/latest.pt`) on both machines under the new distributed
   launch, not be migrated in place.
5. No dataset sharding is actually needed: `get_batch()` already samples random windows
   independently per call, so each rank just samples its own random windows from an identical
   local copy of `train.txt`/`test.txt`.

Production reality / gotchas:
- Realistic speedup for 2 workers is well under the naive 2x — sync overhead, plus mismatched
  machines (different M-series generations/speeds) mean every all-reduce waits for the slowest
  worker.
- gloo's collective calls block/hang by default if one machine drops off the network mid-sync —
  needs an explicit timeout configured, or a stalled worker silently stalls the whole run.
- This buys wall-clock speed, not a better model — total tokens processed is unchanged either
  way, so it doesn't move the Chinchilla-optimal token math above at all, just splits the same
  budget across two machines instead of running it serially on one.

### Q/K/V projection (turning a token embedding into something attention can use)

A token's raw embedding is one vector — using it directly for attention would mean "what I'm
looking for" and "what I contain" are forced to be the same thing, so a token could only ever
attend to things identical to itself. Q/K/V splits that single vector into three separately
**learned** views: a **Query** ("what am I looking for"), a **Key** ("what do I offer, for
matching purposes"), and a **Value** ("what do I actually hand over once matched"). Letting the
model learn these independently is what makes "how a token gets matched" different from "what
it contributes" — the actual point of having three vectors instead of one.

Mechanism, once Q/K/V exist: `scores = Q · Kᵀ / √head_dim` (every query compared against every
key) → softmax (scores become weights summing to 1) → weighted sum of `V`. That weighted sum
*is* attention's output — nothing more mysterious underneath it.

"Projection" is just the mechanism for getting from embedding to Q/K/V: a learned linear layer
(matrix multiply), not a metaphor.

Grounding example — `mini-llms-playground/from_scratch/custom-gpt-50m/src/gpt/model.py:51-89`,
the `sdpa` attention path:

```python
self.in_proj = nn.Linear(embed_size, 3 * embed_size, bias=True)   # ONE fused matmul
...
qkv = self.in_proj(x)                                              # (batch, seq_len, 3*embed_size)
q, k, v = qkv.chunk(3, dim=-1)                                      # split back into three
q = q.view(batch, seq_len, num_heads, head_dim).transpose(1, 2)    # ...and k, v identically
```

Two things this file's own comments call out that are worth remembering:

- **One `Linear(embed_size, 3*embed_size)`, not three separate `Linear(embed_size, embed_size)`
  layers.** Mathematically identical to projecting Q, K, V separately — one bigger matmul is
  just faster on a GPU than three smaller ones. Same trick `nn.MultiheadAttention` uses
  internally under the hood (this codebase's `naive` attn_impl path uses that module directly,
  so the projection is hidden inside it rather than written out by hand).
- **The reshape to `(batch, num_heads, seq_len, head_dim)`** is what makes this *multi-head*
  attention: `embed_size` gets split into `num_heads` independent, smaller Q/K/V subspaces
  (`head_dim = embed_size // num_heads` each), each running its own attention computation in
  parallel — letting different heads specialize in attending to different kinds of relationships
  between tokens.
- `F.scaled_dot_product_attention` (PyTorch's fused/flash-eligible kernel) is a pure *attention
  kernel*, not a layer — it expects already-projected per-head Q/K/V tensors as input, which is
  exactly why this codebase's `sdpa` path has to do the projection manually before calling it,
  unlike the `naive` path where `nn.MultiheadAttention` bundles projection and attention
  together into one module call.

### SLM training cost/hardware tiers (what rig a given model size actually needs)

Picking hardware to train a small model is like picking transport for a trip by distance: a
short hop is free (walk/bus), a longer one needs a car you pay for by the hour, and crossing a
continent needs a rented truck — the "vehicle" here is GPU VRAM and throughput, and the "trip
length" is params × tokens.

Mechanism — two separate things scale with param count, and both drive the table below:
- **Memory (does it fit at all):** VRAM has to hold weights + gradients + optimizer state +
  activations. Adam keeps two extra fp32 moment buffers per parameter, so full fp32 training
  needs roughly ~16 bytes/param (4 for weights, 4 for grads, 8 for Adam's two moments) before
  activations are even counted — mixed precision (fp16/bf16) roughly halves the weights/grads
  portion. This is why a 10M-param model runs on whatever Colab Free hands out, but a 1B-param
  model needs a GPU with tens of GB of VRAM just to hold the optimizer state, independent of
  how fast that GPU is.
- **Compute (how long it takes):** training FLOPs scale roughly as `6 × params × tokens`
  (the same relation behind Chinchilla scaling). For a fixed token budget, more params means
  proportionally more FLOPs, and wall-clock time is that FLOP count divided by the GPU's
  actual throughput — which is why the jump from 125M→350M costs minutes→hours even before
  moving to better hardware.

| Hardware | Model size | Training time | Cost |
|---|---|---|---|
| Google Colab Free | 10M params | 1 hour | $0 |
| Google Colab Free | 125M params | 10 minutes | $0 |
| Google Colab Pro ($10/mo) | 350M params | 4-8 hours | $10/month |
| Cloud A100 | 1B params | 8-16 hours | $8-48 per run |
| RTX 4090 (local) | 1B-3B params | 12-24 hours | $15-30 electricity |

Why the tiers break where they do:
- **Colab Free caps near 125M** not because the GPU (usually a T4, ~16GB VRAM) is purely
  compute-bound, but because free-tier sessions get disconnected/reclaimed after a few hours —
  anything that wouldn't finish inside that window effectively can't be trained there at all,
  regardless of whether the weights would fit.
- **A100 shows up at 1B** because that's roughly where Adam's optimizer-state overhead outgrows
  consumer VRAM (a 24GB card) at fp32/mixed precision without aggressive tricks (gradient
  checkpointing, 8-bit optimizers, LoRA) — A100's 40-80GB HBM plus much higher memory bandwidth
  removes that ceiling.
- **Cost = ($/hr for the GPU) × (training hours)**, and training hours is itself
  `FLOPs needed ÷ GPU throughput` — so the $8-48/run range isn't arbitrary, it's spot/on-demand
  A100 pricing (~$1-3/hr) multiplied by the 8-16 hour estimate above.
- **RTX 4090 (24GB) lands in the same param range as A100** but takes longer per run — a
  desktop card trades throughput for the fact that there's no cloud meter running, so the
  "cost" is electricity, not $/hr billing, and there's no forced session timeout pushing the
  model size back down the way Colab Free's does.

Production reality / gotchas:
- These are **instructional/demo runs**, not compute-optimal pretraining — they use a small,
  fixed token budget to get *a* trained model in a reasonable time, not the ~20 tokens/param
  Chinchilla-optimal budget a real base model would need. A "real" 1B model trained
  compute-optimally would need far more tokens (and therefore far more of the FLOPs term above)
  than what fits in an 8-16 hour A100 run.
- The same param count can straddle two rows depending on technique — LoRA/QLoRA or 8-bit
  Adam can shrink the *fine-tuning* memory footprint enough to fine-tune a model on hardware
  that couldn't have pretrained it from scratch, so "what hardware do I need" depends on
  training-from-scratch vs. fine-tuning, not just param count alone.

**Translating a book's table row to hardware it didn't name — worked example (L4 for the
350M/Colab-Pro row):** the table names a price tier ("Colab Pro, $10/mo"), not a GPU model, so
plugging in an actual GPU means comparing specs, not reading the row literally.
- **Peak Tensor Core FLOPS:** L4 (Ada Lovelace) ≈ 121 TFLOPS FP16/BF16 dense — essentially tied
  with V100's ≈125 TFLOPS, which is the GPU class Colab Pro's $10/mo tier has historically
  meant (Pro+ is the tier that adds A100 access). Peak-FLOPS parity alone would suggest L4
  lands close to the book's 4-8h.
- **Memory bandwidth is where they diverge:** V100 has 900 GB/s (HBM2); L4 has only 300 GB/s
  (GDDR6) — a 3x gap. At 350M-param scale, plenty of the training step (attention softmax,
  layernorm, elementwise ops) is memory-bandwidth-bound rather than matmul-bound, especially at
  the small batch sizes Colab's VRAM forces — so FLOPS parity with V100 doesn't translate into
  time parity when the bottleneck is bandwidth.
- **Resulting estimate:** slower than the V100-based 4-8h, faster than T4 (65 TFLOPS, similar
  ~320 GB/s bandwidth to L4 but far less compute) → roughly **6-14 hours** for 350M params on
  L4, with the exact figure depending on batch size: larger batch pushes it toward
  compute-bound (closer to 4-8h), smaller batch pushes it toward bandwidth-bound (toward the
  wider end). The honest answer is "depends which bottleneck the batch size hits," not a single
  number — the book's table hides that by only naming a price tier.

### Kubernetes controllers — the reconcile loop (why "operator" isn't magic)

A thermostat, not a light switch. A light switch is edge-triggered: it reacts to the one moment
someone flips it, and if it missed that moment (power blip, whatever), it just stays wrong until
another flip happens. A thermostat is level-triggered: it doesn't care *when* the room got cold,
it just keeps asking "is it currently below target" on a loop and corrects — so it self-heals
even if it missed the exact moment the temperature dropped. Every Kubernetes controller/operator
(the ones actually installed and used elsewhere in this repo — KubeRay, Argo/Kubeflow, Kargo)
is the thermostat pattern, not the light-switch pattern.

Mechanism: a **SharedInformer** watches a resource type and keeps a local cache; every change
gets turned into a **key** (usually just the object's namespace/name) pushed onto a
**workqueue** — a queue that dedupes identical pending keys, so a burst of events for the same
object collapses into one pending reconcile, not one-per-event. A worker pulls a key off the
queue and calls **reconcile(key)** — and this is the part that's easy to get backwards:
reconcile does *not* receive the event that triggered it. It re-reads the object's current live
state from the API server and re-derives what should exist, from scratch, every single time —
which is exactly what makes it level-triggered. On top of the event-driven path, a **periodic
resync** re-enqueues every object on a fixed timer regardless of whether anything changed, as a
safety net for events a watch stream silently dropped (a resource-version expiry, a brief
disconnect) — the resync tick is what actually makes the "self-healing" property real, not the
watch loop.

Grounding example — `platform-lab/k8s_explorer/toy-controller/`, built and verified live against
a real 3-node minikube cluster specifically to see this mechanism, not just read about it: a
`ResourceQuota` was deleted by hand from a managed namespace, and it came back ~20s later with
**no new watch event involved at all** — the controller's logs showed a scheduled
`resync: re-enqueued N namespaces` line firing right before the recreate, timed to the 30s resync
tick started at process launch, not to the delete.

Production reality / gotchas:
- **Finalizers**, not reconcile itself, handle cleanup-on-delete — deliberately left out of the
  toy version to keep the core loop legible. Reconcile answers "what should exist," a finalizer
  answers "what has to happen before this object is allowed to actually disappear" — a separate
  mechanism bolted on, not a variant of the same one.
- A reconcile that keeps failing needs **exponential backoff on the requeue**, not a tight retry
  loop — otherwise one permanently-broken object (bad RBAC, a typo'd field) burns CPU hammering
  the API server forever.
- Real frameworks (client-go's `workqueue.RateLimitingInterface`, `controller-runtime` in Go)
  provide the workqueue/backoff/informer machinery for free; this toy version hand-rolls all of
  it in Python specifically to make the pattern visible, not because that's how you'd actually
  ship one.

### Kubernetes extended resources & GPU scheduling (why GPUs need device plugins, not just a bigger number)

CPU and memory are like flour in a recipe — you can ask for exactly 1.5 cups, the kitchen just
measures it out. A GPU (as Kubernetes sees it) is like asking for a whole cake pan — you get one
pan or zero, there's no API for "half a pan." That distinction is the entire reason GPU device
plugins, MIG, and time-slicing exist as a separate layer instead of GPUs just being "a resource
type with more zeroes."

Mechanism: the scheduler only ever reads two numbers off a Node object — `status.capacity` and
`status.allocatable` — for whatever resource names happen to be there. It has **no idea** where
those numbers came from or what's providing them; `cpu`/`memory` come from the kubelet itself,
and anything else (`nvidia.com/gpu`, or any custom name) is an **extended resource**, which a
device plugin advertises by calling the kubelet's `ListAndWatch` gRPC method — which, underneath,
just results in the kubelet patching that same `status.capacity`/`allocatable` pair. Because the
scheduler-facing half is *just* those two numbers, you can simulate exactly that half by hand,
with a plain `kubectl patch --subresource=status`, without any real GPU or device plugin at all —
confirmed this isn't wiped by the kubelet's own periodic node-status heartbeat, because kubelet
only reconciles resource types it manages itself and leaves ones it doesn't recognize alone.

The integer-only rule is the actual reason MIG/time-slicing exist, not an unrelated fact: a Pod
requesting `example.com/toygpu: "500m"` gets **rejected at admission**, before the scheduler is
even involved (`Invalid value: "500m": must be an integer`) — extended resources have no
API-level concept of a fraction. A real GPU can't be requested as "0.4 of a card" for the same
reason. MIG and time-slicing device plugins exist specifically to make **one physical GPU present
itself as several whole extended-resource units** (`nvidia.com/gpu: 4` on a single card, sliced
four ways) — because making the request itself fractional was never on the table.

Grounding example — `platform-lab/k8s_explorer/gpu-scheduling-demo/`: patched a real minikube
node's status to advertise 2 units of a fake `example.com/toygpu` resource, requested 3 Pods at 1
unit each, and watched the real scheduler put 2 `Running` (bin-packed onto the one node that had
the resource at all — the other two nodes were "insufficient" in exactly the same way as a node
that has the resource but is full) and 1 `Pending` with a real
`FailedScheduling: 3 Insufficient example.com/toygpu` event.

Production reality / boundary of this technique: this simulates the scheduler-facing half only.
A real device plugin also implements `Allocate` (called at bind time, handing over which specific
physical device — sets `NVIDIA_VISIBLE_DEVICES`, mounts `/dev/nvidiaN`) over a gRPC socket at
`/var/lib/kubelet/device-plugins/`, none of which this technique touches; and GPU scheduling in
production also cares about topology (NUMA/PCIe locality between the GPU and the CPU/NIC it's
paired with), which plain extended-resource accounting has no concept of at all.

### HF-compatible vs. vLLM-compatible (two different bars, not synonyms)

Think of it like a shipping container: "HF-compatible" is the container meeting the standard
size/shape so *any* dock can lift it (a generic loader — `transformers.AutoModelForCausalLM`).
"vLLM-compatible" is a stricter requirement on top: not just any dock, but specifically the
*fast, specialized* dock that only knows how to unload a handful of container types it was
custom-built for.

Mechanism:
- **HF-compatible** means a model directory has a `config.json` naming an `architectures` class
  `transformers` already implements (e.g. `GPT2LMHeadModel`, `LlamaForCausalLM`), weights
  (safetensors) whose parameter names/shapes match that implementation exactly, and tokenizer
  files transformers can load. Meeting this gets you `from_pretrained()`, `Trainer`,
  `pipeline()`, and Hub upload/download for free.
- **vLLM-compatible** is narrower: vLLM keeps its *own* separate registry of model
  implementations (rewritten internally with paged attention, continuous batching, fused
  kernels) and only serves architectures it has specifically reimplemented — a large list
  (Llama, Mistral, GPT-2, Qwen, Gemma, Phi, ...) but not every HF-loadable architecture. So
  `vLLM-compatible ⊆ HF-compatible`: being HF-loadable (even via `trust_remote_code=True` custom
  code) does not imply vLLM support, but landing on an architecture name vLLM already
  implements gets both at once.

The trick for a genuinely custom/from-scratch architecture is never "make vLLM understand my
model" — it's "repackage my weights to numerically match an architecture vLLM already
understands," verified by comparing logits (`torch.allclose`) between the original model and
the repackaged one on the same input, since a silent key-mapping mistake still produces a
model that *loads* without error but computes something subtly wrong.

Native checkpoint (custom keys/format)
        │
        │ export: remap weights into an existing architecture's
        │ exact key names/shapes + write config.json + tokenizer files
        ▼
HF-format directory (config.json + safetensors + tokenizer files)
        │
        ├──▶ transformers.AutoModelForCausalLM.from_pretrained()   ← HF-compatible
        │
        └──▶ vllm serve <dir>                                      ← vLLM-compatible too,
                                                                        IF the target architecture
                                                                        is one vLLM implements

Two concrete conversions worth remembering as reference points: a GPT-2-shaped custom model
(learned position embeddings, GELU MLP, fused QKV) maps onto `GPT2LMHeadModel` — the only real
wrinkles are that GPT-2's `Conv1D` layers store weights *transposed* relative to `nn.Linear`,
and GPT-2's default activation is a tanh-approximated GELU (`gelu_new`) rather than exact GELU,
so the exported config needs `activation_function="gelu"` to match a model actually trained with
`nn.GELU()`. A RoPE+RMSNorm+SwiGLU custom model (no biases) maps onto `LlamaForCausalLM` instead
— no activation mismatch (SwiGLU's `silu` *is* Llama's default), no transpose needed (both sides
use plain `nn.Linear`), but the fused QKV projection has to be *split* into three separate
matrices since Llama never fuses them. Same underlying principle, different architecture family,
different specific gotchas — the gotchas are always in the weight *layout* and activation
*exactness*, never in the tokenizer if the vocabulary is already a real published one (GPT-2's
tokenizer needs no conversion at all) or already stored in `transformers`' own native tokenizer
JSON format (a custom vocabulary trained via the `tokenizers` library loads directly into
`PreTrainedTokenizerFast` with zero conversion either).
