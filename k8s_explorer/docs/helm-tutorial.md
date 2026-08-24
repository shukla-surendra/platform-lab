# Helm Tutorial — every core command, worked against a real chart

A command-by-command walkthrough of Helm using [`sample-helm-chart/`](../sample-helm-chart/)
(`my-nginx` — one Deployment, one Service) as the example project. Every command below was run
live against this repo's `minikube` cluster; the output shown is the actual output, not
illustrative. [`helm-vs-kustomize.md`](./helm-vs-kustomize.md) covers *why* Helm exists next to
Kustomize in this repo — this doc is purely mechanical: install, inspect, change, undo, remove.

For the command refresher without the explanations, see the "Quick reference" table at the
bottom.

## The chart, piece by piece

```
sample-helm-chart/
  Chart.yaml              # name, version, description — the chart's own identity
  values.yaml              # the defaults every template reads from
  templates/
    deployment.yaml         # a Deployment, templated
    service.yaml             # a Service, templated
    NOTES.txt                 # printed after install/upgrade — not a K8s object
```

`Chart.yaml`:

```yaml
apiVersion: v2
name: my-nginx
version: 0.1.0
description: A simple Nginx Helm chart for Kubernetes
```

`version` is the **chart's** version (bump it when you change the templates/defaults) — not the
app's version. A chart for an app that never changes its own version number still gets `version`
bumps every time its Kubernetes-side behavior changes.

`values.yaml` — the defaults:

```yaml
replicaCount: 2

image:
  repository: nginx
  tag: latest
  pullPolicy: IfNotPresent

service:
  type: ClusterIP
  port: 80
```

`templates/deployment.yaml` — plain Kubernetes YAML with Go template expressions spliced in:

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: {{ .Release.Name }}-nginx
spec:
  replicas: {{ .Values.replicaCount }}
  ...
        image: "{{ .Values.image.repository }}:{{ .Values.image.tag }}"
```

Two objects are in scope inside every template:

| Object | Where it comes from | Example here |
|---|---|---|
| `.Values` | This chart's `values.yaml`, overridden by anything you pass at install/upgrade time (`-f`, `--set`) | `.Values.replicaCount` → `2` by default |
| `.Release` | Set by Helm itself for *this* install — not something you write | `.Release.Name` → whatever name you pass to `helm install <name> ...` |

That's why the Deployment is named `{{ .Release.Name }}-nginx` rather than a hardcoded
`my-nginx`: installing this same chart twice under two release names (e.g. `helm install
staging .` and `helm install prod .`) produces two non-colliding sets of objects
(`staging-nginx`, `prod-nginx`) from one chart, with no template edits.

## 1. Render without touching the cluster

Before installing anything, see exactly what Helm *would* create — this substitutes `.Values`
and `.Release` and prints plain YAML, no API calls made:

```bash
cd k8s_explorer/sample-helm-chart
helm template my-nginx .
```

```yaml
---
# Source: my-nginx/templates/service.yaml
apiVersion: v1
kind: Service
metadata:
  name: my-nginx-nginx
spec:
  type: ClusterIP
  selector:
    app: nginx
  ports:
  - port: 80
    targetPort: 80
---
# Source: my-nginx/templates/deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: my-nginx-nginx
spec:
  replicas: 2
  ...
```

`helm template <release-name> <chart-path>` — the release name here is never actually registered
anywhere; it only exists to fill in `{{ .Release.Name }}` for the render. Reach for this any time
you've changed `values.yaml` or a template and want to see the resulting YAML before it goes
anywhere near a cluster — the same instinct as `terraform plan`.

```bash
helm lint .
```

```
==> Linting .
[INFO] Chart.yaml: icon is recommended

1 chart(s) linted, 0 chart(s) failed
```

Static checks: malformed YAML, missing required fields, bad indentation inside a template
expression. Catches syntax mistakes `helm template` would also expose, but faster and with
clearer error locations — run this first, `helm template` second when something's actually wrong.

## 2. Install

```bash
helm install my-nginx . -n helm-tutorial --create-namespace
```

```
NAME: my-nginx
LAST DEPLOYED: Mon Aug 24 06:28:40 2026
NAMESPACE: helm-tutorial
STATUS: deployed
REVISION: 1
DESCRIPTION: Install complete
TEST SUITE: None
NOTES:
my-nginx-nginx deployed — 2 replica(s) of nginx:latest

Look at it locally:

  kubectl port-forward svc/my-nginx-nginx 8080:80
  open http://localhost:8080
