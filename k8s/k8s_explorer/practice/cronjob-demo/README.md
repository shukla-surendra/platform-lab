# cronjob-demo

Hands-on companion to the CronJob section of
[`docs/workload-types.md`](../docs/workload-types.md). One manifest: a CronJob that runs every
minute and prints a timestamp.

A CronJob is really just a template for creating `Job`s on a schedule — if the mechanics of a
Job itself (retries, parallelism) aren't already familiar, see [`job-demo/`](../job-demo) first.

Assumes a running `minikube` cluster (`minikube status`).

## Apply it

```bash
kubectl apply -f 00-cronjob.yaml
kubectl get cronjob hello-cronjob
```

`LAST SCHEDULE` starts `<none>`. Wait for the top of the next minute (`schedule: "*/1 * * * *"`),
then:

```bash
kubectl get jobs -l app=cronjob-demo --watch
kubectl get cronjob hello-cronjob
```

A new `Job` named `hello-cronjob-<timestamp>` appears each tick — the CronJob controller creates
an ordinary `Job` at each scheduled time; it doesn't run Pods directly, and each of those Jobs
behaves exactly like the ones in [`job-demo/`](../job-demo):

```bash
kubectl logs job/<one-of-the-generated-job-names>
```

`successfulJobsHistoryLimit: 3` / `failedJobsHistoryLimit: 1` cap how many old Jobs stick around
so this doesn't accumulate forever.

## Trigger a run on demand

Useful for testing a CronJob's container without waiting for the schedule:

```bash
kubectl create job --from=cronjob/hello-cronjob manual-run-1
kubectl logs job/manual-run-1
```

## `concurrencyPolicy: Forbid`

If a tick fires while the previous run's Job is still going, the new one is skipped rather than
overlapping — matters for anything that shouldn't run twice concurrently against the same
resource (a backup, a report against shared state). The other options are `Allow` (default —
runs overlap freely) and `Replace` (cancel the still-running one, start the new tick).

## Cleanup

```bash
kubectl delete -f 00-cronjob.yaml
kubectl delete job manual-run-1 --ignore-not-found
```

Deleting a CronJob does **not** automatically delete the Jobs it already created — `kubectl get
jobs -l app=cronjob-demo` afterward to check for stragglers beyond the history limits above.

## Command & flag glossary

| Command / flag | Means |
|---|---|
| `kubectl apply -f <file>` | Create (or update) whatever's described in that YAML file. |
| `kubectl get cronjob <name>` | Shows a CronJob's `SCHEDULE`, `LAST SCHEDULE`, and whether it's currently `SUSPEND`ed. |
| `kubectl get jobs -l app=cronjob-demo --watch` | List Jobs carrying this demo's label and watch new ones appear live as the schedule ticks. |
| `kubectl create job --from=cronjob/<name> <job-name>` | Manually create one Job from a CronJob's template right now, without waiting for or changing its schedule — the standard way to test a CronJob's container on demand. |
| `kubectl delete -f <file>` | The inverse of `apply` — remove exactly what that file describes. |

## Reference

| File | Demonstrates |
|---|---|
| `00-cronjob.yaml` | A CronJob creates a plain `Job` at each scheduled tick; `concurrencyPolicy` controls overlap. |
