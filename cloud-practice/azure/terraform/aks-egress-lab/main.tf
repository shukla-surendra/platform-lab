# AKS cluster tuned for a short, cheap practice session on Services and egress.
#
# Cost choices (see README.md for the numbers and the cleanup checklist):
#   - Free control-plane tier (no hourly charge for the AKS control plane)
#   - 1 small node, no extra node pools
#   - NO container registry (the earlier aks-services lab had one; nothing here needs it)
#   - Outbound traffic goes through the cluster's own Standard load balancer, so there is no NAT gateway to pay for
terraform {
  required_version = ">= 1.5"
  required_providers {
    azurerm = { source = "hashicorp/azurerm" }
    random  = { source = "hashicorp/random" }
  }
}

provider "azurerm" {
  features {}
}

resource "random_string" "suffix" {
  length  = 5
  special = false
  upper   = false
}

locals {
  name = "${var.name_prefix}-${random_string.suffix.result}"
  tags = {
    purpose = "practice"
    ttl     = "destroy-after-session" # a reminder to a human; nothing enforces it
  }
}

resource "azurerm_resource_group" "aks" {
  name     = "rg-${local.name}"
  location = var.location
  tags     = local.tags
}

resource "azurerm_kubernetes_cluster" "lab" {
  name                = local.name
  location            = azurerm_resource_group.aks.location
  resource_group_name = azurerm_resource_group.aks.name
  dns_prefix          = replace(local.name, "-", "")
  sku_tier            = "Free"
  tags                = local.tags

  default_node_pool {
    name       = "system"
    node_count = var.node_count
    vm_size    = var.vm_size
    # NOT setting only_critical_addons_enabled: with a single node, your lab Pods must be allowed to run on it.

    upgrade_settings {
      max_surge = "10%"
    }
  }

  identity {
    type = "SystemAssigned"
  }

  network_profile {
    network_plugin      = "azure"
    network_plugin_mode = "overlay"                                   # Pod IPs come from an overlay range, not your VNet
    network_data_plane  = var.enable_network_policy ? "cilium" : null # Cilium enforces NetworkPolicy
    network_policy      = var.enable_network_policy ? "cilium" : null
    load_balancer_sku   = "standard"
    outbound_type       = "loadBalancer" # EGRESS path: Pods -> node -> the cluster's load balancer -> internet

    load_balancer_profile {
      managed_outbound_ip_count = var.outbound_ip_count # how many stable egress IPs
    }
  }

  node_provisioning_profile {
    mode = "Manual" # same as your earlier labs: you manage the node pool
  }
}
