# Terraform: AKS, Minimal 2-Pool (Exploration Only)

RG + an AKS cluster with **two node pools, one node each**: a tainted
`system` pool that only AKS's own critical add-ons can schedule onto, and
an untainted `user` pool where everything else — including anything you
deploy yourself — actually lands. No workload deployed by this module (no
test pod, no nginx, nothing), no monitoring add-on, no ingress
controller, no autoscaler — the bare two-pool cluster itself, for
exploring the mechanics directly. If you want a version that also proves
the cluster runs real workloads, see the sibling [`../aks/`](../aks/README.md)
module (single pool, single node, deploys and tears down a test `nginx`
deployment as part of verification).

> ⚠️ **This creates billable, continuously-running resources** — 2 real
> VM-backed nodes, billed per hour for as long as the cluster exists (the
> control plane itself is free on the "Free" `sku_tier`). Nothing here
> scales to zero. Run `terraform destroy` when done exploring.

## Usage

```bash
cd cloud-practice/azure/terraform/aks-minimal
terraform init
terraform apply   # ~5 minutes -- a real control plane, not instant
```

## Connect and look around

```bash
az aks get-credentials --resource-group "$(terraform output -raw resource_group_name)" \
  --name "$(terraform output -raw cluster_name)" --overwrite-existing

kubectl get nodes -o wide -L kubernetes.azure.com/agentpool   # 2 nodes, Ready, one per pool
kubectl get pods -A            # only kube-system pods (CNI, CoreDNS, csi drivers, metrics-server) -- nothing else
kubectl describe node <name>   # capacity, allocatable resources, conditions
kubectl top nodes              # needs metrics-server, already running -- live CPU/memory
```

## Two node pools: `system` (tainted) vs. `user`

```bash
az aks nodepool list --resource-group "$(terraform output -raw resource_group_name)" \
  --cluster-name "$(terraform output -raw cluster_name)" \
  --query "[].{name:name, count:count, mode:mode, taints:nodeTaints}" -o table
```

```
Name    Count    Mode
------  -------  ------
system  1        System
user    1        User
```

The `system` pool carries `only_critical_addons_enabled = true` in
`main.tf`, which taints its node `CriticalAddonsOnly=true:NoSchedule` —
confirmed live:

```bash
kubectl get nodes -o custom-columns=NAME:.metadata.name,TAINTS:.spec.taints
```
```
aks-system-19418211-vmss000000   [map[effect:NoSchedule key:CriticalAddonsOnly value:true]]
aks-user-30842888-vmss000000     <none>
```

**Proved it holds, not just declared it**: deployed a plain
`nginx:alpine` test deployment with no toleration at all —

```bash
kubectl create deployment taint-test --image=nginx:alpine
kubectl get pods -o wide -l app=taint-test
```

— and it landed on `aks-user-...`, never even considered for
`aks-system-...`. Then checked where every *existing* system component
actually runs (`kubectl get pods -A -o wide`):

| Kind | Where it runs | Why |
|---|---|---|
| DaemonSets (`kube-proxy`, `azure-cns`, `csi-azuredisk-node`, `csi-azurefile-node`, `azure-ip-masq-agent`, `cloud-node-manager`) | **Both** nodes, one each | They tolerate every taint unconditionally — every node needs its own networking/storage agent regardless of which workloads are allowed to schedule there |
| Deployments (`coredns` ×2, `coredns-autoscaler`, `konnectivity-agent` ×2, `konnectivity-agent-autoscaler`, `metrics-server` ×2) | **Only** the `system` node | AKS's own control-plane components are pre-configured with a toleration for `CriticalAddonsOnly` specifically — the exact taint/toleration pair that makes this split work at all |

That's the real mechanism, not a paraphrase of it: the taint doesn't
single out "user workloads" by name — it excludes anything *without* a
matching toleration, and AKS made sure its own add-ons carry one while
your own deployments (unless you add one yourself) don't.

(Clean up the test deployment when done: `kubectl delete deployment taint-test`.)

## Getting a shell on a node VM (no SSH)

