# Stage 03 -- Terraform now OWNS these resources; change them through code.
#
# Every change below is an IN-PLACE update (`~` in the plan). If you ever see
# `-/+` (destroy-then-create) against the storage account, stop: that would
# wipe the application's data. prevent_destroy makes Terraform refuse outright.
#
# imports.tf is gone -- those resources are already in state.

locals {
  tags = { env = "lab", owner = "platform-team", managed_by = "terraform" }
}

resource "azurerm_resource_group" "lab" {
  name     = local.rg_name
  location = var.location
  tags     = local.tags # CHANGED: owner + managed_by
}

resource "azurerm_storage_account" "lab" {
  name                            = var.storage_account_name
  resource_group_name             = azurerm_resource_group.lab.name
  location                        = azurerm_resource_group.lab.location
  account_kind                    = "StorageV2"
  account_tier                    = "Standard"
  account_replication_type        = "LRS"
  access_tier                     = "Hot"
  min_tls_version                 = "TLS1_2"
  https_traffic_only_enabled      = true
  allow_nested_items_to_be_public = false
  tags                            = local.tags # CHANGED

  # NEW: blob versioning + 7-day soft delete protect the app's data.
  blob_properties {
    versioning_enabled = true
    delete_retention_policy {
      days = 7
    }
    container_delete_retention_policy {
      days = 7
    }
  }

  lifecycle {
    prevent_destroy = true # NEW: holds real data -- never recreate
  }
}

resource "azurerm_storage_container" "appdata" {
  name                  = "appdata"
  storage_account_id    = azurerm_storage_account.lab.id
  container_access_type = "private"
}

resource "azurerm_network_security_group" "lab" {
  name                = "nsg-import-lab"
  resource_group_name = azurerm_resource_group.lab.name
  location            = azurerm_resource_group.lab.location
  tags                = local.tags # CHANGED
}

resource "azurerm_network_security_rule" "allow_ssh" {
  name                        = "allow-ssh"
  resource_group_name         = azurerm_resource_group.lab.name
  network_security_group_name = azurerm_network_security_group.lab.name
  priority                    = 100
  direction                   = "Inbound"
  access                      = "Allow"
  protocol                    = "Tcp"
  source_address_prefix       = "198.51.100.0/24" # CHANGED: tighter source range
  source_port_range           = "*"
  destination_address_prefix  = "*"
  destination_port_range      = "22"
}

# NEW: a rule that never existed manually -- Terraform creates it.
resource "azurerm_network_security_rule" "allow_https" {
  name                        = "allow-https"
  resource_group_name         = azurerm_resource_group.lab.name
  network_security_group_name = azurerm_network_security_group.lab.name
  priority                    = 110
  direction                   = "Inbound"
  access                      = "Allow"
  protocol                    = "Tcp"
  source_address_prefix       = "Internet"
  source_port_range           = "*"
  destination_address_prefix  = "*"
  destination_port_range      = "443"
}

resource "azurerm_virtual_network" "lab" {
  name                = "vnet-import-lab"
  resource_group_name = azurerm_resource_group.lab.name
  location            = azurerm_resource_group.lab.location
  address_space       = ["10.50.0.0/16"]
  tags                = local.tags # CHANGED
}

resource "azurerm_subnet" "app" {
  name                 = "snet-app"
  resource_group_name  = azurerm_resource_group.lab.name
  virtual_network_name = azurerm_virtual_network.lab.name
  address_prefixes     = ["10.50.1.0/24"]
  service_endpoints    = ["Microsoft.Storage"] # CHANGED: in-place on the subnet

  default_outbound_access_enabled = false
}

resource "azurerm_subnet_network_security_group_association" "app" {
  subnet_id                 = azurerm_subnet.app.id
  network_security_group_id = azurerm_network_security_group.lab.id
}

# NEW: second subnet, Terraform-born.
resource "azurerm_subnet" "data" {
  name                 = "snet-data"
  resource_group_name  = azurerm_resource_group.lab.name
  virtual_network_name = azurerm_virtual_network.lab.name
  address_prefixes     = ["10.50.2.0/24"]

  default_outbound_access_enabled = false
}
