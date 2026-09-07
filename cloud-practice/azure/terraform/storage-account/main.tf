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
resource "azurerm_resource_group" "storage" {
  name     = "rg-storage-demo"
  location = "Central India"
}

# 2. Storage account names must be globally unique across ALL of Azure,
# lowercase alphanumeric only, 3-24 chars -- a random suffix means this
# applies cleanly no matter who else has already claimed a name.
resource "random_string" "suffix" {
  length  = 6
  special = false
  upper   = false
}

# 3. Storage Account -- StorageV2, locally-redundant, hot access tier
# (cheapest option; fine for a demo, not for anything needing geo-redundancy).
resource "azurerm_storage_account" "demo" {
  name                     = "stdemo${random_string.suffix.result}"
  resource_group_name      = azurerm_resource_group.storage.name
  location                 = azurerm_resource_group.storage.location
  account_tier             = "Standard"
  account_replication_type = "LRS"
  account_kind             = "StorageV2"
  access_tier              = "Hot"
}

# 4. A private Blob container -- "container" here means a folder-like
# grouping inside the storage account, unrelated to Docker/ACI containers.
resource "azurerm_storage_container" "demo" {
  name                  = "demo-container"
  storage_account_id    = azurerm_storage_account.demo.id
  container_access_type = "private"
}

output "storage_account_name" {
  value = azurerm_storage_account.demo.name
}

output "blob_endpoint" {
  value = azurerm_storage_account.demo.primary_blob_endpoint
}

output "primary_connection_string" {
  value     = azurerm_storage_account.demo.primary_connection_string
  sensitive = true
}
