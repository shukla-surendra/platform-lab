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

## Everything else

New standalone topics get added here directly. Nothing currently sits in the catch-all.
