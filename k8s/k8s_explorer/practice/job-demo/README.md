# job-demo

Hands-on companion to the Job section of [`docs/workload-types.md`](../docs/workload-types.md).
Three manifests, each isolating one behavior of `Job` that's easy to describe but more
convincing to watch happen: run-to-completion, retry-on-failure, and parallel work-splitting.

See [`cronjob-demo/`](../cronjob-demo) for running a Job like these on a schedule.

Assumes a running `minikube` cluster (`minikube status`).

## The use case (a concrete scenario)

Say `full-stack-app`'s Postgres schema changes between releases. Before the new backend Pods
roll out, *something* needs to connect to the database and run one migration script — once,
successfully, and then never again until the next release. That something isn't a service: it
doesn't listen on a port, it isn't meant to stay up, and nothing should be "load-balancing"
traffic to it. It just needs to run to completion, reliably, and then get out of the way.

That's not hypothetical — it's exactly what
[`full-stack-app/templates/migration-job.yaml`](../full-stack-app/templates/migration-job.yaml)
does in this repo, wired up as a Helm `post-install,pre-upgrade` hook so it fires automatically
on every install/upgrade.

## What problem does it solve?

Every other workload type in this repo (`Deployment`, `StatefulSet`, `DaemonSet`) is built
around the assumption that a Pod exiting is a *problem* — the controller's whole job is to
notice and bring up a replacement, forever. That's the wrong assumption for the migration
scenario above: point a Deployment at that same container and it becomes a bug — the Pod exits
`0`, the Deployment sees "container not running" and restarts it, and now the one-time migration
re-runs in an infinite crash loop.

`Job` inverts the assumption: it exists specifically to run a Pod (or several) **to completion,
exactly the number of times you asked for, and then stop** — while still giving you the
reliability piece (retry on failure, up to `backoffLimit`) that a bare, unsupervised
`kubectl run` Pod doesn't give you at all. It's the missing middle between "one Pod, no
supervision" and "a controller that never lets the Pod stay stopped."

Same shape applies beyond migrations — batch/data processing over a fixed input (`02-job-
parallel.yaml` here), one-off backfills or admin tasks, and build/test steps run inside the
cluster. The common thread: a defined finish line and a defined *number* of times to run — never
"keep this running."

## How this compares to tools you may already know

If you've used a workflow/orchestration product before, `Job` isn't the whole product — it's the
**single-run primitive underneath it**:

| Tool you may know | The piece that's equivalent to a K8s `Job` | What that tool adds on top that plain `Job` doesn't have |
|---|---|---|
| **Databricks Jobs** | One Task run (a notebook/script executed once on a job cluster) | Multi-task DAGs, managed cluster provisioning, run history UI, alerting |
| **Apache Airflow** | One Task instance inside a DAG run | The DAG itself (task dependencies/ordering), scheduler, retry/SLA UI |
| **AWS Batch** | One Job (a container run once, pulled off a queue) | Job queues, compute-environment auto-scaling, priority scheduling |
| **CI pipeline (GitHub Actions, Jenkins, ...)** | One job/step in a workflow | Multi-step pipelines, triggers on push/PR, artifact passing between steps |
| **`cron` on a plain Linux box** | The command a crontab line runs | Nothing extra — `cron` itself maps to `CronJob` below; the *command it invokes* is the `Job`-equivalent piece |

The pattern is the same across all of them: a plain Kubernetes `Job` is deliberately just the
innermost "run this container once, reliably" primitive. The DAG/scheduling/queueing features
those tools bundle don't exist in `Job` itself — Kubernetes expects you to reach for something
layered on top (Argo Workflows, Tekton, Kubeflow Pipelines — see
[`kubeflow-pipeline-sample/`](../kubeflow-pipeline-sample) in this repo) for multi-step
orchestration, the same way Databricks needs multi-task Jobs or Airflow needs a DAG for that.

## Do we need to schedule it?

Not necessarily — that's the deciding line between `Job` and `CronJob`:

