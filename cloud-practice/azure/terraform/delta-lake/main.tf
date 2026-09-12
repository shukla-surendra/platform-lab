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
resource "azurerm_resource_group" "delta" {
  name     = "rg-deltalake-demo"
  location = "Central India"
}

resource "random_string" "suffix" {
  length  = 6
  special = false
  upper   = false
}

# 2. ADLS Gen2 storage account. The "Gen2" part is entirely
# is_hns_enabled = true (hierarchical namespace) -- without it this is
# plain Blob Storage, which only fakes directories via "/" in blob names
# (a "rename" is a full copy+delete of every blob under that prefix).
# HNS gives real directories with atomic, metadata-only rename/move --
# Delta Lake's transaction log commits rely on exactly that atomicity
# (see README's "How Delta Lake gets ACID out of plain files").
resource "azurerm_storage_account" "lake" {
  name                     = "stdeltalake${random_string.suffix.result}"
  resource_group_name      = azurerm_resource_group.delta.name
  location                 = azurerm_resource_group.delta.location
  account_tier             = "Standard"
  account_replication_type = "LRS"
  account_kind             = "StorageV2"
  is_hns_enabled           = true
}

# 3. A filesystem -- ADLS Gen2's name for what looks like a Blob container
# but, because HNS is on, is a real directory tree underneath. This is
# the actual "Data Lake" in Azure Data Lake Storage; Delta tables below
# live as paths inside it (e.g. "orders/", "orders/_delta_log/").
resource "azurerm_storage_data_lake_gen2_filesystem" "delta" {
  name               = "delta-lake"
  storage_account_id = azurerm_storage_account.lake.id
}

output "storage_account_name" {
  value = azurerm_storage_account.lake.name
}

output "filesystem_name" {
  value = azurerm_storage_data_lake_gen2_filesystem.delta.name
}

output "primary_access_key" {
  value     = azurerm_storage_account.lake.primary_access_key
  sensitive = true
}

output "abfss_uri_base" {
  description = "Base abfss:// URI -- append a table name (e.g. /orders) for a Delta table path."
  value       = "abfss://${azurerm_storage_data_lake_gen2_filesystem.delta.name}@${azurerm_storage_account.lake.name}.dfs.core.windows.net"
}