```

| Piece | Meaning |
|---|---|
| `my-nginx` | The **release name** — a name *you* pick, not read from `Chart.yaml`. Everything below refers back to it. |
| `.` | The chart path — current directory. Could also be `./sample-helm-chart` from elsewhere, or `repo/chart-name` for a chart added via `helm repo add`. |
| `-n helm-tutorial` | Target namespace. Short for `--namespace`. |
| `--create-namespace` | Create `helm-tutorial` if it doesn't exist yet. Only takes effect on `install` — `helm upgrade` against a namespace that no longer exists fails even with this flag. |
| `REVISION: 1` | Every install/upgrade/rollback bumps this. It's how `helm rollback` knows what "go back to" means. |
| `NOTES:` | The rendered contents of `templates/NOTES.txt` — a template file whose output is printed, not applied to the cluster. Every chart in this repo ships one with the actual next command to run. |

Check what actually landed:

```bash
kubectl -n helm-tutorial get pods
```

```
NAME                              READY   STATUS              RESTARTS   AGE
my-nginx-nginx-59f86b59ff-9mqqn   0/1     ContainerCreating   0          0s
my-nginx-nginx-59f86b59ff-slfqz   0/1     ContainerCreating   0          0s
```

`helm install` returning success means the API server **accepted** the objects — it says nothing
about whether the Pods actually come up healthy. Wait for that separately:

```bash
kubectl -n helm-tutorial wait --for=condition=available deployment/my-nginx-nginx --timeout=90s
```

## 3. Inspect a running release

```bash
helm list -n helm-tutorial
```

```
NAME    	NAMESPACE    	REVISION	UPDATED                                	STATUS  	CHART         	APP VERSION
my-nginx	helm-tutorial	1       	2026-08-24 06:28:40.990821009 +0000 UTC	deployed	my-nginx-0.1.0	
```

Every release, in the given namespace. Add `-A` to list every release in every namespace at
once — the first command to run when you've forgotten what's installed where.

```bash
helm status my-nginx -n helm-tutorial
```

Same `NOTES:` block as install, plus the current state of every object the release owns
(`Service`, `Deployment`, related `Pod`s) — the re-run-anytime version of the install output,
without re-installing anything.

```bash
helm get values my-nginx -n helm-tutorial
```

```
USER-SUPPLIED VALUES:
null
```

`null` here because this install used every default in `values.yaml` untouched — this command
shows only what **you** overrode, not the fully-merged config (that's `helm get values -a`
instead, which also has "computed from every chart default" values mixed in and is noisier to
read).

## 4. Change something: upgrade

```bash
helm upgrade my-nginx . -n helm-tutorial --set replicaCount=3
```

```
Release "my-nginx" has been upgraded. Happy Helming!
NAME: my-nginx
...
REVISION: 2
DESCRIPTION: Upgrade complete
NOTES:
my-nginx-nginx deployed — 3 replica(s) of nginx:latest
```

`--set replicaCount=3` overrides one value from the command line — fine for a quick one-off, but
it is **not remembered** on the next `helm upgrade`: run `helm upgrade my-nginx .` again with no
flags and it reverts to `values.yaml`'s `replicaCount: 2`. For anything you want to persist,
either edit `values.yaml` directly, or keep an override file and pass it every time:

```bash
helm upgrade my-nginx . -n helm-tutorial -f my-values.yaml
```

Confirm the override actually took:

```bash
helm get values my-nginx -n helm-tutorial
```
```
USER-SUPPLIED VALUES:
replicaCount: 3
```
```bash
kubectl -n helm-tutorial get pods
```
```
NAME                              READY   STATUS              RESTARTS   AGE
my-nginx-nginx-59f86b59ff-9mqqn   1/1     Running             0          30s
my-nginx-nginx-59f86b59ff-slfd7   0/1     ContainerCreating   0          1s
my-nginx-nginx-59f86b59ff-slfqz   1/1     Running             0          30s
```

`helm upgrade` diffs the rendered YAML against what's currently on the cluster and patches only
what changed — the Service (untouched) wasn't touched; the Deployment's `replicas` field was, and
Kubernetes' own Deployment controller took it from there (scheduled one more Pod).

`helm upgrade --install <name> <path> -n <ns> --create-namespace` combines install+upgrade into
one idempotent command — "make the cluster match what's on disk, whether or not it's already
installed." Every chart README in this repo (`metrics-stack`, `evidently_stack`,
`grafana-log-viewer`) documents this as the safe default for CI/repeatable scripts.

## 5. See what changed, and undo it: history + rollback

```bash
helm history my-nginx -n helm-tutorial
```

```
REVISION	UPDATED                 	STATUS    	CHART         	APP VERSION	DESCRIPTION
1       	Mon Aug 24 06:28:40 2026	superseded	my-nginx-0.1.0	           	Install complete
2       	Mon Aug 24 06:29:10 2026	deployed  	my-nginx-0.1.0	           	Upgrade complete
```

Every revision Helm has ever produced for this release, kept even after `helm upgrade` moves
past it — this history (stored as Secrets in the release's namespace by default) is what makes
rollback possible without you having to remember what the previous values were.

```bash
helm rollback my-nginx 1 -n helm-tutorial
```

```
Rollback was a success! Happy Helming!
```

```bash
helm history my-nginx -n helm-tutorial
```

```
REVISION	UPDATED                 	STATUS    	CHART         	APP VERSION	DESCRIPTION
1       	Mon Aug 24 06:28:40 2026	superseded	my-nginx-0.1.0	           	Install complete
2       	Mon Aug 24 06:29:10 2026	superseded	my-nginx-0.1.0	           	Upgrade complete
3       	Mon Aug 24 06:29:14 2026	deployed  	my-nginx-0.1.0	           	Rollback to 1
```

**Rollback is not "delete revision 2" — it's a new revision (3) whose content matches
revision 1's.** History only ever grows forward; nothing is erased. `helm get values` afterward
confirms `replicaCount` is back to `null` (i.e. the `values.yaml` default of 2), matching what
revision 1 actually had.

## 6. Reach the app

```bash
kubectl -n helm-tutorial port-forward svc/my-nginx-nginx 8080:80
curl -s -o /dev/null -w "HTTP %{http_code}\n" http://localhost:8080
```

```
HTTP 200
```

Confirms the Service actually routes to a healthy Pod, not just that the objects exist. See
[`accessing-pods-and-services.md`](./accessing-pods-and-services.md) for `port-forward` vs.
Ingress vs. `NodePort`/`minikube service` as the other ways in.

## 7. Remove it

```bash
helm uninstall my-nginx -n helm-tutorial
```

```
release "my-nginx" uninstalled
```

Deletes every object the release owns (Deployment, Service — and their Pods, cleaned up by the
Deployment controller once its ReplicaSet is gone) and clears the release from `helm list`.
**Does not** delete the namespace itself, even if `--create-namespace` created it on install:

```bash
kubectl delete namespace helm-tutorial
```

## What this chart doesn't show: dependencies

`sample-helm-chart` has no `dependencies:` block in `Chart.yaml` — every object it creates is
defined in its own `templates/`. Most real-world charts in this repo instead **wrap** an
upstream chart:

```yaml
# k8s_observability/metrics-stack/Chart.yaml
dependencies:
  - name: kube-prometheus-stack
    version: "88.2.0"
    repository: "https://prometheus-community.github.io/helm-charts"
