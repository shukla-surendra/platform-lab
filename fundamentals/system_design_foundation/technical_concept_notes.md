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

New standalone topics get added here directly. Nothing currently sits in the catch-all.
