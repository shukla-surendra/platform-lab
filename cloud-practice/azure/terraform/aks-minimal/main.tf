terraform {
  required_providers {
    azurerm = { source = "hashicorp/azurerm" }
    random  = { source = "hashicorp/random" }
  }
}

provider "azurerm" {
  features {}
}

# 1. Resource Group
resource "azurerm_resource_group" "aks" {
  name     = "rg-aks-minimal-demo"
  location = "Central India"
}

resource "random_string" "suffix" {
  length  = 6
  special = false
  upper   = false
}

# 2. The cluster. Two node pools, one node each -- the real production
# split, not a toy: a "system" pool that ONLY runs AKS's own critical
# add-ons (kube-proxy, CoreDNS, CNI, CSI drivers, etc. -- see
# node-anatomy.md), and a separate "user" pool where actual workloads are
# meant to land. Free control-plane tier, smallest AKS-supported VM size,
# no other add-ons (no monitoring agent, no ingress controller, no
# autoscaler) and no workload deployed onto it -- just the two-pool
# cluster itself, to explore directly.
resource "azurerm_kubernetes_cluster" "demo" {
  name                = "aks-min-${random_string.suffix.result}"
  location            = azurerm_resource_group.aks.location
  resource_group_name = azurerm_resource_group.aks.name
  dns_prefix          = "aksmin${random_string.suffix.result}"
  sku_tier            = "Free"

  # The "system" pool -- every AKS cluster's first node pool, defined
  # inline on the cluster resource itself rather than as a separate
  # azurerm_kubernetes_cluster_node_pool (that's a hard requirement: the
  # default_node_pool can never be removed/recreated without recreating
  # the whole cluster, which is exactly why a second, disposable "user"
  # pool -- added below as its own resource -- is where real workloads
  # belong instead).
  default_node_pool {
    name       = "system"
    node_count = 1
    # Standard_B2s (the size named in every generic AKS example) is not
    # allowed for this subscription/region -- confirmed directly building
    # the sibling aks/ module: Azure's 400 response lists the actual
    # allowlist, and Standard_B2s_v2 (same burstable 2 vCPU/4GB class,
    # newer generation) is on it.
    vm_size = "Standard_B2s_v2"

    # The actual production pattern this pool exists to demonstrate:
    # taints this pool with CriticalAddonsOnly=true:NoSchedule, so only
    # pods that explicitly tolerate it (AKS's own system add-ons already
    # do) can be scheduled here. Every other workload -- anything you'd
    # deploy yourself -- gets refused by the scheduler on this pool and
    # has to land on the "user" pool below instead. Without this, the
    # system pool is just a regular pool your own pods could crowd,
    # potentially starving the components the cluster itself depends on.
    only_critical_addons_enabled = true

    # Required by the provider specifically for THIS change: applying a
    # new taint to an existing node pool isn't a live relabel -- Azure
    # actually rotates the pool's nodes (spins up new ones with the new
    # taint, drains/removes the old), and the provider needs a temporary
    # pool name to stage that migration without downtime. Hit the error
    # this fixes directly: "temporary_name_for_rotation must be specified
    # when updating ... only_critical_addons_enabled".
    temporary_name_for_rotation = "systemtemp"
  }

  identity {
    type = "SystemAssigned"
  }

  # Required by this azurerm provider version even when unused -- "Manual"
  # means node pools are exactly what's declared above, not AKS's newer
  # Karpenter-based auto-provisioning mode ("Auto").
  node_provisioning_profile {
    mode = "Manual"
  }
}

# 3. The "user" pool -- a genuinely separate resource, not part of the
# cluster resource above, and (unlike default_node_pool) can be added,
# resized, or removed independently without touching the cluster or its
# system pool at all. mode = "User" is the counterpart to the system
# pool's taint: User-mode pools are exactly where the scheduler is
# expected to place ordinary workloads.
resource "azurerm_kubernetes_cluster_node_pool" "user" {
  name                  = "user"
  kubernetes_cluster_id = azurerm_kubernetes_cluster.demo.id
  vm_size               = "Standard_B2s_v2"
  node_count            = 1
  mode                  = "User"
}

output "resource_group_name" {
  value = azurerm_resource_group.aks.name
}

output "cluster_name" {
  value = azurerm_kubernetes_cluster.demo.name
}

output "node_resource_group" {
  description = "AKS auto-creates a SECOND resource group for the actual node VMs/disks/NICs -- this is its name."
  value       = azurerm_kubernetes_cluster.demo.node_resource_group
}

output "kube_config" {
  value     = azurerm_kubernetes_cluster.demo.kube_config_raw
  sensitive = true
}
