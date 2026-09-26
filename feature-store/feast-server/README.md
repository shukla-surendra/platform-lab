# Feast lab — Redis (online) + Postgres (offline + registry) in Docker Compose

A local, throwaway Feast deployment for exploring the concepts in [`../doubt.md`](../doubt.md) on a real feature store
(Feast **0.66.0**), instead of the ~100-line toy in [`../demos`](../demos).

```
                       ┌────────────── Postgres ──────────────┐
 load_data.py ───────► │ transactions   customer_stats   merchant_stats   │  ← OFFLINE store (history, point-in-time joins)
                       │ registry tables (entities, views, services, versions) │  ← SQL REGISTRY
                       └──────────────────────────────────────┘
        feast apply ──► registry            feast materialize ──► Redis  ← ONLINE store (latest value per entity key)
                                                                  ▲
 feature-server (REST :6566) ── get-online-features ──────────────┘        feast-ui (:8888, optional)
```

| Piece | Backend | Why |
|---|---|---|
| Online store | **Redis** | Key-value, latest value per entity key, the standard low-latency choice |
| Offline store | **Postgres** (`feast[postgres]`) | Runs locally, point-in-time joins are SQL you can read |
| Registry | **Postgres (SQL registry)** | Shared by every container; inspect it with `psql` |
| Feature server | `feast serve` (REST) | Online reads over HTTP, like production |

## Run it

```bash
cd feature-store/feast-server
docker compose up -d --build            # Redis + Postgres, then init (data → apply → materialize), then the feature server
docker compose ps                        # feast-init exits 0; the rest stay up

docker compose --profile ui up -d        # optional: Feast UI on http://localhost:8888
docker compose run --rm workbench python explore/01_offline_pit.py     # run any explore script

docker compose down                      # stop (data kept in volumes)
docker compose down -v                   # stop and wipe everything
docker compose up -d --force-recreate feast-init   # reload fresh demo data + re-apply + re-materialize
```
Ports: Redis `6379`, Postgres `5432`, feature server `6566`, UI `8888`. Credentials (`feast`/`feast`) are local-lab defaults.
Requires Docker with Compose v2; the images total about 1.4 GB (Feast image ~1 GB, Postgres ~0.4 GB, Redis ~60 MB).

## What's in it

| Path | Purpose |
|---|---|
| `docker-compose.yml`, `Dockerfile` | The stack; one image runs init, server, UI and scripts |
| `feature_repo/feature_store.yaml` | Backends (Redis, Postgres, SQL registry). Version-pinning flag enabled |
| `feature_repo/feature_definitions.py` | Entities `customer`, `merchant`; views `customer_stats`, `merchant_stats`, `customer_stats_fresh` (push); on-demand view `amount_vs_avg`; feature services `model_a`, `model_b` |
| `scripts/load_data.py`, `scripts/init.sh` | Generate ~13k transactions ending "now", load into Postgres, apply, materialize |
| `explore/*.py` | Guided experiments, below |

Demo data: 200 customers, 25 merchants, 90 days ending at container start. ~15% of customers go quiet, so some values are stale/missing (TTL, cold start).
`transactions` is the labelled **spine**; `customer_stats` / `merchant_stats` hold trailing-30-day features at every transaction time.

## Explore scripts → concepts

Run each with `docker compose run --rm workbench python explore/<script>.py`.

| Script | Shows | `doubt.md` |
|---|---|---|
| `01_offline_pit.py` | Point-in-time join of two feature views (two entities) onto a labelled spine; checked against an independent pandas as-of join | Q1, Q2, Q6–Q8 |
| `02_online_get.py` | Single/multi-key lookup via SDK **and REST**, missing keys → `None`, what Redis actually stores, who is missing online | Q4, Q11 |
| `03_push_modes.py` | `ONLINE`-only push creates skew; the offline push modes **do not work with the Postgres offline store** in 0.66; manual dual-write workaround | Q4, Q5 |
| `04_on_demand_and_services.py` | Feature services per model; on-demand feature computed from a stored feature + the live request, identical online/offline, over SDK and REST | Q9 |
| `05_feature_versions.py` | Drop a feature → new version; unpinned reference breaks, `@v0` pin keeps the old model working; each version needs its own materialization | Q12 |

## Things worth trying by hand

```bash
# online lookup over REST
curl -s -X POST localhost:6566/get-online-features -H 'Content-Type: application/json' \
  -d '{"features":["customer_stats:avg_amount_30d"],"entities":{"customer_id":[0,1,2]}}' | python3 -m json.tool

# on-demand feature: request-time values travel in "entities" next to the key
curl -s -X POST localhost:6566/get-online-features -H 'Content-Type: application/json' \
  -d '{"feature_service":"model_b","entities":{"customer_id":[0],"amount":[100.0]}}'

docker compose exec redis redis-cli dbsize                                    # one hash per entity key
docker compose exec postgres psql -U feast -d feast -c "select * from customer_stats order by event_timestamp desc limit 5"
docker compose exec postgres psql -U feast -d feast -c "select feature_view_name, version_number from feature_view_version_history"
docker compose run --rm workbench feast -c /app/feature_repo feature-views list      # what the registry knows
docker compose run --rm workbench feast -c /app/feature_repo feature-services list   # (also: entities, data-sources)
```

Ideas: change `ttl` in `feature_definitions.py` and re-run `feast apply` (`docker compose run --rm workbench bash -c "cd feature_repo && feast apply"`);
add a third feature view; stop materializing and watch online values go stale; add a `LabelView` (new in Feast 0.66) to keep labels in the store.

## Findings from building this (Feast 0.66.0, verified by running it)

- **Postgres offline store has no `offline_write_batch`**, so `PushMode.ONLINE_AND_OFFLINE` / `OFFLINE` raise `NotImplementedError`; the file (Dask) store does implement it. Other backends were not checked. The dual write is a property of your backend (Q4).
- **Feast's Postgres connections default to `sslmode=require`**; the plain Postgres container has no TLS, hence `sslmode: disable` in the config (lab only).
- **`feast ui` needs the `grpcio` extra** (it crashed with `No module named 'grpc'` without it), so the image installs `feast[redis,postgres,grpcio]`.
- **`feast registry-dump` does not support a SQL registry** in 0.66 (it fails with "unsupported scheme postgresql+psycopg"; only file/S3/GCS/HDFS). Use `feast <entities|feature-views|feature-services|data-sources> list`, the UI, or query the registry tables in Postgres.
- **Point-in-time join matches an independent pandas `merge_asof`** for 100% of sampled rows, including the 14-day TTL, and is inclusive of the event timestamp (Q7).
- **Definition changes create versions automatically; unchanged re-applies do not.** Version-qualified references (`view@v0:feature`) require `enable_online_feature_view_versioning: true`, and pinned online reads need that version materialized (Q12).
- **Request-time values for on-demand views go in the REST `entities` map**, not a separate field.
- **Redis holds one hash per entity key**, shared by every feature view of that entity, with no Redis-level expiry; the feature `ttl` is Feast's concept.
- Only customers active in the 30-day materialization window exist online; the rest return `None`.

## Not covered (yet)

Streaming ingestion, remote offline/registry servers (`feast serve_offline`, `serve_registry`), authentication (`no_auth` here),
feature logging to a serving log, and non-Postgres offline stores.
