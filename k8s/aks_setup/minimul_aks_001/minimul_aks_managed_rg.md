# What's Inside `MC_rg-aks-dev_aks-dev_centralindia`

When you create an AKS cluster, Azure doesn't put all its underlying infrastructure into the resource group you created yourself (`rg-aks-dev`). Instead, it automatically creates a *second* resource group, always following the same naming pattern: `MC_<your-resource-group>_<cluster-name>_<region>`. This is where the actual "engine" of your cluster lives — the VMs, load balancer, and networking that make your nodes real.

**Important:** none of these resources are declared anywhere in `main.tf`. Terraform only knows about (and manages) the `azurerm_kubernetes_cluster` resource itself. Everything inside `MC_...` is AKS's own responsibility — it creates all of it the moment the cluster is created, and it **destroys all of it automatically** when the cluster is deleted, even though Terraform never explicitly asked for any of these individual resources. You should never manually edit anything inside this resource group — AKS treats it as its own territory, and manual changes can get silently reverted or break the cluster.

## What's in there right now

### `aks-system-89223860-vmss` and `aks-userpool-18252216-vmss` — the actual worker machines
**Type:** Virtual Machine Scale Set (VMSS)

This is the literal computer(s) that run your workloads. Each Terraform node pool (the `default_node_pool` block for system, the separate `azurerm_kubernetes_cluster_node_pool.user` block for user) corresponds to exactly one VMSS here — not a single VM, but a "scale set": a template Azure uses to run a group of identical VMs, and to grow or shrink that group. Right now both are sized `Standard_D2s_v5` with a capacity of 1 — one VM each — matching your Terraform `vm_size`/`node_count` settings after the resize.

### `kubernetes` — the Load Balancer
**Type:** Standard Load Balancer

A real Kubernetes cluster needs something to route traffic to whichever node has room, and to give Services a stable entry point. This load balancer is what backs the built-in `kubernetes` Service (the internal API-server entry point from the earlier `kubectl get all` output) and any Service you create yourself with `type: LoadBalancer`.

It currently has 1 outbound rule — that's what gives your nodes/pods a way to reach the internet at all (pulling images, calling external APIs, etc.). Without something handling outbound connectivity like this, your nodes would have no general internet access.

### A Public IP address
**Type:** Public IP, Standard SKU, Static allocation

This is the actual internet-facing address the Load Balancer above uses for that outbound connectivity. "Static" means it won't change for as long as the cluster exists. You didn't ask for this anywhere in `main.tf` — it exists because AKS defaults to creating and managing outbound connectivity for you when you don't specify anything about it yourself.

### `aks-agentpool-10099729-nsg` — Network Security Group
**Type:** NSG

Think of this as a firewall attached to your nodes' network interfaces. Right now it has zero custom rules — meaning it's relying entirely on Azure's invisible built-in defaults (allow traffic within the VNet, allow the load balancer to reach nodes, deny everything else from the outside). AKS always creates one of these as a placeholder, ready for you — or an Ingress controller, later — to add specific rules to if you ever need tighter control.

### `aks-dev-agentpool` — Managed Identity
**Type:** User Assigned Managed Identity

This is the "worker badge" your nodes use to authenticate to other Azure services. This is the *exact* identity referenced by name earlier as `kubelet_identity` in `azurerm_role_assignment.aks_acr_pull` — it's not a person, and it's not the same as the cluster's own `SystemAssigned` identity (that one manages the cluster's own Azure resources, like creating this whole resource group). This one specifically represents "the kubelet software running on your nodes," and it's what actually holds the `AcrPull` permission you granted it.

## Why this matters

- **You never destroy this resource group directly.** Deleting the cluster (`terraform destroy` on `azurerm_kubernetes_cluster.aks`, or deleting it in the Portal) is what tears this whole resource group down. Trying to delete things inside `MC_...` by hand while the cluster still exists will either get them silently recreated, or leave the cluster in a broken state.
- **This is also where most of your actual compute cost lives.** The VMSS instances here are the VMs you're paying for. The resource group you created yourself (`rg-aks-dev`) mostly just holds "control surface" objects — the cluster definition, the VNet, the ACR — not the running machines themselves.
- If you ever see an Azure resource you don't remember creating and it's AKS-related, this resource group is almost always where it lives.
