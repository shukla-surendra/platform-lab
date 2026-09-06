This builds on `minimul_aks/main.tf` by adding two new resources: an Azure Container Registry (ACR) and a separate user node pool.

## ACR

```
resource "azurerm_container_registry" "acr" {
  name                = "aksdevacr123"
  resource_group_name = azurerm_resource_group.aks.name
  location            = azurerm_resource_group.aks.location
  sku                 = "Basic"
}
```

AKS doesn't build or store your application images — you need a registry for that. ACR is Azure's managed container registry.

ACR names must be globally unique and alphanumeric only (no hyphens/underscores) — that's why this is `aksdevacr123` instead of following the `rg-aks-dev` / `vnet-aks-dev` naming style used elsewhere in this setup.

then push

```
aksdevacr123.azurecr.io/frontend
aksdevacr123.azurecr.io/backend
```

```
ACR
├── frontend
│   └── image:tag
└── backend
    └── image:tag
```

Missing piece: creating the ACR doesn't let AKS pull from it. AKS's kubelet identity needs the `AcrPull` role on the registry (e.g. via `az aks update --attach-acr` or an `azurerm_role_assignment`), or pods referencing these images will fail with `ImagePullBackOff`.

## User Node Pool

```
# 5.  A separate User Node Pool
resource "azurerm_kubernetes_cluster_node_pool" "user" {

  name = "userpool"
  kubernetes_cluster_id = azurerm_kubernetes_cluster.aks.id
  vm_size    = "Standard_D2s_v5"
  node_count = 1
  vnet_subnet_id = azurerm_subnet.aks.id

}
```

Separates application workloads from the system node pool (`default_node_pool` in the cluster resource, running `Standard_D4s_v5`). Splitting them means:

- Application pods don't compete with system pods (CoreDNS, metrics-server, etc.) for resources.
- Each pool can use a different, independently-sized VM SKU — a smaller `Standard_D2s_v5` here vs. the system pool's `Standard_D4s_v5`.
- Each pool scales independently.

Missing piece: nothing here tells Kubernetes to actually schedule application pods onto this pool instead of the system one. That needs either a taint on the system pool (AKS's own convention is `CriticalAddonsOnly=true:NoSchedule`) with a matching toleration on system workloads, or a `nodeSelector`/affinity rule on your application deployments targeting this pool.

## One thing to check

`main.tf` still has `node_provisioning_profile { mode = "Auto" }` on the cluster (carried over from the base setup) at the same time this file adds a manually-defined `userpool`. That mode is AKS's Node Autoprovisioning (auto-creates/sizes/scales node pools for you, Karpenter-style) — worth confirming whether a manually-defined pool alongside it behaves the way you expect, or whether it's redundant with what NAP would provision on its own.

## What else you could add here

- **ACR → AKS role assignment** (`azurerm_role_assignment` granting `AcrPull` to the cluster's kubelet identity) — the single most impactful missing piece; without it the registry is unreachable from inside the cluster.
- **Taint the system pool / label the user pool** so workloads land where you intend, rather than wherever the scheduler happens to place them.
- **Autoscaling** (`enable_auto_scaling = true`, `min_count`/`max_count`) on the user pool at least — right now both pools are fixed at `node_count = 1`.
- **Log Analytics workspace + `oms_agent` block** on the cluster — container insights/logs, the next item down from Node Pools/ACR in the original setup tree.
- **Key Vault / Workload Identity**, if any workload will need secrets — also already called out as a later step in `minimul_aks_000.md`'s original tree.
- **`output` blocks** — ACR login server, cluster name, kube_config — so later Terraform runs / CI can consume them without hardcoding.