`az aks show ... --query linuxProfile` on this cluster returns `null` —
this module never sets a `linux_profile` block in `main.tf`, so **no SSH
key was ever provisioned**, and the node VMs have no public IP either
(the one public IP that does show up in the node resource group belongs
to the cluster's outbound load balancer, not any individual node's NIC —
there's no inbound path to port 22 regardless). Real SSH would need both
a key added to the cluster *and* network-level access into the AKS VNet
(Azure Bastion, a peered jumpbox, or a VPN) — meaningfully more setup
than this "explore a bare cluster" module is meant to require.

**This is deliberate, not just laziness.** Production AKS and EKS have
both largely moved *away* from bastion+SSH as the routine node-access
pattern, toward exactly the two mechanisms below: AKS's `kubectl debug
node` and EKS's equivalent (SSM Session Manager) both give a real root
shell on the node with no persistent key to distribute/rotate/leak, no
open port 22 anywhere, and access controlled by the same RBAC/IAM
identity you already have — instead of a separate credential and a
bastion host that's itself an always-on cost line and attack surface.
Azure Bastion + SSH is still real and Microsoft-documented, but it's more
the pattern for plain VM fleets than for Kubernetes-managed nodes; it was
considered and deliberately skipped here for exactly that reason (and its
real recurring cost, ~$0.19/hr / ~$140/month left running, on top of the
cluster itself).

Two things that give you an actual shell on the node right now, with
zero extra setup, because neither depends on the node having a public IP
or an SSH key at all — exact commands for this cluster, verified live
output, and the cleanup step people forget, in
**[`debugging.md`](debugging.md)**. Once you're in, see
**[`node-anatomy.md`](node-anatomy.md)** for what's actually running
there — every pod, systemd service, and config file present on a bare
node with nothing deployed, explained.

## Things to try, since this is meant to be poked at

- `kubectl get nodes -o wide -L kubernetes.azure.com/agentpool` — two
  distinct node names, each labeled with which pool it belongs to;
  confirms these are two independent VM Scale Sets, not one pool split
  logically.
- `kubectl describe node <name>` on both nodes — compare `Allocatable` vs
  `Capacity` (some capacity is always reserved for the OS/kubelet itself,
  never schedulable).
- Scale the user pool up (`azurerm_kubernetes_cluster_node_pool.user`'s
  `node_count` in `main.tf` → 2, `terraform apply`) and deploy a
  2-replica Deployment — watch whether the scheduler spreads the
  replicas across both user nodes or stacks them on one (no
  anti-affinity rule is set here, so it's not guaranteed either way — a
  good prompt to go learn `podAntiAffinity`). The system pool's
  `temporary_name_for_rotation` line only matters if you change
  `only_critical_addons_enabled` again later — a plain user-pool resize
  doesn't need it.
- `kubectl cordon <user-node>` then re-deploy — watch the scheduler have
  nowhere ordinary to put it (the system node still refuses it via the
  taint) until you `kubectl uncordon`.
- `az aks nodepool list --cluster-name "$(terraform output -raw cluster_name)" --resource-group "$(terraform output -raw resource_group_name)"` —
  see the node pools as Azure's control plane understands them, alongside
  `kubectl get nodes` as Kubernetes' own view of the same 2 machines.

## Two resource groups, not one

Same as `../aks/`: `terraform output resource_group_name` is what this
module's state manages. AKS separately auto-creates
`terraform output node_resource_group` (`MC_<rg>_<cluster>_<region>`) —
that's where both node VMs (one per pool), their disks, and NICs
actually live. Expect to see it in `az group list` after `apply`; it's
destroyed automatically along with the cluster.

## What's deliberately not here

No workload of any kind beyond the taint-proving test above, which gets
cleaned up (that's the whole point — explore an otherwise-empty
cluster's mechanics first). No autoscaling on either pool, no Azure
AD/RBAC integration beyond AKS's own defaults, no private cluster/custom
VNet, no Azure Monitor/Container Insights. See
[`../aks/README.md`](../aks/README.md) for the same minimal-cluster
pattern (single pool) with one workload actually deployed and verified,
if you want that comparison next.

## Teardown

```bash
terraform destroy   # a few minutes -- deleting a real control plane isn't instant either
```
