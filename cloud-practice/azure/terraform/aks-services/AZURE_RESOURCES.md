# What `terraform apply` Actually Creates in Azure

`main.tf` declares **3 Terraform resources**: `azurerm_resource_group`,
`random_string` (local only, nothing in Azure) and
`azurerm_kubernetes_cluster`. Azure ends up with **2 resource groups and 7
resources** at idle, and more once you create LoadBalancer Services. AKS
creates everything beyond the cluster object itself. Terraform never sees it.

All names below come from a real `terraform apply` (cluster
`aks-svc-lf508l`, Central India). The numeric and hash suffixes are generated
per cluster, so yours will be different.

```
rg-aks-services-demo                       <- YOUR resource group (Terraform manages it)
└── aks-svc-lf508l                         Managed cluster (control plane, run by Azure)
         │ managedBy
         ▼
MC_rg-aks-services-demo_aks-svc-lf508l_centralindia   <- NODE resource group (AKS manages it)
├── aks-vnet-25611862                      Virtual network
│   └── aks-subnet  ── aks-agentpool-25611862-nsg      NSG on the node subnet
├── aks-system-31524237-vmss               VM scale set = the node pool (1 VM)
├── aks-svc-lf508l-agentpool               Managed identity for kubelet
├── kubernetes                             Standard Load Balancer
│   └── 5f799ddc-...                       Public IP (outbound SNAT)
│
│   (only while Services exist)
├── kubernetes-a<svc-uid>                  Public IP per public LoadBalancer Service
└── kubernetes-internal                    Internal LB (only for internal Services)
```

## Resource group 1: `rg-aks-services-demo` (yours)

| Resource | Type | Created by |
|---|---|---|
| `rg-aks-services-demo` | Resource group | Terraform (`azurerm_resource_group.aks`) |
| `aks-svc-lf508l` | `Microsoft.ContainerService/managedClusters` | Terraform (`azurerm_kubernetes_cluster.demo`) |
| `akssvclf508lacr` | `Microsoft.ContainerRegistry/registries` (Basic) | Terraform (`azurerm_container_registry.acr`), added for [`DEPLOY_GRIDWORK.md`](DEPLOY_GRIDWORK.md) |

### The managed cluster: `aks-svc-lf508l`

This is the only thing in your own RG. It is the **control plane**
(API server, etcd, scheduler, controller-manager, cloud-controller-manager).
Azure runs it on its own infrastructure. There's no VM for it in your
subscription and, on the `Free` tier, no charge for it.

| Setting | Value | Where it comes from |
|---|---|---|
| Kubernetes version | 1.35 | AKS default (not pinned in `main.tf`) |
| SKU tier | Free (no uptime SLA) | `sku_tier = "Free"` |
| API server FQDN | `akssvclf508l-<hash>.hcp.centralindia.azmk8s.io` | `dns_prefix` + generated hash; public endpoint |
| Cluster identity | System-assigned managed identity | `identity { type = "SystemAssigned" }` |
| Network plugin | Azure CNI **Overlay** | `network_plugin = "azure"`, `network_plugin_mode = "overlay"` |
| Pod CIDR | `10.244.0.0/16` | Overlay default. Pods do **not** use VNet IPs |
| Service CIDR | `10.0.0.0/16` | Default. ClusterIPs such as `10.0.205.251` come from here |
| DNS service IP | `10.0.0.10` | Default (CoreDNS ClusterIP) |
| Outbound type | `loadBalancer` | `outbound_type` → requires the `kubernetes` LB below |
| LB SKU | Standard | `load_balancer_sku` |
| OIDC issuer | Enabled | AKS default on this version |
| Node provisioning | Manual | `node_provisioning_profile { mode = "Manual" }` |

## Resource group 2: `MC_rg-aks-services-demo_aks-svc-lf508l_centralindia` (AKS's)

