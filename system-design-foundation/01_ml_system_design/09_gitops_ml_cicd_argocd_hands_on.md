# Hands-On: ArgoCD

A practical companion to the [GitOps & CI/CD for ML tutorial](09_gitops_ml_cicd.md#argocds-reconciliation-loop)
— that tutorial covers *why* GitOps and ArgoCD matter for ML deployments; this covers
*how* to actually stand it up, deploy something, and drive a canary rollout with it.

## What You'll Set Up

A local (or any) Kubernetes cluster running ArgoCD, watching a Git repo, deploying a
sample app declaratively — then adding Argo Rollouts on top for a canary release, the
GitOps-native implementation of the canary strategy from the
[model serving tutorial](04_model_serving_deployment.md).

## Prerequisites

- A Kubernetes cluster (`kind`, `minikube`, or any real cluster) with `kubectl` configured
- The `argocd` CLI (`brew install argocd` on macOS, or download from the ArgoCD releases page)

## 1. Install ArgoCD

```bash
kubectl create namespace argocd
kubectl apply -n argocd -f https://raw.githubusercontent.com/argoproj/argo-cd/stable/manifests/install.yaml

# wait for pods to be ready
kubectl -n argocd wait --for=condition=available --timeout=300s deployment --all
```

## 2. Access the UI and CLI

```bash
# port-forward the API server locally
kubectl -n argocd port-forward svc/argocd-server 8080:443 &

# get the auto-generated initial admin password
argocd admin initial-password -n argocd

# log in via CLI
argocd login localhost:8080 --username admin --password <password-from-above> --insecure
```

The UI is now at `https://localhost:8080` (self-signed cert — accept the browser warning
for local use).

## 3. Register a Git Repo

```bash
argocd repo add https://github.com/your-org/your-ml-manifests.git \
  --username <git-username> --password <git-token>
```

For a public repo, you can skip credentials entirely.

## 4. Create an Application

An ArgoCD `Application` is the core resource: it declares *what* Git repo/path to watch
and *where* to deploy it.

```yaml
# application.yaml
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: model-serving
  namespace: argocd
spec:
  project: default
  source:
    repoURL: https://github.com/your-org/your-ml-manifests.git
    targetRevision: main
    path: manifests/model-serving
  destination:
    server: https://kubernetes.default.svc
    namespace: model-serving
  syncPolicy:
    automated:
      prune: true       # remove resources deleted from Git
      selfHeal: true    # auto-correct manual drift (the reconciliation loop in action)
    syncOptions:
      - CreateNamespace=true
```

```bash
kubectl apply -f application.yaml
# or equivalently:
argocd app create model-serving \
  --repo https://github.com/your-org/your-ml-manifests.git \
  --path manifests/model-serving \
  --dest-server https://kubernetes.default.svc \
  --dest-namespace model-serving \
  --sync-policy automated --self-heal --auto-prune
```

## 5. Sync and Watch Drift Detection

```bash
argocd app get model-serving          # see sync/health status
argocd app sync model-serving         # manually trigger a sync (if not automated)
argocd app history model-serving      # see deployment history for rollback
```

**Try this to see drift detection work**: manually edit a resource ArgoCD manages
(`kubectl edit deployment ...` in the `model-serving` namespace) and watch `argocd app get`
show `OutOfSync` within seconds — with `selfHeal: true`, ArgoCD reverts your manual change
automatically. This is the reconciliation loop from the tutorial, observable directly.

## 6. The App-of-Apps Pattern

For managing many `Application` resources declaratively (rather than `kubectl apply`-ing
each one by hand), a "root" Application points at a directory of *other* Application
manifests:

```yaml
# root-app.yaml
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: root
  namespace: argocd
spec:
  project: default
  source:
    repoURL: https://github.com/your-org/your-ml-manifests.git
    targetRevision: main
    path: apps               # a directory containing multiple Application YAMLs
  destination:
    server: https://kubernetes.default.svc
    namespace: argocd
  syncPolicy:
    automated:
      prune: true
      selfHeal: true
```

Adding a new model-serving deployment becomes "add a new Application YAML file to `apps/`
and merge the PR" — no manual ArgoCD CLI commands needed at all going forward.

## 7. Canary Rollout with Argo Rollouts

Install Argo Rollouts, then replace a plain `Deployment` with a `Rollout` resource
declaring the canary strategy directly:

```bash
kubectl create namespace argo-rollouts
kubectl apply -n argo-rollouts -f https://github.com/argoproj/argo-rollouts/releases/latest/download/install.yaml
```

```yaml
# rollout.yaml
apiVersion: argoproj.io/v1alpha1
kind: Rollout
metadata:
  name: model-serving
spec:
  replicas: 5
  strategy:
    canary:
      steps:
        - setWeight: 20     # 20% of traffic to the new version
        - pause: { duration: 10m }
        - analysis:
            templates:
              - templateName: latency-and-error-rate   # guardrail check, see below
        - setWeight: 50
        - pause: { duration: 10m }
        - setWeight: 100
  selector:
    matchLabels:
      app: model-serving
  template:
    metadata:
      labels:
        app: model-serving
    spec:
      containers:
        - name: model-server
          image: your-registry/model-server:v2
```

The `analysis` step references an `AnalysisTemplate` — this is where the automated
guardrail-checking loop from the
[model serving tutorial's canary deep-dive](04_model_serving_deployment.md#deep-dive-designing-the-canary-evaluation-loop)
becomes a concrete Kubernetes resource, e.g. querying Prometheus for error rate and
failing the rollout automatically if it exceeds a threshold:

```yaml
# analysis-template.yaml
apiVersion: argoproj.io/v1alpha1
kind: AnalysisTemplate
metadata:
  name: latency-and-error-rate
spec:
  metrics:
    - name: error-rate
      interval: 1m
      successCondition: result[0] < 0.01
      provider:
        prometheus:
          address: http://prometheus.monitoring:9090
          query: |
            sum(rate(http_requests_total{app="model-serving",status=~"5.."}[5m]))
            /
            sum(rate(http_requests_total{app="model-serving"}[5m]))
```

```bash
kubectl argo rollouts get rollout model-serving --watch   # live rollout progress
kubectl argo rollouts promote model-serving               # manually advance a paused step
kubectl argo rollouts abort model-serving                 # abort and roll back
```

## Common Commands Cheat Sheet

| Command | What it does |
|---|---|
| `argocd app list` | List all managed Applications and their sync/health status |
| `argocd app get <name>` | Detailed status for one Application |
| `argocd app sync <name>` | Manually trigger a sync |
| `argocd app diff <name>` | Show the diff between live state and Git-declared state |
| `argocd app rollback <name> <history-id>` | Roll back to a previous deployed revision |
| `argocd app history <name>` | List deployment history |
| `kubectl argo rollouts get rollout <name> --watch` | Live-watch a canary rollout's progress |
| `kubectl argo rollouts promote <name>` | Advance a paused canary step manually |
| `kubectl argo rollouts abort <name>` | Abort a rollout and revert to the stable version |

## Troubleshooting

- **App stuck `Progressing` indefinitely**: usually a readiness probe never succeeding —
  check `kubectl describe pod` in the target namespace for the actual pod-level error, not
  just the ArgoCD status.
- **`OutOfSync` but the diff looks empty**: often a field ArgoCD tracks that your manifest
  doesn't explicitly set (Kubernetes defaulting a field your YAML omits) — use
  `argocd app diff` to see the exact field-level difference, and either set it explicitly
  or configure ArgoCD to ignore that field's differences.
- **Sync succeeds but the app doesn't actually behave differently**: check whether the
  image tag is mutable (`:latest`) — per the
  [tricky scenario on GitOps rollouts](12_tricky_scenarios_09_gitops_rollout_wrong_predictions.md),
  a mutable tag can mean "synced" doesn't mean "the artifact you expect is running."

## Articulate It: Interview Framing & Vocabulary

### Three Ways to Explain This

- **Demonstration-first (the default when asked to prove you've actually run this, not
  just read about it):** "I'd walk through it live: create an Application pointing at a
  Git path, let it sync, then manually edit the deployed resource with `kubectl edit` and
  watch ArgoCD flag it `OutOfSync` and self-heal within seconds. That's the reconciliation
  loop made concrete, not theoretical."
- **Escalation-framing (good for 'how would you scale this to many services'):** "A single
  Application resource doesn't scale past a handful of services — I'd reach for the
  app-of-apps pattern, where one root Application manages a directory of other Application
  manifests, so adding a new service becomes 'merge a PR that adds a YAML file,' not a
  manual CLI command."
- **Debugging-framing (good for troubleshooting questions):** "When something's
  `OutOfSync` but the diff looks empty, I don't trust the summary status — I go straight to
  `argocd app diff` for the field-level difference, since it's usually a Kubernetes-defaulted
  field my manifest just didn't set explicitly."

### Vocabulary Builder

**Technical shorthand — use these instead of over-explaining the concept every time:**

- **app-of-apps** (n. phrase) — a pattern where one root Application declaratively manages
  a set of other Applications, avoiding manual per-service setup.
- **mutable tag** (n. phrase) — an image reference (like `:latest`) that can point to
  different actual content over time, which can make "sync succeeded" misleading about
  what's actually running.
- **readiness probe** (n. phrase) — the Kubernetes health check a pod must pass before
  being considered ready; a common hidden cause of a rollout stuck `Progressing`.
- **canary weight** (n. phrase) — the percentage of traffic routed to a new version during
  a staged rollout, incremented in steps with pauses/analysis between them.

**Expressive phrases — for stating a trade-off fluently instead of listing pros/cons:**

- **"…observable directly, not just theoretical"** — useful for signaling you've actually
  run a mechanism (drift detection, self-heal) rather than only read about it.
- **"'Synced' doesn't mean…"** — a fluent template for flagging a subtle gap between a
  status indicator and the actual guarantee it implies (a mutable tag being "synced" without
  the expected artifact actually running).
- **granular** (adj.) — broken down to a fine level of detail. *"`argocd app diff` gives
  you the granular, field-level difference, not just a pass/fail sync status."*
- **"…no manual CLI commands needed going forward"** — a clean way to describe the payoff
  of investing in a declarative pattern (app-of-apps) up front.
- **staged** (adj.) — proceeding in deliberate, incremental steps rather than all at once.
  *"A staged canary with pauses and analysis steps bounds the blast radius of a bad
  rollout."*

---

**See also:** [GitOps & CI/CD for ML tutorial](09_gitops_ml_cicd.md) · [Hands-On: DVC](09_gitops_ml_cicd_dvc_hands_on.md)
