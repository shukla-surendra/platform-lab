# ===========================================================================
# Azure Synapse Analytics: a cost-conscious learning workspace
# ===========================================================================
# What this builds:
#   Resource group
#   ├─ Storage account (ADLS Gen2)         the data lake
#   │    ├─ filesystem "synapse"           workspace default storage (Spark logs, notebooks output)
#   │    ├─ filesystem "raw"               sample CSVs land here (uploaded by scripts/)
#   │    └─ filesystem "curated"           CETAS / Spark write results here
#   └─ Synapse workspace                   FREE by itself
#        ├─ Built-in serverless SQL pool   always exists, pay per TB scanned (~$5/TB)
#        ├─ Spark pool (optional)          var.enable_spark_pool     default TRUE, auto-pauses
#        └─ Dedicated SQL pool (optional)  var.enable_dedicated_pool default FALSE, bills per hour
#
# COST SUMMARY (verify on the Azure pricing calculator, prices differ by region):
#   workspace + serverless SQL ..... ~0 for this data size (a few MB scanned)
#   storage ........................ cents per month
#   Spark pool ..................... only while a session is running (see README)
#   dedicated SQL pool ............. ~ $1.2-1.5/hour while NOT paused. Off by default.

terraform {
  required_version = ">= 1.5"

  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 5.0"
    }
    random = {
      source = "hashicorp/random"
    }
    http = {
      source = "hashicorp/http"
    }
  }
}

provider "azurerm" {
  features {}
}

# ---------------------------------------------------------------------------
# Inputs
# ---------------------------------------------------------------------------
variable "location" {
  type    = string
  default = "Central India"
}

variable "enable_spark_pool" {
  description = "Create a small Apache Spark pool (billed only while a session is active; auto-pauses)."
  type        = bool
  default     = true
}

variable "spark_version" {
  description = "Synapse Spark runtime. Check supported versions: Synapse Studio > Manage > Apache Spark pools."
  type        = string
  default     = "3.5"
}

variable "enable_dedicated_pool" {
  description = "Create a dedicated SQL pool (DW100c). BILLS PER HOUR until paused or destroyed."
  type        = bool
  default     = false
}

variable "sql_admin_password" {
  description = "Password for the workspace SQL admin (sqladminuser). Set via TF_VAR_sql_admin_password or terraform.tfvars."
  type        = string
  sensitive   = true
}

variable "extra_firewall_ip" {
  description = "Optional extra IP to allow. Your current public IP is detected automatically."
  type        = string
  default     = ""
}

# ---------------------------------------------------------------------------
# Context: who am I, what is my public IP
# ---------------------------------------------------------------------------
data "azurerm_client_config" "current" {}

data "http" "my_ip" {
  url = "https://api.ipify.org"
}

resource "random_string" "suffix" {
  length  = 6
  upper   = false
  special = false
}

locals {
  my_ip = chomp(data.http.my_ip.response_body)
}

# ---------------------------------------------------------------------------
# Resource group + data lake
# ---------------------------------------------------------------------------
resource "azurerm_resource_group" "this" {
  name     = "rg-synapse-demo"
  location = var.location
}

resource "azurerm_storage_account" "lake" {
  name                     = "stsyn${random_string.suffix.result}"
  resource_group_name      = azurerm_resource_group.this.name
  location                 = azurerm_resource_group.this.location
  account_tier             = "Standard"
  account_replication_type = "LRS" # cheapest
  account_kind             = "StorageV2"
  is_hns_enabled           = true # ADLS Gen2, required by Synapse
  min_tls_version          = "TLS1_2"
}

resource "azurerm_storage_data_lake_gen2_filesystem" "synapse" {
  name               = "synapse"
  storage_account_id = azurerm_storage_account.lake.id
}

resource "azurerm_storage_data_lake_gen2_filesystem" "raw" {
  name               = "raw"
  storage_account_id = azurerm_storage_account.lake.id
}

resource "azurerm_storage_data_lake_gen2_filesystem" "curated" {
  name               = "curated"
  storage_account_id = azurerm_storage_account.lake.id
}