The **node resource group**. AKS creates it with the cluster and deletes it
with the cluster. Its `managedBy` property points at the cluster, so treat it
as read-only: if you change things in it by hand, AKS can overwrite them or
break. Name pattern: `MC_<rg>_<cluster>_<region>`
(override with `node_resource_group` in Terraform).

### Always present (idle cluster, no Services)

| # | Name | Type | What it does |
|---|---|---|---|
| 1 | `aks-vnet-25611862` | Virtual network | `10.224.0.0/12`. Created because no existing subnet was supplied (`vnet_subnet_id`). |
| 2 | `aks-agentpool-25611862-nsg` | Network security group | Attached to `aks-subnet`. |
| 3 | `aks-system-31524237-vmss` | VM scale set | The `system` node pool. |
| 4 | `aks-svc-lf508l-agentpool` | User-assigned managed identity | The **kubelet identity** that nodes use to pull images, etc. |
| 5 | `kubernetes` | Load balancer (Standard) | Outbound internet access for nodes. Later also hosts public Services. |
| 6 | `5f799ddc-3546-467e-aeef-4272a769ffc9` | Public IP (Standard, static, zones 1/2/3) | The LB's managed **outbound** IP. Tagged `aks-managed-type=aks-slb-managed-outbound-ip`. |

#### 1. Virtual network `aks-vnet-25611862`

| Subnet | CIDR | Used? |
|---|---|---|
| `aks-subnet` | `10.224.0.0/16` | **Yes**: node NICs get IPs here (the node is `10.224.0.4`). Internal LB IPs also come from here (e.g. `10.224.0.5`). |
| `aks-appgateway` | `10.238.0.0/24` | No. Reserved for the App Gateway ingress (AGIC) add-on. |
| `aks-virtualkubelet` | `10.239.0.0/16` | No. Reserved for virtual nodes (ACI). |

Because of Overlay, **pods don't take IPs from this VNet**. They use
`10.244.0.0/16`, and traffic leaving a node is NAT'ed to the node IP.

#### 2. NSG `aks-agentpool-25611862-nsg`

Starts with **0 custom rules**, just Azure's six defaults
(`AllowVnetInBound`, `AllowAzureLoadBalancerInBound`, `DenyAllInBound`,
`AllowVnetOutBound`, `AllowInternetOutBound`, `DenyAllOutBound`).
With default settings, when you create a public LoadBalancer Service, the
cloud-controller-manager **adds an allow rule** here for that Service's
IP:port (named `k8s-azure-lb_allow_IPv4_<hash>`, verified). Otherwise `DenyAllInBound` would drop the traffic. When you delete
the Service, the rule is removed.

#### 3. VM scale set `aks-system-31524237-vmss`

| Property | Value |
|---|---|
| SKU | `Standard_B2s_v2` (2 vCPU / 8 GiB), capacity 1 |
| OS image | `AKSUbuntu-2404gen2containerd-202609.15.0` (Ubuntu 24.04, containerd) |
| OS disk | 128 GB managed, `Premium_LRS`, ReadOnly cache. It belongs to the VMSS instance, so it isn't a separate top-level resource |
| Max pods per node | 250 (Overlay default) |
| Zones | none |
| Extensions | `vmssCSE` (bootstraps the node into the cluster), `AKSLinuxExtension`, `...-AKSLinuxBilling` |

Scale the pool with `node_count` in Terraform, not on the VMSS directly.

#### 4. Kubelet identity `aks-svc-lf508l-agentpool`

It's assigned to the VMSS and is what the node itself authenticates as.
It had **no role assignments** until the ACR was added. Now it has `AcrPull`
on the registry, which is how nodes pull the gridwork images.

#### 5. Load balancer `kubernetes`

| Part | Idle state |
|---|---|
| Frontend IP configs | 1 (the outbound public IP) |
| Backend pools | `kubernetes` (for Service traffic) and `aksOutboundBackendPool` (for SNAT). Both hold the VMSS NICs |
| Outbound rule | `aksOutboundRule`: protocol All, 30 min idle timeout, ports auto-allocated |
| LB rules / probes | 0 / 0 |