- **No recurrence needed → plain `Job`** (what's in this directory). You create it once —
  by hand, from a CI/CD pipeline step, as a Helm install/upgrade hook (see the migration Job
  above), or in response to some other event — it runs to completion, and it's done. There's no
  schedule because there's nothing to repeat.
- **The same work needs to happen on a timer → `CronJob`** (see
  [`cronjob-demo/`](../cronjob-demo) — the `cron`/Databricks-schedule-trigger equivalent). A
  CronJob doesn't replace a Job's mechanics — it *is* a Job template, and at every tick it
  creates a new, ordinary `Job` that behaves exactly like the ones in this directory (same
  `backoffLimit` retries, same completion tracking). The only thing a CronJob adds on top is
  "and do that again every `schedule`."

Rule of thumb: reach for `CronJob` only once you can name the recurring cadence up front (nightly
backup, hourly report). If the trigger is instead "after a deploy," "when a user clicks a
button," or "whenever this pipeline stage runs" — that's a plain `Job`, created on demand by
whatever's driving that event, not a schedule.

## Once it's finished, does it ever run again — e.g. on the next deployment?

Two separate things are easy to conflate here, so worth pulling apart explicitly:

**`completions` is about Pods *within one Job object*.** `02-job-parallel.yaml` sets
`completions: 6` — that Job runs 6 Pods to completion, marks itself `Complete`, and is done,
permanently, for that Job object. It will never start a 7th Pod, no matter how long it sits in
the cluster.

**Whether it runs again on the next deployment is a completely different question — it depends
on whether that deployment creates a *new* Job object or tries to reuse the old one:**

- `kubectl apply -f` the *exact same* manifest again, and a Job with that name already exists and
  is `Complete`? Nothing happens — `apply` sees no diff and does nothing. It does **not** rerun.
- Edit the manifest (new image, new command) and `apply` it against that same existing name?
  Kubernetes actually **errors** — most of a Job's `spec.template` is immutable once created. You
  cannot mutate a finished Job into running again.
- The only way to get the same work to run again is to create a **new Job object**: a different
  name, the old one deleted first, or — the common pattern — a name that changes every time it's
  deployed.

That last pattern is exactly what this repo's real migration Job already does. Look at
[`full-stack-app/templates/migration-job.yaml`](../full-stack-app/templates/migration-job.yaml)'s
name:

```yaml
name: {{ .Release.Name }}-db-migrate-{{ .Release.Revision }}
```

Every Helm install/upgrade bumps `Release.Revision`, so it's a **brand-new Job object** each time
(`myapp-db-migrate-1`, `myapp-db-migrate-2`, ...) — the old one isn't waking back up, it's a
completely separate object that happens to run the same script. The previous revision's Job just
sits there, `Complete` forever, ignored.

`CronJob` is nothing more than automation for that same trick: instead of a human (or Helm)
manually generating a new name each time, the CronJob controller does it automatically at every
scheduled tick — which is why the Jobs it creates are named `hello-cronjob-<timestamp>`, never a
reused `hello-cronjob`.

## Part 1 — a basic Job (`00-job-basic.yaml`)

```bash
kubectl apply -f 00-job-basic.yaml
kubectl get pods -l job-name=pi-calc -w
```

Watch the Pod go `Pending` → `Running` → `Completed`. Unlike a Deployment's Pods, a Job's Pod
finishing successfully is the goal, not a crash to recover from — it stays in `Completed`, it
isn't restarted:

```bash
kubectl get job pi-calc
kubectl logs job/pi-calc
```

`kubectl get job` shows `COMPLETIONS 1/1` once done. The logs are the first couple thousand
digits of pi — proof the container actually ran to completion rather than just exiting `0`
immediately.

## Part 2 — retries via `backoffLimit` (`01-job-retry.yaml`)

```bash
kubectl apply -f 01-job-retry.yaml
kubectl get pods -l job-name=flaky-job -w
```

This container always `exit 1`s. With `restartPolicy: Never`, a failed Pod isn't restarted in
place — the **Job controller** notices the failure and creates a brand-new Pod instead. Watch
three Pods appear (the original attempt plus two retries, matching `backoffLimit: 2`), each
with a fresh name:

```bash
kubectl get pods -l job-name=flaky-job
kubectl describe job flaky-job
```

`describe` ends with `Status: Failed` and an event log showing each `SuccessfulCreate` — one per
attempt. Once `backoffLimit` attempts are all exhausted, the Job stops retrying and reports
failed rather than looping forever.

## Part 3 — splitting work with `completions`/`parallelism` (`02-job-parallel.yaml`)

```bash
kubectl apply -f 02-job-parallel.yaml
kubectl get pods -l job-name=parallel-work -w
```

`completions: 6, parallelism: 3` means: run this Pod six times total, up to three at once. Expect
three Pods `Running` immediately, and — as each finishes its 5s sleep — a new one starts to
replace it, until six have completed:

```bash
kubectl get job parallel-work
kubectl logs -l job-name=parallel-work --prefix
```

Each log line shows a different Pod hostname picking up "one unit of work" — this is the pattern
for batch/fan-out jobs (e.g. processing a queue or a fixed list of files) where you want bounded
concurrency instead of either fully serial or fully unbounded.

## Cleanup

```bash
kubectl delete -f 02-job-parallel.yaml
kubectl delete -f 01-job-retry.yaml
kubectl delete -f 00-job-basic.yaml
```

## Command & flag glossary

| Command / flag | Means |
|---|---|
| `kubectl apply -f <file>` | Create (or update) whatever's described in that YAML file. |
| `kubectl get pods -l job-name=<name> -w` | List Pods labeled with the Job that owns them (Kubernetes auto-labels every Job's Pods with `job-name=<job>`) and `-w`atch for changes live instead of a one-time snapshot. |
| `kubectl get job <name>` | Shows a Job's `COMPLETIONS` (e.g. `1/1`, `6/6`) and `DURATION` — the summary view; `describe` below gives the blow-by-blow. |
| `kubectl describe job <name>` | Full detail including the event log — every Pod the Job controller created and why (`SuccessfulCreate`, `BackoffLimitExceeded`, etc). |
| `kubectl logs -l job-name=<name> --prefix` | Logs from every Pod matching the label at once, each line prefixed with which Pod it came from — needed here since a parallel Job has several Pods, not one. |
| `kubectl delete -f <file>` | The inverse of `apply` — remove exactly what that file describes. |

## Reference

| File | Demonstrates |
|---|---|
| `00-job-basic.yaml` | A Job runs its Pod once to completion and stops — no restart on success. |
| `01-job-retry.yaml` | `backoffLimit` — a failed Pod isn't restarted in place; the Job controller creates a new one, up to the limit. |
| `02-job-parallel.yaml` | `completions`/`parallelism` — bounded concurrent fan-out across many Pod runs. |
