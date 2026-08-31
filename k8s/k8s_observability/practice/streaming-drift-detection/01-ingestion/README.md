# 01-ingestion

Kafka (Bitnami's OCI chart, KRaft mode — no ZooKeeper pod) plus a synthetic
producer that stands in for the real production event source. This is stage
1 of [`../`](../): the entry point for every event that eventually gets
feature-ized (stage 2) and drift-checked (stage 3).

**Status: scaffolded, not installed.** Chart dependency (`kafka` 26.6.1 from
`oci://registry-1.docker.io/bitnamicharts`) was confirmed live on Artifact
Hub; the `values.yaml` KRaft/persistence keys paired with it have not been
diffed against the chart's actual schema yet. Do that first:

```bash
helm show values oci://registry-1.docker.io/bitnamicharts/kafka --version 26.6.1
```

## Why Kafka, not Pub/Sub or Kinesis

The spec named all three as equivalent options. Pub/Sub and Kinesis are both
managed-only — no self-hosted mode that runs on a local minikube cluster —
so picking either would mean this project needs real cloud credentials just
to run stage 1. Kafka is the one of the three that's realistically
self-hostable, and it's what the rest of this repo already leans on
conceptually (see
[`../../../mlops_aiops/docs/tools/kafka/README.md`](../../../mlops_aiops/docs/tools/kafka/README.md)).

## Why Bitnami's OCI chart, not the legacy `charts.bitnami.com/bitnami` repo

`charts.bitnami.com/bitnami` stopped publishing updates on 2025-08-28 — all
previously-published tags moved to `docker.io/bitnamilegacy` and the classic
Helm repo is effectively frozen. Current Bitnami charts are OCI-only now
(`oci://registry-1.docker.io/bitnamicharts/<chart>`), which is what
`Chart.yaml` here points at. This is the same kind of chart-provenance
gotcha `../README.md`'s "Chart provenance note" section documents for
`trace-stack`'s Grafana/Tempo charts — worth knowing before copying this
`Chart.yaml` as a starting point elsewhere.

## Why KRaft mode

Bitnami's Kafka chart can run either KRaft (Kafka's own Raft-based metadata
quorum, no external dependency) or ZooKeeper-backed. KRaft means one fewer
StatefulSet on a resource-constrained minikube cluster, and it's the
direction upstream Kafka itself has been moving — ZooKeeper mode is legacy
at this point, not the safer default.

## How the synthetic producer simulates drift

[`producer/produce_events.py`](producer/produce_events.py) emits JSON events
with one numeric feature, `amount` — drawn from `Normal(50, 10)` for the
first `driftShiftAfterEvents` events (2000 by default, a few minutes at the
default rate), then from `Normal(90, 10)` for everything after. That's the
signal both of stage 3's modes are built to catch: batch mode sees it once
its window rolls past the shift point; streaming mode sees it a few seconds
after the shift, once its sliding window fills with post-shift events. Set
`producer.driftShiftAfterEvents: 0` to disable the shift and produce a
stationary stream instead (useful for confirming stage 3 stays quiet on
undrifted data).

## Build the image and install

```bash
minikube image build -t producer:local -f producer/Dockerfile producer/
helm dependency build .
helm install ingestion . -n drift-detection --create-namespace
```

## Related

- [`../README.md`](../README.md) — the full 5-stage pipeline and why these
  charts share one namespace.
- [`../../../mlops_aiops/docs/tools/kafka/README.md`](../../../mlops_aiops/docs/tools/kafka/README.md),
  [`.../kafka-vs-rabbitmq.md`](../../../mlops_aiops/docs/tools/kafka-vs-rabbitmq.md).
