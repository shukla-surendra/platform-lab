# Stage 02 -- describe the manually-created resources EXACTLY as they exist.
#
# Goal: `terraform plan` says "8 to import, 0 to add, 0 to change, 0 to destroy".
# Any non-zero "change" means this config disagrees with reality and applying
# would silently mutate a resource you only meant to adopt.

resource "azurerm_resource_group" "lab" {
  name     = local.rg_name
  location = var.location
  tags     = { env = "lab", owner = "manual" }
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
  allow_nested_items_to_be_public = false # provider default is true -> would flip it!
  tags                            = { env = "lab", owner = "manual" }
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
  tags                = { env = "lab", owner = "manual" }
}

resource "azurerm_network_security_rule" "allow_ssh" {
  name                        = "allow-ssh"
  resource_group_name         = azurerm_resource_group.lab.name
  network_security_group_name = azurerm_network_security_group.lab.name
  priority                    = 100
  direction                   = "Inbound"
  access                      = "Allow"
  protocol                    = "Tcp"
  source_address_prefix       = "203.0.113.0/24"
  source_port_range           = "*"
  destination_address_prefix  = "*"
  destination_port_range      = "22"
}

resource "azurerm_virtual_network" "lab" {
  name                = "vnet-import-lab"
  resource_group_name = azurerm_resource_group.lab.name
  location            = azurerm_resource_group.lab.location
  address_space       = ["10.50.0.0/16"]
  tags                = { env = "lab", owner = "manual" }
}

# Subnets are modelled as separate resources, NOT inline `subnet {}` blocks
# on the VNet -- mixing the two makes each fight the other on every plan.
resource "azurerm_subnet" "app" {
  name                 = "snet-app"
  resource_group_name  = azurerm_resource_group.lab.name
  virtual_network_name = azurerm_virtual_network.lab.name
  address_prefixes     = ["10.50.1.0/24"]

  # Newer az CLI / API versions create subnets as "private" (no implicit
  # outbound internet). The provider still defaults this to true, so without
  # this line the first plan shows `false -> true` -- import would re-open it.
  default_outbound_access_enabled = false
}

resource "azurerm_subnet_network_security_group_association" "app" {
  subnet_id                 = azurerm_subnet.app.id
  network_security_group_id = azurerm_network_security_group.lab.id
}
