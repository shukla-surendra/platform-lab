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
