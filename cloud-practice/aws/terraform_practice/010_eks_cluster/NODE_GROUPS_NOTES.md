# AKS system node pool vs EKS node groups

Written from general knowledge; verify details against current AWS/Azure docs.

## Short answer

EKS has **no built-in "system node pool"** concept. You can recreate it by convention, but nothing enforces it.

## Comparison

| | AKS | EKS |
|---|---|---|
| System pool | **Required**, a formal pool type (>= 1) | Does not exist as a type |
| System pods (CoreDNS, kube-proxy, metrics...) | Scheduled on the system pool (`CriticalAddonsOnly` taint) | Land on **any** node with capacity |
| App workloads | User node pools | Same node groups unless you separate them yourself |
| Control plane (API server, etcd) | Hidden, run by Azure | Hidden, run by AWS |

The system pool in AKS is **not** the control plane. It is your own VMs that host system pods. In both services the real control plane is invisible to you.

In this lab (`main.tf` files here), CoreDNS and kube-proxy run on the single `default` node group together with your apps.

## Making an "EKS system node group" (convention)

1. A small dedicated managed node group (e.g. 2 x `t3.medium`) with a taint and label:
   ```hcl
   resource "aws_eks_node_group" "system" {
     # ... same cluster/role/subnets as the default group ...
     labels = { role = "system" }
     taint {
       key    = "CriticalAddonsOnly"
       value  = "true"
       effect = "NO_SCHEDULE"
     }
   }
   ```
2. System add-ons/controllers tolerate that taint (CoreDNS does; add tolerations for others).
3. Separate node group(s) or Karpenter nodes for your applications.

Why: a noisy app can't starve DNS or controllers, and you can size/patch/upgrade system nodes separately.

## Related options

- **Karpenter**: common autoscaler; usually runs on a small managed node group or Fargate so it isn't scaling its own host.
- **Fargate profiles**: serverless pods, no node to manage for them; CoreDNS can run there.
- **EKS Auto Mode**: AWS manages nodes and core add-ons (closest to a fully managed data plane); adds a per-instance management fee on top of EC2.

## For this lab

One node group is fine. Possible follow-up lesson: add a second, tainted `system` node group and a normal `apps` group, then watch where CoreDNS and your deployment land (`kubectl get pods -A -o wide`).

## Terminology: node group vs node pool

Same idea, different name per cloud: a set of identical worker VMs backed by an autoscaling mechanism.

| Cloud | Term | Terraform resource | Backed by |
|---|---|---|---|
| AWS EKS | **node group** ("managed node group") | `aws_eks_node_group` | Auto Scaling Group |
| Azure AKS | **node pool** (system / user) | `azurerm_kubernetes_cluster_node_pool` (default pool is inside `azurerm_kubernetes_cluster`) | Virtual Machine Scale Set |
| Google GKE | **node pool** | `google_container_node_pool` | Managed instance group |

Use the cloud's own term when searching docs or writing Terraform: "node group" for EKS, "node pool" for AKS and GKE.

## Can a cluster exist without any nodes?

| | AKS | EKS |
|---|---|---|
| Create cluster with no node pool | **No.** A cluster needs at least one (system) node pool at creation | **Yes.** The control plane is created on its own |
| In Terraform | `default_node_pool { ... }` block is **required inside** `azurerm_kubernetes_cluster` | `aws_eks_cluster` has no node settings; nodes are a **separate** resource (`aws_eks_node_group`) |
| Remove all nodes later | System pool must keep >= 1 node (user pools can scale to 0). To stop paying for compute, **stop the cluster** | Delete or scale the node group to 0; the control plane stays |
| What you get with zero nodes | n/a | `kubectl` works (API server is up) but pods stay `Pending`; CoreDNS can't run |
| What's billed with zero nodes | n/a (compute can be stopped; control plane tier depends on Free/Standard) | **Control plane still bills ~$0.10/hr** |

Why the difference: in AKS the system pool is part of the cluster definition (it hosts system pods as a required component). In EKS the control plane is a standalone service and worker capacity is something you attach afterwards.

In this lab that split is visible in the code:

- `03_cluster.tf` -> `aws_eks_cluster` (control plane only, "STEP 3")
- `04_nodes.tf` -> `aws_eks_node_group` (workers, "STEP 4"), created after the cluster

Try it: `terraform apply -target=aws_eks_cluster.this`, then `kubectl get nodes` returns "No resources found". Apply the rest and nodes appear. (Pricing and AKS limits written from memory; verify in current docs.)

Ways EKS can have no EC2 nodes you manage: **Fargate profiles** (serverless pods) or **EKS Auto Mode** (AWS-managed nodes).
