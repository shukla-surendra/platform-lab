terraform {
  required_version = ">= 1.5.0"

  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 4.0"
    }
  }
}

provider "azurerm" {
  features {}
}

# ============================================================
# 1. RESOURCE GROUP
# ============================================================

resource "azurerm_resource_group" "network" {
  name     = "rg-vnet-demo"
  location = "East US"
}


# ============================================================
# 2. VIRTUAL NETWORK
# ============================================================

resource "azurerm_virtual_network" "main" {
  name                = "vnet-demo"
  location            = azurerm_resource_group.network.location
  resource_group_name = azurerm_resource_group.network.name

  address_space = ["10.0.0.0/16"]
}


# ============================================================
# 3. PUBLIC SUBNET 1
# ============================================================

resource "azurerm_subnet" "public_1" {
  name                 = "snet-public-1"
  resource_group_name  = azurerm_resource_group.network.name
  virtual_network_name = azurerm_virtual_network.main.name

  address_prefixes = ["10.0.1.0/24"]
}


# ============================================================
# 4. PUBLIC SUBNET 2
# ============================================================

resource "azurerm_subnet" "public_2" {
  name                 = "snet-public-2"
  resource_group_name  = azurerm_resource_group.network.name
  virtual_network_name = azurerm_virtual_network.main.name

  address_prefixes = ["10.0.2.0/24"]
}


# ============================================================
# 5. PRIVATE SUBNET 1
# ============================================================

resource "azurerm_subnet" "private_1" {
  name                 = "snet-private-1"
  resource_group_name  = azurerm_resource_group.network.name
  virtual_network_name = azurerm_virtual_network.main.name

  address_prefixes = ["10.0.11.0/24"]
}


# ============================================================
# 6. PRIVATE SUBNET 2
# ============================================================

resource "azurerm_subnet" "private_2" {
  name                 = "snet-private-2"
  resource_group_name  = azurerm_resource_group.network.name
  virtual_network_name = azurerm_virtual_network.main.name

  address_prefixes = ["10.0.12.0/24"]
}


# ============================================================
# 7. PUBLIC NSG
# ============================================================

resource "azurerm_network_security_group" "public" {
  name                = "nsg-public"
  location            = azurerm_resource_group.network.location
  resource_group_name = azurerm_resource_group.network.name

  # Allow SSH
  security_rule {
    name                       = "Allow-SSH"
    priority                   = 100
    direction                  = "Inbound"
    access                     = "Allow"
    protocol                   = "Tcp"

    source_port_range          = "*"
    destination_port_range     = "22"

    source_address_prefix      = "*"
    destination_address_prefix = "*"
  }

  # Allow HTTP
  security_rule {
    name                       = "Allow-HTTP"
    priority                   = 110
    direction                  = "Inbound"
    access                     = "Allow"
    protocol                   = "Tcp"

    source_port_range          = "*"
    destination_port_range     = "80"

    source_address_prefix      = "*"
    destination_address_prefix = "*"
  }

  # Allow HTTPS
  security_rule {
    name                       = "Allow-HTTPS"
    priority                   = 120
    direction                  = "Inbound"
    access                     = "Allow"
    protocol                   = "Tcp"

    source_port_range          = "*"
    destination_port_range     = "443"

    source_address_prefix      = "*"
    destination_address_prefix = "*"
  }
}


# ============================================================
# 8. PRIVATE NSG
# ============================================================

resource "azurerm_network_security_group" "private" {
  name                = "nsg-private"
  location            = azurerm_resource_group.network.location
  resource_group_name = azurerm_resource_group.network.name

  # Allow SSH only from inside the VNet
  security_rule {
    name                       = "Allow-SSH-From-VNet"
    priority                   = 100
    direction                  = "Inbound"
    access                     = "Allow"
    protocol                   = "Tcp"

    source_port_range          = "*"
    destination_port_range     = "22"

    source_address_prefix      = "VirtualNetwork"
    destination_address_prefix = "*"
  }

  # Allow HTTP from VNet
  security_rule {
    name                       = "Allow-HTTP-From-VNet"
    priority                   = 110
    direction                  = "Inbound"
    access                     = "Allow"
    protocol                   = "Tcp"

    source_port_range          = "*"
    destination_port_range     = "80"

    source_address_prefix      = "VirtualNetwork"
    destination_address_prefix = "*"
  }
}


# ============================================================
# 9. ASSOCIATE PUBLIC NSG WITH PUBLIC SUBNET 1
# ============================================================

