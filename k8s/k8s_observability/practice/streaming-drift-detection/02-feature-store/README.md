# 02-feature-store

A self-hosted [Feast](../../../mlops_aiops/docs/tools/feast/README.md) feature
server, custom-built image with this project's `feature_repo/` baked in.
Stage 2 of [`../`](../): sits between the raw event stream (stage 1) and the
drift engine (stage 3), and its entire job is making sure both training-time
and serving-time reads of `amount`/`category` go through the exact same
definition — see [`feature_repo/definitions.py`](feature_repo/definitions.py)
for why that's one `FeatureView` backed by a `PushSource`, not two separate
pipelines.

**Status: scaffolded, not installed / not built.** `definitions.py` and
`feature_store.yaml` are real Feast config (matches the `feast==0.49.0` API
surface), but `feast apply` has not actually been run against them yet — do
that locally first (`pip install feast[sqlite]==0.49.0 && cd feature_repo &&
python generate_seed_data.py && feast apply`) before trusting the Docker
build to catch a typo.

## Why Feast, not Tecton

Tecton has no self-hosted tier — it's SaaS-only, so using it here would mean
this stage can't run on a local minikube cluster at all, same problem Pub/Sub
and Kinesis had for stage 1. Feast is fully open-source and self-hostable;
[`../../../mlops_aiops/docs/tools/feast/README.md`](../../../mlops_aiops/docs/tools/feast/README.md)
has the full comparison.

## Why no third-party Helm chart dependency

Feast does publish its own Helm charts, but their exact `values.yaml`
schema (subchart layout, how `feature_repo/` gets mounted vs. baked in) is
not something this pass verified from source — depending on it here would
mean shipping config nobody's checked. `evidently_stack` next door
([`../../k8s/k8s_mlops/evidently_stack/`](../../k8s/k8s_mlops/evidently_stack/))
already establishes the fallback for exactly this situation in this repo:
build a small custom image with the app's own Dockerfile, hand-write the
Deployment/Service. Same approach here — [`Dockerfile`](Dockerfile) installs
`feast[sqlite]`, copies in `feature_repo/`, runs `feast apply` at build time
so the image ships with an already-populated registry.

## Two paths, one definition

- **Offline** — `amount_source` (`FileSource` in
  [`definitions.py`](feature_repo/definitions.py)), backfilled from
  [`generate_seed_data.py`](feature_repo/generate_seed_data.py)'s seed
  parquet at build time. This is what a real training job would read, and
  what 03-drift-engine's **batch** mode treats as the reference distribution
  to compare against.
- **Online** — the `PushSource` itself. 03-drift-engine's **streaming**
  consumer calls this feature server's `/push` endpoint once per Kafka event
  it reads from stage 1, then reads back via `/get-online-features` to build
  its sliding window. Same `FeatureView`, same schema — training and
  serving can't silently diverge the way they would with two hand-written
  transformation functions.

No binary data is committed: `generate_seed_data.py` runs at image build
time instead of a `.parquet` file living in git.

## Build and install

```bash
minikube image build -t feature-store:local .
helm install feature-store . -n drift-detection --create-namespace
```

## Related

- [`../README.md`](../README.md) — the full pipeline.
- [`../../../mlops_aiops/docs/tools/feast/README.md`](../../../mlops_aiops/docs/tools/feast/README.md).
- [`../../k8s/k8s_mlops/evidently_stack/`](../../k8s/k8s_mlops/evidently_stack/) —
  the custom-Dockerfile pattern this chart follows.
