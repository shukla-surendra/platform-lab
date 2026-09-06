# What `helm upgrade --install gridwork ./gridwork` actually creates

Reference output, one real `kubectl get all` after a clean install on `aks-dev`:

```
NAME                                    READY   STATUS      RESTARTS        AGE
pod/gridwork-backend-7484674458-zjvsw   1/1     Running     1 (2m13s ago)   2m56s
pod/gridwork-frontend-f4bd8d655-g7c6z   1/1     Running     0               2m56s
pod/gridwork-migrate-1-kjjh6            0/1     Completed   0               2m56s
pod/gridwork-postgres-0                 1/1     Running     0               2m56s
pod/gridwork-redis-575846c79d-9ftln     1/1     Running     0               2m56s

NAME                        TYPE        CLUSTER-IP     EXTERNAL-IP   PORT(S)        AGE
service/gridwork-backend    ClusterIP   10.1.139.55    <none>        8000/TCP       2m56s
service/gridwork-frontend   NodePort    10.1.217.192   <none>        80:32636/TCP   2m56s
service/gridwork-postgres   ClusterIP   None           <none>        5432/TCP       2m56s
service/gridwork-redis      ClusterIP   10.1.172.204   <none>        6379/TCP       2m56s
service/kubernetes          ClusterIP   10.1.0.1       <none>        443/TCP        99m

NAME                                READY   UP-TO-DATE   AVAILABLE   AGE
deployment.apps/gridwork-backend    1/1     1            1           2m56s
deployment.apps/gridwork-frontend   1/1     1            1           2m56s
deployment.apps/gridwork-redis      1/1     1            1           2m56s

NAME                                          DESIRED   CURRENT   READY   AGE
replicaset.apps/gridwork-backend-7484674458   1         1         1       2m56s
replicaset.apps/gridwork-frontend-f4bd8d655   1         1         1       2m56s
replicaset.apps/gridwork-redis-575846c79d     1         1         1       2m56s

NAME                                 READY   AGE
statefulset.apps/gridwork-postgres   1/1     2m56s

NAME                           STATUS     COMPLETIONS   DURATION   AGE
job.batch/gridwork-migrate-1   Complete   1/1           55s        2m56s
```

## Pods — the actual running containers

| Pod | What it is |
|---|---|
| `gridwork-backend-...` | FastAPI app container, `1/1` — one container, ready |
| `gridwork-frontend-...` | nginx serving the static Next.js export + proxying `/api/` |
| `gridwork-migrate-1-...` | `0/1 Completed` — ran once, did its job (Alembic migrations), exited 0. `0/1` here means "0 *of its containers currently running*," not failure — Jobs are supposed to end at 0/1 |
| `gridwork-postgres-0` | the `-0` suffix is the StatefulSet giveaway — a stable, numbered identity, not a random hash suffix like the others |
| `gridwork-redis-...` | cache/broker, no persistence, so it's a plain Deployment like backend/frontend |

## Why 3 Deployments but 1 StatefulSet

- **Deployment** (backend, frontend, redis): stateless — any replica is interchangeable, pods get random-hash names, can be killed and replaced with a fresh one at a new IP with zero consequence.
- **StatefulSet** (postgres): the data on disk *is* the identity. It gets a stable name (`gridwork-postgres-0` forever, not `-xk29f`) and a stable PersistentVolumeClaim bound to that ordinal, so if the pod is rescheduled, `-0` comes back and reattaches to the *same* disk instead of starting empty. That's `templates/postgres.yaml`.

Each Deployment also owns a **ReplicaSet**, which is the thing actually enforcing "keep N pods alive" — the Deployment itself is just a versioned wrapper around ReplicaSets, so a future rolling update creates a new ReplicaSet and scales the old one to 0 rather than editing pods in place. That's why you see `replicaset.apps/gridwork-backend-7484674458` (that hash is a checksum of the pod template — bump the image tag or change an env var and you'd get a new hash and a new ReplicaSet).

## Job — runs once, not a long-lived workload

