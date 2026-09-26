# feature-store

Why feature stores exist, when you don't need one, and how they work inside —
built by reproducing the problems in plain pandas and then writing a tiny
feature store from scratch. Written for someone who has *used* SageMaker
Feature Store / Databricks feature tables and still thinks "this looks
unnecessary".

**The thesis:** a feature store solves no modeling problem. It solves four
data-plumbing problems — *training/serving skew, point-in-time leakage,
feature duplication, and online-serving plumbing* — and it only pays for itself
when at least one of them actually hurts you. For a single batch-scored model
it usually doesn't, which is exactly why it feels pointless.

## Reading order

| # | Doc | Question it answers |
|---|---|---|
| 1 | [The problem](docs/01-the-problem.md) | What breaks without one? (with numbers from the demos) |
| 2 | [Do you need one?](docs/02-do-you-need-one.md) | The skeptic's page: when it's overkill, when it isn't, what it costs |
| 3 | [Core concepts](docs/03-core-concepts.md) | Entity, offline/online store, event time, point-in-time join, materialization, TTL |
| 4 | [SageMaker vs Databricks vs Feast](docs/04-sagemaker-databricks-feast.md) | The same concepts under each product's names; what you probably did/didn't exercise |

Questions as they come up live in [`doubt.md`](doubt.md) — a running Q&A log.

## Demos (runnable, pandas + numpy only, no cloud account)

```bash
cd feature-store
uv sync
uv run python demos/01_training_serving_skew.py     # two "identical" features disagree on 79% of customers
uv run python demos/02_point_in_time_leakage.py     # AUC 0.98 (leaky join) vs 0.62 (as-of join)
uv run python demos/03_mini_feature_store.py        # one definition -> offline + online, 0 mismatches
```

| Demo | Shows |
|---|---|
| `demos/01_training_serving_skew.py` | The batch and serving implementations of one feature diverge silently; the model's decisions flip for 40% of customers. |
| `demos/02_point_in_time_leakage.py` | Joining labels to the "latest" feature value leaks the future and inflates AUC from 0.62 to 0.98. |
| `demos/mini_feature_store.py` | ~100-line feature store: registry, offline store, as-of join, materialization, online store, TTL. |
| `demos/03_mini_feature_store.py` | Uses it: point-in-time training set, materialize, online lookup, and a check that online == offline at the same instant. |
| `demos/04_column_transformer_boundary.py` | What sklearn's `ColumnTransformer` learns at `fit`, and why fitted (stateful) transforms belong with the model, not in the shared feature store. Needs `--with scikit-learn`. |
| `demos/06_actuals_arrive_later.py` | Labels ("actuals") arrive late and never live in the online store: the serving-log-to-label join, label maturity by age, and why label-derived features must use outcomes known at event time (naive join differs from served value for 48% of events). |
| `demos/07_joins.py` | What "join" means in a feature store: two feature views for different entities joined onto one spine, point-in-time, verified against a direct computation; online = one lookup per entity. Also flags the inclusive as-of gotcha. |
| `demos/08_composing_models.py` | How several models build on one store: shared views + a model's own view + an on-demand (request-time) feature, each model declaring what it consumes; serving matches the offline build. |
| `demos/09_access_patterns.py` | Offline (point-in-time join, range scan, snapshot as-of, event-scoped lookup) and online (single get, multi-get, multi-entity, stale/missing) access patterns with the use case for each; asserts snapshot == point-in-time join. |
| `demos/10_feature_evolution.py` | Train today, then drop 2 / add 3 features: in-place redefinition vs versioned views vs training snapshot, plus expired source history; shows what breaks in reproduction and in serving. |
| `demos/05_online_offline_writes.py` | Batch vs push-to-both vs push-online-only: whether online feature rows also reach the offline store, and the silent skew when they don't. |

(`uv` may warn that the root `VIRTUAL_ENV` doesn't match this project's `.venv`;
it's harmless — this folder has its own environment.)

## Feast lab (real feature store, Docker Compose)

[`feast-server/`](feast-server) runs Feast 0.66.0 locally with **Redis** as the online store and **Postgres** as the offline store and
SQL registry, plus a REST feature server and an optional UI. Five guided scripts (`explore/`) exercise the concepts from
[`doubt.md`](doubt.md) on the real thing: point-in-time joins, online lookups over REST, push modes, on-demand features and
feature versions. Start with [`feast-server/README.md`](feast-server/README.md).

```bash
cd feast-server && docker compose up -d --build
docker compose run --rm workbench python explore/01_offline_pit.py
```

## Related in this repo

- [`mlops/projects/feast-demo`](../mlops/projects/feast-demo) — the same ideas with real Feast (registry, SQLite online store).
- [`mlops/projects/fraud-detection-xgboost`](../mlops/projects/fraud-detection-xgboost) — Feast features feeding a real model (`feast_features.py`, `train_with_feast.py`).
- [`mlops/projects/batch-drift-detection-xgboost`](../mlops/projects/batch-drift-detection-xgboost) — monitoring, the natural next step: feature/prediction drift.

## Deep-dive backlog

Ideas for the "go deep" phase; each should end with a runnable demo or a decision
rule, not just prose.

- [ ] **Streaming features** — window aggregates (`txns_last_10_min`) and why matching the training backfill is the hardest part. Build with a small event-time simulation.
- [ ] **Late and out-of-order data** — event time vs ingestion time; reproduce "what did we know when we trained model v3".
- [ ] **Backfills & feature versioning** — changing a definition without breaking consumers; feature service per model version.
- [ ] **On-demand features** — request-time transforms that must share code with training.
- [ ] **Skew detection in production** — log served features, compare with offline recomputation; link to Evidently drift work.
- [ ] **Real product hands-on** — SageMaker feature group (Terraform in `cloud-practice/aws/terraform`), Databricks feature table, Feast with Redis; map each line to the concept.
- [ ] **Cost model** — online store sizing/pricing vs "a table + a cache".
- [ ] **Embeddings / LLM-era features** — where a feature store does and doesn't fit next to a vector DB and RAG pipelines (honest take).
- [ ] **Decision rubric** — turn page 2's guide into a checklist you can apply to a real project in 10 minutes.