This is the shared load balancer from the experiment in `README.md`.

### Only while LoadBalancer Services exist

The cloud-controller-manager creates these at runtime (not Terraform or AKS
provisioning), and deletes them again with the Service.

| Trigger | What gets created | Seen in the experiment |
|---|---|---|
| Each **public** `type: LoadBalancer` Service | 1 public IP `kubernetes-a<service-uid>` (tag `k8s-azure-service=<ns>/<name>`), plus 1 frontend, 1 LB rule and 1 health probe per port on the **existing** `kubernetes` LB, plus an NSG allow rule | `web-lb-a` → `4.213.207.68`, `web-lb-b` → `4.187.194.33`. LB went to 3 frontends / 2 rules |
| First **internal** Service (`azure-load-balancer-internal: "true"`) | A new LB `kubernetes-internal` with a private frontend from `aks-subnet` | `web-lb-internal` → `10.224.0.5` |
| A PVC using the `default` storage class | An Azure **Managed Disk** `pvc-<uid>` (StandardSSD_LRS), created by the Azure Disk CSI driver | gridwork Postgres: 1 GiB disk |
| Last internal Service deleted | `kubernetes-internal` is deleted entirely | ✔ |
| All public Services deleted | Their IPs, frontends, rules and probes are removed. `kubernetes` stays (outbound needs it) | Back to 1 frontend / 0 rules |

## Identities and permissions

| Identity | Kind | Role assignment |
|---|---|---|
| Cluster identity (principal `57f5265a-...`) | System-assigned, on the cluster | **Contributor** on the node resource group. This is how the cloud-controller-manager can create public IPs, edit the LB and NSG, and scale the VMSS |
| `aks-svc-lf508l-agentpool` | User-assigned, on the nodes | **AcrPull** on the ACR (Terraform `azurerm_role_assignment.kubelet_acr_pull`). None before the ACR was added |

## Created as part of the cluster but *not* Azure resources

These run inside Kubernetes (`kubectl get pods -n kube-system`), not as Azure
objects: CoreDNS, kube-proxy, the Azure CNI / overlay components,
the Azure Disk/File CSI drivers, metrics-server and konnectivity-agent
(the tunnel back to the managed control plane).

## What costs money

| Item | Billing |
|---|---|
| Control plane | Free (`Free` tier) |
| 1 × `Standard_B2s_v2` VM + 128 GB Premium SSD | Hourly, while the cluster exists |
| Outbound public IP (Standard) | Hourly, always |
| Each LoadBalancer Service public IP | Hourly, while the Service exists |
| Standard LB | Per rule-hour + data processed (the first 5 rules are billed as a flat amount) |
| ACR Basic | ~US$0.17/day + storage for images |
| Managed Disk for each PVC (gridwork Postgres: 1 GiB StandardSSD) | Monthly per disk, while the PVC exists |
| VNet, NSG, managed identity | Free |

## Lifecycle

- `terraform destroy` deletes the cluster. **AKS then deletes the whole
  `MC_...` group**, including any Service IPs still there. Deleting the
  Services first (`kubectl delete -f manifests/`) is still the cleaner order.
- Never delete the `MC_...` group or its resources by hand while the cluster
  exists. The cluster will break, and Terraform won't detect it.

## Reproduce this inventory

```bash
RG=$(terraform output -raw resource_group_name)
NRG=$(terraform output -raw node_resource_group)
az resource list -g $RG  --query "[].[name,type]" -o tsv
az resource list -g $NRG --query "[].[name,type]" -o tsv
az network lb list -g $NRG --query "[].{name:name, frontends:length(frontendIPConfigurations), rules:length(loadBalancingRules||\`[]\`)}" -o table
az network public-ip list -g $NRG --query "[].{name:name, ip:ipAddress, svc:tags.\"k8s-azure-service\"}" -o table
az role assignment list --assignee $(az aks show -g $RG -n $(terraform output -raw cluster_name) --query identity.principalId -o tsv) --all -o table
```