`job.batch/gridwork-migrate-1` — this is `templates/migration-job.yaml`, annotated `helm.sh/hook: post-install,pre-upgrade`. Helm doesn't create this as a normal chart resource that lives alongside everything else on every reconcile — it runs it as a *hook*, before the backend Deployment's pods are even created on install, and again before any future `helm upgrade` rolls new backend pods out. `COMPLETIONS 1/1`, `DURATION 55s` — it ran `alembic upgrade head` against Postgres and exited. The `-1` suffix is the Helm **revision number**, so a second `helm upgrade` produces `gridwork-migrate-2`, never reusing the name (Job names can't be reused once they've run).

## Services — 3 different flavors, each solving a different problem

| Service | Type | CLUSTER-IP | Why |
|---|---|---|---|
| `gridwork-backend` | ClusterIP | real IP | internal-only DNS name + stable IP so frontend's nginx can proxy to `gridwork-backend:8000` regardless of which pod/IP is actually behind it right now |
| `gridwork-frontend` | **NodePort** | real IP | the *only* thing meant to be reachable from outside the cluster — exposes port `32636` on every node's own IP, which is what `kubectl port-forward svc/gridwork-frontend 8080:80` tunnels into |
| `gridwork-postgres` | ClusterIP, **`None`** | `None` = headless | deliberate, not a default. A headless Service skips load-balancing entirely and instead makes DNS return the pod's own IP directly (`gridwork-postgres-0.gridwork-postgres`) — required for StatefulSets, since "any Postgres replica will do" is false; the backend needs to reach that *specific* pod's disk |
| `gridwork-redis` | ClusterIP | real IP | same pattern as backend — Redis is stateless-enough here (cache, not durable data) that a normal load-balanced ClusterIP is fine |
| `kubernetes` | ClusterIP | `10.1.0.1` | not part of this chart — every cluster gets this automatically, it's how pods reach the Kubernetes API server itself |

Every one of these `gridwork-*` Service DNS names — `gridwork-postgres`, `gridwork-redis`, `gridwork-backend` — traces back to `_helpers.tpl`'s `pa.fullname` (= `.Release.Name`, set to `gridwork` throughout this chart's docs) and gets wired into containers via `templates/configmap-backend.yaml` (`DB_HOST`, `REDIS_URL`) rather than hardcoded, so renaming the release would rewire all of it automatically.

## The `RESTARTS 1` on backend — root-caused, not a mystery

`gridwork-backend` showed `RESTARTS 1` on a clean install. Pulling the previous container's logs (`kubectl logs pod/gridwork-backend-... --previous`) showed the cause directly:

```
ERROR - Database connection attempt 1 failed: (psycopg2.OperationalError)
  could not translate host name "gridwork-postgres" to address: Name or service not known
... (5 attempts, 5s apart) ...
ERROR - Max retries reached. Could not connect to database.
```

This is a **DNS/CoreDNS** failure, not a "Postgres not accepting connections yet" failure — those look different (that one says "connection refused"). The backend tried to resolve `gridwork-postgres` 5 times, 5 seconds apart, gave up, and exited. Kubernetes' default restart policy (`Always`) restarted the container, and the second attempt succeeded — Postgres's pod IP had been registered in CoreDNS by then.

**Why it happens:** the migration Job's `pre-upgrade`/`post-install` hook only guarantees the Job *itself* doesn't start before Postgres exists in the manifest — Helm doesn't block on Postgres being *DNS-resolvable*, and nothing in `backend.yaml` has an `initContainer` or readiness gate on Postgres either. On a cold cluster, Postgres's pod and the backend's pod can come up close enough together that CoreDNS hasn't propagated the new pod's record yet when the backend's very first connection attempt fires.

**Why it's not worth fixing here:** the backend's own retry loop (5 attempts, 5s apart — application code, not Kubernetes) is exactly what turns this into a harmless one-time restart instead of a permanent crash-loop. If that retry loop didn't exist, the fix would be a Kubernetes-level one — an `initContainer` doing `until nslookup gridwork-postgres; do sleep 1; done` before the main container starts, or just more/longer app-level retries. Given it self-heals in one restart cycle, this is expected behavior for a dev-lab chart, not a bug — recorded here so the restart count doesn't look mysterious the next time `kubectl get all` shows it.
