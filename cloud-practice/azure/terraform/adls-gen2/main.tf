# ===========================================================================
# ADLS Gen2 (Azure Data Lake Storage Gen2): storage account + medallion layout
# ===========================================================================
# ADLS Gen2 is NOT a separate Azure service. It is a normal Storage Account with
# ONE setting turned on: the hierarchical namespace (is_hns_enabled = true).
# That gives real directories, atomic rename/move, and POSIX-style ACLs on top
# of Blob storage, which is what analytics engines (Spark, Synapse, Databricks,
# Delta Lake) need.
#
# What this project builds:
#   Resource group
#   └─ Storage account (HNS on)
#        ├─ filesystem "bronze"  (raw landing data)      /raw/sales, /raw/customers
#        ├─ filesystem "silver"  (cleaned data)          /sales, /customers
#        └─ filesystem "gold"    (curated / reporting)   /reports
#   + RBAC for you (Storage Blob Data Owner)
#   + optional reader (RBAC at one filesystem + ACL on one directory)
#   + a lifecycle policy (raw data cools after 30 days)
#   (a sample CSV is uploaded by scripts/demo.sh, not by Terraform)

terraform {
  required_version = ">= 1.5"

  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 5.0" # v5 changed several storage arguments; pin the major version
    }
    random = {
      source = "hashicorp/random"
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

variable "reader_object_id" {
  description = <<-EOT
    Optional: Entra ID object id of a user, group or service principal that should
    get READ-ONLY access to the gold layer only. Leave empty to skip.
    Find yours:  az ad signed-in-user show --query id -o tsv
  EOT
  type        = string
  default     = ""
}

# The medallion layers: one filesystem each
variable "filesystems" {
  type    = set(string)
  default = ["bronze", "silver", "gold"]
}

# Folder skeleton inside each filesystem (key = "<filesystem>/<path>")
variable "directories" {
  type = map(object({ filesystem = string, path = string }))
  default = {
    bronze_sales     = { filesystem = "bronze", path = "raw/sales" }
    bronze_customers = { filesystem = "bronze", path = "raw/customers" }
    silver_sales     = { filesystem = "silver", path = "sales" }
    silver_customers = { filesystem = "silver", path = "customers" }
    gold_reports     = { filesystem = "gold", path = "reports" }
  }
}

# Who is running Terraform / the az CLI: used for the RBAC assignment below
data "azurerm_client_config" "current" {}

# ---------------------------------------------------------------------------
# 1. Resource group
# ---------------------------------------------------------------------------
resource "azurerm_resource_group" "lake" {
  name     = "rg-adls-gen2-demo"
  location = var.location
}

# Storage account names: globally unique, 3-24 chars, lowercase letters and digits only
resource "random_string" "suffix" {
  length  = 6
  special = false
  upper   = false
}

# ---------------------------------------------------------------------------
# 2. The storage account with the hierarchical namespace
# ---------------------------------------------------------------------------
resource "azurerm_storage_account" "lake" {
  name                = "stadls${random_string.suffix.result}"
  resource_group_name = azurerm_resource_group.lake.name
  location            = azurerm_resource_group.lake.location

  account_kind             = "StorageV2"
  account_tier             = "Standard"
  account_replication_type = "LRS" # cheapest; use ZRS/GRS for real data

  # THE setting that makes this a data lake. Can only be chosen at creation:
  # you cannot switch an existing Blob account to HNS in Terraform without
  # a migration (and changing it later forces a new account).
  is_hns_enabled = true

  # Security baseline
  https_traffic_only_enabled      = true
  min_tls_version                 = "TLS1_2"
  allow_nested_items_to_be_public = false

  # LAB CHOICE: shared keys stay enabled because Terraform creates the
  # filesystems/directories through the data plane with the account key.
  # In production set this to false and use Entra ID (RBAC) only; then the
  # provider needs `storage_use_azuread = true` and your identity needs
  # Storage Blob Data Owner (plus time for the role to propagate).
  shared_access_key_enabled = true

  # Safety net against accidental deletes
  blob_properties {
    delete_retention_policy {
      days = 7
    }
    container_delete_retention_policy {
      days = 7
    }
  }
}

# ---------------------------------------------------------------------------
# 3. Filesystems (the ADLS Gen2 name for a container with real directories)
# ---------------------------------------------------------------------------
resource "azurerm_storage_data_lake_gen2_filesystem" "layer" {
  for_each = var.filesystems

  name               = each.key
  storage_account_id = azurerm_storage_account.lake.id
}

# ---------------------------------------------------------------------------
# 4. Directories (real directories because HNS is on)
# ---------------------------------------------------------------------------
resource "azurerm_storage_data_lake_gen2_path" "dir" {
  for_each = var.directories

  path               = each.value.path
  filesystem_name    = azurerm_storage_data_lake_gen2_filesystem.layer[each.value.filesystem].name
  storage_account_id = azurerm_storage_account.lake.id
  resource           = "directory"

  # ACLs (POSIX-style) are set on the SAME resource as the directory, because a
  # path can only be managed by one Terraform resource. Only gold_reports gets
  # ACL entries, and only when a reader was supplied. See section 7.
  dynamic "ace" {
    for_each = (each.key == "gold_reports" && var.reader_object_id != "") ? ["access", "default"] : []
    content {
      scope       = ace.value # "access" = this directory, "default" = inherited by new children
      type        = "user"
      id          = var.reader_object_id
      permissions = "r-x" # r to read, x to traverse into the directory
    }
  }
}

# ---------------------------------------------------------------------------
# 6. Access control, layer 1: RBAC (who may use the DATA PLANE at all)
# ---------------------------------------------------------------------------
# Owning the subscription does NOT let you read file contents with Entra ID.
# Control-plane roles (Owner/Contributor) manage the account; DATA roles
# (Storage Blob Data *) read and write files. Give yourself Data Owner so the
# az CLI with `--auth-mode login` works in scripts/demo.sh.
resource "azurerm_role_assignment" "me_data_owner" {
  scope                = azurerm_storage_account.lake.id
  role_definition_name = "Storage Blob Data Owner"
  principal_id         = data.azurerm_client_config.current.object_id
}

# Optional read-only consumer of the GOLD layer only (scoped to one filesystem)
resource "azurerm_role_assignment" "reader_gold" {
  count = var.reader_object_id == "" ? 0 : 1

  # ARM scope of a filesystem = account id + /blobServices/default/containers/<name>
  scope                = "${azurerm_storage_account.lake.id}/blobServices/default/containers/${azurerm_storage_data_lake_gen2_filesystem.layer["gold"].name}"
  role_definition_name = "Storage Blob Data Reader"
  principal_id         = var.reader_object_id
}

# ---------------------------------------------------------------------------
# 7. Access control, layer 2: ACLs (POSIX-style, per directory/file)
# ---------------------------------------------------------------------------
# RBAC is coarse (account/filesystem). ACLs are fine-grained (one folder).
# Evaluation order: RBAC first; if a role already allows the action, ACLs are
# NOT checked. If RBAC does not grant it, the ACLs decide.
# The ACL itself is declared inside the directory resource in step 4 (the
# dynamic "ace" block): the optional reader gets r-x on gold/reports.
# NOTE: an ACL alone is not enough for a reader to get in: they also need
# execute (x) on every parent directory, including the filesystem root, or a
# data role (RBAC). Here the reader gets the RBAC Reader role on gold (step 6),
# so the ACL is shown for learning rather than being the only gate.

# ---------------------------------------------------------------------------
# 8. Lifecycle management: cheaper tiers for old raw data
# ---------------------------------------------------------------------------
resource "azurerm_storage_management_policy" "lifecycle" {
  storage_account_id = azurerm_storage_account.lake.id

  rule {
    name    = "cool-old-raw-data"
    enabled = true

    filters {
      blob_types   = ["blockBlob"]
      prefix_match = ["bronze/raw"] # <filesystem>/<path prefix>
    }

    actions {
      base_blob {
        tier_to_cool_after_days_since_modification_greater_than = 30
        delete_after_days_since_modification_greater_than       = 365
      }
    }
  }
}

# ---------------------------------------------------------------------------
# Outputs
# ---------------------------------------------------------------------------
output "storage_account_name" {
  value = azurerm_storage_account.lake.name
}

output "dfs_endpoint" {
  description = "The Data Lake (DFS) endpoint, used by Spark/Synapse/Databricks via abfss://"
  value       = azurerm_storage_account.lake.primary_dfs_endpoint
}

output "blob_endpoint" {
  description = "Same data, Blob endpoint (multi-protocol access)"
  value       = azurerm_storage_account.lake.primary_blob_endpoint
}

output "abfss_uris" {
  description = "abfss://<filesystem>@<account>.dfs.core.windows.net  (append a path)"
  value = {
    for fs in var.filesystems :
    fs => "abfss://${fs}@${azurerm_storage_account.lake.name}.dfs.core.windows.net"
  }
}

output "demo_command" {
  value = "./scripts/demo.sh"
}
