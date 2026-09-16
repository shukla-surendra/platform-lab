# 6. Build, push, deploy

Everything here runs from `/tmp/webapp-operator` (step 3's scaffold,
with the hand-written files copied in) against the cluster/registry step 1
created.

## Build and push the operator image

```bash
cd /tmp/webapp-operator
export ACR_LOGIN_SERVER=$(terraform -chdir=$OLDPWD/k8s/aks_crd_operator/infra output -raw acr_login_server)
export IMG="${ACR_LOGIN_SERVER}/webapp-operator:v0.1.0"

make docker-build IMG="$IMG"
az acr login --name "${ACR_LOGIN_SERVER%%.*}"
make docker-push IMG="$IMG"
```

`make docker-build`/`docker-push` are Makefile targets Kubebuilder generated
in step 3 — they wrap `docker build -t "$IMG" .` and `docker push "$IMG"`
using this repo's `Dockerfile`.

## Install the CRD

```bash
make install
```

Runs `kubectl apply -f config/crd/bases/` under the hood — registers
`webapps.webapp.platformlab.dev` with the API server. Confirm:

```bash
kubectl get crd webapps.webapp.platformlab.dev
```

This step alone doesn't run any controller — per
`k8s_explorer/docs/crds-and-operators.md`, a CRD with nothing watching it is
inert schema. `kubectl apply` a `WebApp` right now and it would sit in etcd
with no Deployment ever appearing. The next step is what starts the watcher.

## Deploy the operator (manager + RBAC)

```bash
make deploy IMG="$IMG"
```

Applies `config/rbac/` (the ServiceAccount + ClusterRole from step 5's
markers) and `config/manager/` (a Deployment running the image just pushed)
into a new `webapp-operator-system` namespace.

```bash
kubectl get pods -n webapp-operator-system
kubectl logs -n webapp-operator-system deploy/webapp-operator-controller-manager -f
```

Wait for the Pod to reach `Running` and the log line `"starting manager"`
(from `main.go`) before moving to step 7 — if the Pod is stuck in
`ImagePullBackOff`, it's almost always `IMG` not matching what `az acr login`
authenticated against, or the Terraform `AcrPull` role assignment from step 1
not having propagated yet (usually resolves within a minute; `kubectl
describe pod` shows the exact pull error).

## Why no `imagePullSecret` anywhere in `config/manager/`

Because of `azurerm_role_assignment.aks_acr_pull` in `infra/main.tf` — the
AKS cluster's own kubelet identity has `AcrPull` on the registry, so any Pod
scheduled on this cluster can pull from `akscrdlabacr01` without a
per-namespace pull secret. This is AKS+ACR-specific; the same
`config/manager/manager.yaml` deployed to a non-Azure cluster pulling from
this same ACR would need an explicit `imagePullSecrets` entry instead.