```

That adds one extra first-time step before any of the commands above work — pulling the
dependency down into a local `charts/` folder:

```bash
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm dependency build .        # reads Chart.lock if present, else resolves + writes one
```

After that, `install`/`upgrade`/`uninstall`/`rollback` all work exactly as above — the only
difference is that `values.yaml` now nests everything under the dependency's name
(`kube-prometheus-stack:` as a top-level key) to configure the subchart instead of top-level
keys configuring templates you own. See
[`../../k8s_observability/metrics-stack`](../../k8s_observability/metrics-stack) (its
`README.md`) for that chart's full install walkthrough, and
[`../grafana-log-viewer`](../grafana-log-viewer) (its `README.md`) for a second worked example
(wrapping `loki-stack`) including the `helm dependency update` vs. `helm dependency build`
distinction (`update` re-resolves versions against `Chart.yaml`; `build` trusts the existing
`Chart.lock` — prefer `build` once a `Chart.lock` exists, so a dependency doesn't silently move
to a newer version you didn't ask for).

## Quick reference

```bash
helm template <name> <path>                    # render to YAML, no cluster call
helm lint <path>                                # static checks on the chart

helm install <name> <path> -n <ns> --create-namespace
helm upgrade <name> <path> -n <ns> [--set k=v] [-f values.yaml]
helm upgrade --install <name> <path> -n <ns> --create-namespace   # idempotent either way

helm list -n <ns>                               # releases in one namespace
helm list -A                                    # every release, every namespace
helm status <name> -n <ns>                      # NOTES.txt + object status, re-runnable
helm get values <name> -n <ns>                  # what YOU overrode
helm get values <name> -n <ns> -a                # fully-merged values, including defaults
helm get manifest <name> -n <ns>                # the exact YAML currently applied

helm history <name> -n <ns>                     # every revision
helm rollback <name> <revision> -n <ns>          # new revision matching an old one's content

helm uninstall <name> -n <ns>                    # removes objects, not the namespace
kubectl delete namespace <ns>                    # only if --create-namespace made it

helm dependency build <path>                     # fetch subcharts per Chart.lock (preferred)
helm dependency update <path>                    # re-resolve + rewrite Chart.lock
```