resource "azurerm_subnet_network_security_group_association" "public_1" {
  subnet_id                 = azurerm_subnet.public_1.id
  network_security_group_id = azurerm_network_security_group.public.id
}


# ============================================================
# 10. ASSOCIATE PUBLIC NSG WITH PUBLIC SUBNET 2
# ============================================================

resource "azurerm_subnet_network_security_group_association" "public_2" {
  subnet_id                 = azurerm_subnet.public_2.id
  network_security_group_id = azurerm_network_security_group.public.id
}


# ============================================================
# 11. ASSOCIATE PRIVATE NSG WITH PRIVATE SUBNET 1
# ============================================================

resource "azurerm_subnet_network_security_group_association" "private_1" {
  subnet_id                 = azurerm_subnet.private_1.id
  network_security_group_id = azurerm_network_security_group.private.id
}


# ============================================================
# 12. ASSOCIATE PRIVATE NSG WITH PRIVATE SUBNET 2
# ============================================================

resource "azurerm_subnet_network_security_group_association" "private_2" {
  subnet_id                 = azurerm_subnet.private_2.id
  network_security_group_id = azurerm_network_security_group.private.id
}


# ============================================================
# 13. NAT GATEWAY PUBLIC IP
# ============================================================

resource "azurerm_public_ip" "nat" {
  name                = "pip-nat-gateway"
  location            = azurerm_resource_group.network.location
  resource_group_name = azurerm_resource_group.network.name

  allocation_method = "Static"
  sku               = "Standard"
}


# ============================================================
# 14. NAT GATEWAY
# ============================================================

resource "azurerm_nat_gateway" "main" {
  name                = "nat-gateway"
  location            = azurerm_resource_group.network.location
  resource_group_name = azurerm_resource_group.network.name

  sku_name = "Standard"
}


# ============================================================
# 15. ASSOCIATE PUBLIC IP WITH NAT GATEWAY
# ============================================================

resource "azurerm_nat_gateway_public_ip_association" "main" {
  nat_gateway_id       = azurerm_nat_gateway.main.id
  public_ip_address_id = azurerm_public_ip.nat.id
}


# ============================================================
# 16. ASSOCIATE NAT GATEWAY WITH PRIVATE SUBNET 1
# ============================================================

resource "azurerm_subnet_nat_gateway_association" "private_1" {
  subnet_id      = azurerm_subnet.private_1.id
  nat_gateway_id = azurerm_nat_gateway.main.id
}


# ============================================================
# 17. ASSOCIATE NAT GATEWAY WITH PRIVATE SUBNET 2
# ============================================================

resource "azurerm_subnet_nat_gateway_association" "private_2" {
  subnet_id      = azurerm_subnet.private_2.id
  nat_gateway_id = azurerm_nat_gateway.main.id
}


# ============================================================
# 18. ROUTE TABLE
# ============================================================

resource "azurerm_route_table" "private" {
  name                = "rt-private"
  location            = azurerm_resource_group.network.location
  resource_group_name = azurerm_resource_group.network.name

  route {
    name           = "Internet"
    address_prefix = "0.0.0.0/0"

    next_hop_type = "Internet"
  }
}


# ============================================================
# 19. ASSOCIATE ROUTE TABLE WITH PRIVATE SUBNET 1
# ============================================================

resource "azurerm_subnet_route_table_association" "private_1" {
  subnet_id      = azurerm_subnet.private_1.id
  route_table_id = azurerm_route_table.private.id
}


# ============================================================
# 20. ASSOCIATE ROUTE TABLE WITH PRIVATE SUBNET 2
# ============================================================

resource "azurerm_subnet_route_table_association" "private_2" {
  subnet_id      = azurerm_subnet.private_2.id
  route_table_id = azurerm_route_table.private.id
}


# ============================================================
# OUTPUTS
# ============================================================

output "resource_group_name" {
  value = azurerm_resource_group.network.name
}

output "vnet_name" {
  value = azurerm_virtual_network.main.name
}

output "vnet_id" {
  value = azurerm_virtual_network.main.id
}

output "vnet_address_space" {
  value = azurerm_virtual_network.main.address_space
}

output "public_subnet_1_id" {
  value = azurerm_subnet.public_1.id
}

output "public_subnet_2_id" {
  value = azurerm_subnet.public_2.id
}

output "private_subnet_1_id" {
  value = azurerm_subnet.private_1.id
}

output "private_subnet_2_id" {
  value = azurerm_subnet.private_2.id
}

output "nat_gateway_public_ip" {
  value = azurerm_public_ip.nat.ip_address
}