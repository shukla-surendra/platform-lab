# Connecting to the Cluster with `kubectl`

How `kubectl` on your laptop reaches this AKS cluster, what credentials it
uses, and how to switch, clean up and troubleshoot. Everything here was run
against the real cluster (`aks-svc-lf508l`, K8s server v1.35.8, kubectl client
v1.36.1).

## TL;DR

```bash
cd cloud-practice/azure/terraform/aks-services

az login                                   # once, if not already signed in
az aks get-credentials \
  --resource-group "$(terraform output -raw resource_group_name)" \
  --name           "$(terraform output -raw cluster_name)" \
  --overwrite-existing

kubectl get nodes
```

## Prerequisites

| Tool | Why | Check |
|---|---|---|
| Azure CLI (`az`) | Fetches the kubeconfig from Azure | `az account show` shows the subscription that holds the cluster |
| `kubectl` | Talks to the API server | `kubectl version --client`. Keep it within ±1 minor version of the server (1.35) |
| Terraform outputs | Supply the RG and cluster names so you don't copy them by hand | `terraform output` |

**`kubelogin` is not needed for this cluster.** It is only required when
Entra ID (AAD) integration is enabled (see [Auth model](#the-auth-model-for-this-cluster)).

## What `az aks get-credentials` actually does

1. It calls the Azure management API (`listClusterUserCredential`) using your
   `az login` identity. **Your Azure RBAC decides whether you can download the
   kubeconfig at all.** Owner/Contributor on the RG is enough. The narrow roles
   are *Azure Kubernetes Service Cluster User Role* and *... Cluster Admin Role*.
2. It **merges** the result into `~/.kube/config` (or the file given with `--file`) as three entries:

   | kubeconfig entry | Value for this cluster |
   |---|---|
   | cluster | `aks-svc-lf508l` → `https://akssvclf508l-<hash>.hcp.centralindia.azmk8s.io:443` + the cluster CA |
   | user | `clusterUser_rg-aks-services-demo_aks-svc-lf508l` → client certificate + key + token |
   | context | `aks-svc-lf508l` (cluster + user) |

3. It sets that context as **current**. The CLI prints
   `Merged "aks-svc-lf508l" as current context in ~/.kube/config`.

`--overwrite-existing` replaces an existing entry with the same name. You'll
want that after a `destroy` + `apply` that reuses names. Without it the
merge fails when the names clash.

## The auth model for this cluster

```bash
az aks show -g rg-aks-services-demo -n aks-svc-lf508l \
  --query "{aad:aadProfile, rbac:enableRbac, localDisabled:disableLocalAccounts, private:apiServerAccessProfile.enablePrivateCluster}"
# { "aad": null, "rbac": true, "localDisabled": false, "private": false }
```

| Setting | Value | Meaning |
|---|---|---|
| Entra ID integration | **off** (`aad: null`) | No Azure sign-in at the Kubernetes layer |
| Local accounts | **enabled** | The downloaded kubeconfig contains a long-lived **client certificate** |
| Kubernetes RBAC | on | RBAC is enforced, but see below |
| Private cluster | no | The API server has a **public** endpoint |
| Authorized IP ranges | none | The endpoint accepts connections from any IP (it still requires a valid cert) |

Who does the API server think you are?

```bash
kubectl auth whoami
# Username    masterclient
# Groups      [system:masters system:authenticated]
```

**You are cluster-admin.** Without Entra ID, the "user" credential and the
`--admin` credential are both the `masterclient` certificate in
`system:masters`, which bypasses RBAC. Consequences:

- Anyone holding your `~/.kube/config` entry has full control of the cluster until the cert expires or is rotated.
  Treat the file like a password.
- Revoking access means rotating the certs: `az aks rotate-certs -g ... -n ...`
  (this restarts the nodes and invalidates **all** kubeconfigs).
- Fine for a throwaway lab. For anything real, turn on Entra ID + Azure RBAC and
  `disable_local_accounts`. Then `get-credentials` returns an exec-plugin
  config that calls `kubelogin`, and every user gets their own identity.

## Everyday commands

```bash
kubectl config current-context        # which cluster am I pointed at?
kubectl config get-contexts           # all clusters in ~/.kube/config
kubectl config use-context aks-svc-lf508l

kubectl cluster-info                  # API server, CoreDNS, metrics-server endpoints
kubectl get nodes -o wide             # 1 node, InternalIP 10.224.0.4
kubectl get pods -A                   # kube-system add-ons
kubectl get svc -A
```

### Keeping this cluster out of your main kubeconfig (optional)

```bash
az aks get-credentials -g rg-aks-services-demo -n aks-svc-lf508l \
  --file ./kubeconfig-aks-services
export KUBECONFIG=$PWD/kubeconfig-aks-services
kubectl get nodes
```

> This file holds an admin credential. This module's `.gitignore` already
> excludes `kubeconfig*`, so it won't be committed, but it's still better kept outside
> the repo (e.g. `--file ~/.kube/aks-services`).

## Alternatives that don't need your kubeconfig

| Method | Command | When |
|---|---|---|
| Run commands through the Azure API | `az aks command invoke -g rg-aks-services-demo -n aks-svc-lf508l --command "kubectl get pods -A"` | Private clusters, or when you only have Azure access. It runs in a temporary pod in the cluster |
| Azure portal | Cluster → *Kubernetes resources* | Browse workloads and Services in the UI |
| Cloud Shell | `az aks get-credentials ...` then `kubectl` | No local tools |

## Cleaning up after `terraform destroy`

`destroy` removes the cluster but **not** its entries in `~/.kube/config`.
Stale contexts from old lab clusters pile up, and `kubectl` against them just
times out / fails DNS resolution. Remove them:

```bash
kubectl config delete-context aks-svc-lf508l
kubectl config delete-cluster aks-svc-lf508l
kubectl config delete-user    clusterUser_rg-aks-services-demo_aks-svc-lf508l
kubectl config get-contexts   # check what's left, and use-context something valid
```

## Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| `dial tcp: lookup akssvc...azmk8s.io: no such host` | Cluster was destroyed/recreated, or you're on a stale context | `kubectl config current-context`; re-run `get-credentials --overwrite-existing` |
| `A different object named ... already exists` | Name clash on merge | Add `--overwrite-existing` |
| `AuthorizationFailed ... listClusterUserCredential` | Your Azure identity lacks rights on the cluster | Grant *AKS Cluster User Role* (or Contributor) on the cluster/RG |
| `(SubscriptionNotFound)` / `ResourceNotFound` | `az` pointed at the wrong subscription | `az account set --subscription <id>` |
| `Unable to connect to the server: x509 ...` | Certs were rotated | Re-run `get-credentials --overwrite-existing` |
| `kubelogin is not installed` | Only happens when Entra ID is enabled | `brew install Azure/kubelogin/kubelogin` or `az aks install-cli` |
| Requests hang / time out | Cluster **stopped** (`az aks stop`) or authorized IP ranges exclude you | `az aks show --query powerState`; `az aks start`; check `apiServerAccessProfile` |
| Version skew warning | kubectl more than one minor version from the server | `az aks install-cli` or install a matching kubectl |

## How the traffic flows

```
kubectl (laptop)
   │  HTTPS :443, client cert from ~/.kube/config
   ▼
akssvclf508l-<hash>.hcp.centralindia.azmk8s.io   public API server endpoint (Azure-managed, not in your subscription)
   │  konnectivity tunnel (initiated by the node, outbound via the "kubernetes" LB)
   ▼
node aks-system-31524237-vmss000000 (10.224.0.4)  kubelet: used by logs / exec / port-forward
```

`kubectl get` / `apply` stop at the API server. `kubectl logs`, `exec` and
`port-forward` go on through the konnectivity tunnel to the kubelet. That's
why those three break when node outbound connectivity is broken, while
`get` keeps working.
