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
resource "azurerm_resource_group" "kv" {
  name     = "rg-keyvault-demo"
  location = "Central India"
}

resource "random_string" "suffix" {
  length  = 6
  special = false
  upper   = false
}

# 2. Who's running this -- needed for both the vault's tenant_id and the
# access policy below, which grants secrets access to whoever applies
# this, not to some other identity.
data "azurerm_client_config" "current" {}

# 3. Key Vault -- standard SKU, soft-delete on (can't be turned off on
# current azurerm, minimum retention 7 days), purge protection OFF so
# `terraform destroy` can actually remove it instead of leaving a
# soft-deleted vault occupying the name for the retention period.
resource "azurerm_key_vault" "demo" {
  name                       = "kv-demo-${random_string.suffix.result}"
  resource_group_name        = azurerm_resource_group.kv.name
  location                   = azurerm_resource_group.kv.location
  tenant_id                  = data.azurerm_client_config.current.tenant_id
  sku_name                   = "standard"
  soft_delete_retention_days = 7
  purge_protection_enabled   = false
  # false -- this project uses the older access-policy model (see the
  # azurerm_key_vault_access_policy resource below), not RBAC-based
  # authorization. Current azurerm requires this explicitly; there's no
  # default that silently picks one for you.
  rbac_authorization_enabled = false
}

# 4. Access policy -- without this, even the vault's creator gets 403 on
# every secret operation. Azure Key Vault's access model is opt-in per
# identity, not "owner of the resource can do anything."
resource "azurerm_key_vault_access_policy" "creator" {
  key_vault_id = azurerm_key_vault.demo.id
  tenant_id    = data.azurerm_client_config.current.tenant_id
  object_id    = data.azurerm_client_config.current.object_id

  secret_permissions = ["Get", "List", "Set", "Delete", "Purge"]
}

# 5. A demo secret, so there's something to actually read on first use.
resource "azurerm_key_vault_secret" "demo" {
  name         = "demo-secret"
  value        = "hello-from-terraform"
  key_vault_id = azurerm_key_vault.demo.id

  depends_on = [azurerm_key_vault_access_policy.creator]
}

output "key_vault_name" {
  value = azurerm_key_vault.demo.name
}

output "key_vault_uri" {
  value = azurerm_key_vault.demo.vault_uri
}
