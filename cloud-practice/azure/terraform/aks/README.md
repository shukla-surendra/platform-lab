# Terraform: Azure Kubernetes Service (AKS, minimal single-node)

RG + a single-node AKS cluster — the cheapest real, working AKS setup:
Free control-plane tier, one `Standard_B2s_v2` node, system-assigned
identity. Verified live: node `Ready`, all `kube-system` pods `Running`,
and a real `nginx` deployment scheduled and ran successfully.

> ⚠️ **This creates billable, continuously-running resources** — unlike
> the storage-only modules in this repo, AKS worker nodes are real VMs
> billed per hour for as long as the cluster exists (the control plane
> itself is free on the "Free" `sku_tier`). Nothing here scales to zero
> on its own. Run `terraform destroy` when done exploring.

## Usage

```bash
cd cloud-practice/azure/terraform/aks
terraform init
terraform apply   # takes ~5 minutes -- AKS provisions a real control plane, not instant
```

## Connect and verify

```bash
az aks get-credentials --resource-group "$(terraform output -raw resource_group_name)" \
  --name "$(terraform output -raw cluster_name)" --overwrite-existing

kubectl get nodes -o wide      # 1 node, Ready
kubectl get pods -A            # kube-system pods (CNI, CoreDNS, csi drivers, metrics-server) all Running

# prove it actually schedules and runs workloads, not just healthy plumbing
kubectl create deployment demo-nginx --image=nginx:alpine --replicas=2
kubectl get pods -l app=demo-nginx -o wide   # both Running after a few seconds
kubectl delete deployment demo-nginx
```

## Why VM size matters here, and why it's `Standard_B2s_v2`

AKS node VM sizes are constrained by what your specific Azure
subscription is allowed to provision in a given region — hit this
directly building this module: `Standard_B2s` (the size used in every
other burstable-VM example you'll find) came back `400 Bad Request: The
VM size of Standard_B2s is not allowed in your subscription in location
'centralindia'`, with the actual allowlist for this subscription/region in
the error body. `Standard_B2s_v2` was on that list and is the newer
generation of the same burstable-2-vCPU/4GB-RAM size class anyway. If you
hit the same error in a different subscription/region, the 400 response
itself lists exactly what's allowed — check `az vm list-skus --location
<region> --resource-type virtualMachines -o table` too.

## Two resource groups, not one

`terraform output resource_group_name` (`rg-aks-demo`) is what this
module's state manages directly — it holds the `azurerm_kubernetes_cluster`
resource itself (the control plane's Azure-facing identity). AKS also
auto-creates a **second** resource group Terraform never touches directly:
`terraform output node_resource_group` (`MC_rg-aks-demo_<cluster>_<region>`)
— this is where the actual node VMs, disks, NICs, and any
`LoadBalancer`-type Kubernetes Services' underlying Azure Load Balancer
land. Worth knowing before an unexplained resource group shows up in
`az group list` after your first `apply`.

## What's deliberately not here

Single node, no autoscaling (`auto_scaling_enabled`/`min_count`/`max_count`
on `default_node_pool` — trivial to add), no separate user/system node
pool split (a real cluster typically taints the system pool
`CriticalAddonsOnly` and runs workloads on a separate user pool), no
Azure AD/RBAC integration beyond AKS's own defaults, no private cluster
/ custom VNet (uses AKS's default networking), no Azure Monitor /
Container Insights (`oms_agent` block).

## Teardown

```bash
terraform destroy   # also takes a few minutes -- deleting a real control plane isn't instant either
```