# You need data-plane rights to upload files and for serverless SQL (your identity) to read them.
resource "azurerm_role_assignment" "me_blob_owner" {
  scope                = azurerm_storage_account.lake.id
  role_definition_name = "Storage Blob Data Owner"
  principal_id         = data.azurerm_client_config.current.object_id
}

# ---------------------------------------------------------------------------
# Synapse workspace
# ---------------------------------------------------------------------------
resource "azurerm_synapse_workspace" "this" {
  name                                 = "syn-demo-${random_string.suffix.result}"
  resource_group_name                  = azurerm_resource_group.this.name
  location                             = azurerm_resource_group.this.location
  storage_data_lake_gen2_filesystem_id = azurerm_storage_data_lake_gen2_filesystem.synapse.id

  sql_administrator_login          = "sqladminuser"
  sql_administrator_login_password = var.sql_admin_password

  identity {
    type = "SystemAssigned"
  }
}

# The workspace managed identity is what Spark/pipelines/serverless (with MI auth) use to read the lake.
resource "azurerm_role_assignment" "workspace_blob_contributor" {
  scope                = azurerm_storage_account.lake.id
  role_definition_name = "Storage Blob Data Contributor"
  principal_id         = azurerm_synapse_workspace.this.identity[0].principal_id
}

# Note: the identity that creates the workspace is automatically made Synapse Administrator
# (Synapse RBAC, separate from Azure RBAC), so no explicit role assignment is needed for you.

# Firewall: without a rule your browser/CLI cannot reach the workspace endpoints.
resource "azurerm_synapse_firewall_rule" "me" {
  name                 = "allow-my-ip"
  synapse_workspace_id = azurerm_synapse_workspace.this.id
  start_ip_address     = local.my_ip
  end_ip_address       = local.my_ip
}

resource "azurerm_synapse_firewall_rule" "extra" {
  count                = var.extra_firewall_ip == "" ? 0 : 1
  name                 = "allow-extra-ip"
  synapse_workspace_id = azurerm_synapse_workspace.this.id
  start_ip_address     = var.extra_firewall_ip
  end_ip_address       = var.extra_firewall_ip
}

# ---------------------------------------------------------------------------
# Optional: Spark pool (3 x Small nodes = 12 vCores; auto-pause after 10 idle minutes)
# ---------------------------------------------------------------------------
resource "azurerm_synapse_spark_pool" "small" {
  count                = var.enable_spark_pool ? 1 : 0
  name                 = "sparksmall"
  synapse_workspace_id = azurerm_synapse_workspace.this.id
  node_size_family     = "MemoryOptimized"
  node_size            = "Small" # 4 vCores, 32 GB
  spark_version        = var.spark_version
  cache_size           = 0

  node_count = 3 # fixed size: the minimum Synapse allows is 3 nodes

  auto_pause {
    delay_in_minutes = 5 # shortest practical; idle pool stops billing
  }
}

# ---------------------------------------------------------------------------
# Optional: Dedicated SQL pool (the expensive one)
# ---------------------------------------------------------------------------
resource "azurerm_synapse_sql_pool" "dw" {
  count                = var.enable_dedicated_pool ? 1 : 0
  name                 = "dw100"
  synapse_workspace_id = azurerm_synapse_workspace.this.id
  sku_name             = "DW100c" # smallest
  create_mode          = "Default"
  storage_account_type = "LRS"
}

# ---------------------------------------------------------------------------
# Outputs
# ---------------------------------------------------------------------------
output "resource_group" {
  value = azurerm_resource_group.this.name
}

output "workspace_name" {
  value = azurerm_synapse_workspace.this.name
}

output "storage_account" {
  value = azurerm_storage_account.lake.name
}

output "studio_url" {
  value = "https://web.azuresynapse.net?workspace=%2fsubscriptions%2f${data.azurerm_client_config.current.subscription_id}%2fresourceGroups%2f${azurerm_resource_group.this.name}%2fproviders%2fMicrosoft.Synapse%2fworkspaces%2f${azurerm_synapse_workspace.this.name}"
}

output "serverless_sql_endpoint" {
  value = azurerm_synapse_workspace.this.connectivity_endpoints["sqlOnDemand"]
}

output "my_ip_allowed" {
  value = local.my_ip
}
