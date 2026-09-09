terraform {
  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 4.0"
    }

    tls = {
      source  = "hashicorp/tls"
      version = "~> 4.0"
    }
  }
}

provider "azurerm" {
  features {}
}

# ============================================================
# Variables
# ============================================================

variable "location" {
  description = "Azure region"
  type        = string
  default     = "East US"
}

variable "resource_group_name" {
  description = "Resource group for the load balancer lab"
  type        = string
  default     = "rg-lb-lab"
}

variable "admin_username" {
  description = "Linux VM administrator username"
  type        = string
  default     = "azureuser"
}

# ============================================================
# 1. Resource Group
# ============================================================

resource "azurerm_resource_group" "main" {
  name     = var.resource_group_name
  location = var.location
}

# ============================================================
# 2. Virtual Network
# ============================================================

resource "azurerm_virtual_network" "main" {
  name                = "vnet-lb-lab"
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name

  address_space = [
    "10.20.0.0/16"
  ]
}

# ============================================================
# 3. Backend Subnet
# ============================================================

resource "azurerm_subnet" "backend" {
  name                 = "snet-backend"
  resource_group_name  = azurerm_resource_group.main.name
  virtual_network_name = azurerm_virtual_network.main.name

  address_prefixes = [
    "10.20.1.0/24"
  ]
}

# ============================================================
# 4. Network Security Group
#
# Terraform owns the NSG association.
# No manual `az network vnet subnet update` required.
# ============================================================

resource "azurerm_network_security_group" "backend" {
  name                = "nsg-backend"
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name

  # Allow HTTP traffic from the Internet to the backend.
  #
  # This is required because the public Load Balancer forwards
  # client traffic to the VMSS instances.
  security_rule {
    name                       = "Allow-HTTP-From-Internet"
    priority                   = 100
    direction                  = "Inbound"
    access                     = "Allow"
    protocol                   = "Tcp"

    source_port_range          = "*"
    destination_port_range     = "80"

    source_address_prefix     = "Internet"
    destination_address_prefix = "*"
  }

  # Allow Azure Load Balancer health probes.
  #
  # The LB uses this to determine whether backend instances are healthy.
  security_rule {
    name                       = "Allow-HTTP-From-AzureLoadBalancer"
    priority                   = 110
    direction                  = "Inbound"
    access                     = "Allow"
    protocol                   = "Tcp"

    source_port_range          = "*"
    destination_port_range     = "80"

    source_address_prefix     = "AzureLoadBalancer"
    destination_address_prefix = "*"
  }
}

# ============================================================
# 5. Associate NSG with Backend Subnet
#
# This is the part that eliminates the manual Azure CLI command.
# ============================================================

resource "azurerm_subnet_network_security_group_association" "backend" {
  subnet_id                 = azurerm_subnet.backend.id
  network_security_group_id = azurerm_network_security_group.backend.id
}

# ============================================================
# 6. Public IP
# ============================================================

resource "azurerm_public_ip" "load_balancer" {
  name                = "pip-lb"
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name

  allocation_method = "Static"
  sku               = "Standard"
}

# ============================================================
# 7. Azure Load Balancer
# ============================================================

resource "azurerm_lb" "public" {
  name                = "lb-public"
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name

  sku = "Standard"

  frontend_ip_configuration {
    name = "frontend-public"

    public_ip_address_id = azurerm_public_ip.load_balancer.id
  }
}

# ============================================================
# 8. Backend Address Pool
# ============================================================

resource "azurerm_lb_backend_address_pool" "web" {
  name            = "backend-web"
  loadbalancer_id = azurerm_lb.public.id
}

# ============================================================
# 9. Health Probe
# ============================================================

resource "azurerm_lb_probe" "http" {
  name            = "probe-http"
  loadbalancer_id = azurerm_lb.public.id

  protocol = "Http"
  port     = 80
  request_path = "/"
}

# ============================================================
# 10. Load Balancer Rule
#
# Public :80 -> Backend :80
# ============================================================

resource "azurerm_lb_rule" "http" {
  name            = "rule-http"
  loadbalancer_id = azurerm_lb.public.id

  protocol = "Tcp"

  frontend_port = 80
  backend_port  = 80

  frontend_ip_configuration_name = "frontend-public"

  backend_address_pool_ids = [
    azurerm_lb_backend_address_pool.web.id
  ]

  probe_id = azurerm_lb_probe.http.id
}

# ============================================================
# 11. SSH Key
# ============================================================

resource "tls_private_key" "vmss" {
  algorithm = "RSA"
  rsa_bits  = 4096
}

# ============================================================
# 12. Linux VM Scale Set
# ============================================================

resource "azurerm_linux_virtual_machine_scale_set" "web" {
  name                = "vmss-web"
  resource_group_name = azurerm_resource_group.main.name
  location            = azurerm_resource_group.main.location

  sku      = "Standard_D2s_v7"
  instances = 2

  admin_username = var.admin_username

  # ----------------------------------------------------------
  # SSH
  # ----------------------------------------------------------

  admin_ssh_key {
    username = var.admin_username

    public_key = tls_private_key.vmss.public_key_openssh
  }

  # ----------------------------------------------------------
  # Ubuntu
  # ----------------------------------------------------------

  source_image_reference {
    publisher = "Canonical"
    offer     = "0001-com-ubuntu-server-jammy"
    sku       = "22_04-lts-gen2"
    version   = "latest"
  }

  # ----------------------------------------------------------
  # OS Disk
  # ----------------------------------------------------------

  os_disk {
    caching              = "ReadWrite"
    storage_account_type = "Standard_LRS"
  }

  # ----------------------------------------------------------
  # Install Nginx
  #
  # Each instance returns its hostname so that you can see
  # Load Balancer distribution.
  # ----------------------------------------------------------

  custom_data = base64encode(<<-EOF
    #!/bin/bash

    set -e

    apt-get update
    apt-get install -y nginx

    HOSTNAME=$(hostname)

    cat > /var/www/html/index.html <<HTML
    <!DOCTYPE html>
    <html>
    <head>
      <title>Azure Load Balancer Lab</title>
    </head>
    <body>
      <h1>Azure Load Balancer Lab</h1>
      <p>Served by: $HOSTNAME</p>
    </body>
    </html>
    HTML

    systemctl enable nginx
    systemctl restart nginx
  EOF
  )

  # ----------------------------------------------------------
  # Network Interface
  # ----------------------------------------------------------

  network_interface {
    name    = "nic-web"
    primary = true

    ip_configuration {
      name      = "ipconfig-web"
      primary   = true
      subnet_id = azurerm_subnet.backend.id

      load_balancer_backend_address_pool_ids = [
        azurerm_lb_backend_address_pool.web.id
      ]
    }
  }

  # Make sure the NSG association exists before the VMSS
  # instances are created.
  depends_on = [
    azurerm_subnet_network_security_group_association.backend
  ]
}

# ============================================================
# Outputs
# ============================================================

output "load_balancer_public_ip" {
  description = "Public IP address of the Azure Load Balancer"
  value       = azurerm_public_ip.load_balancer.ip_address
}

output "load_balancer_url" {
  description = "URL to test the Load Balancer"
  value       = "http://${azurerm_public_ip.load_balancer.ip_address}"
}

output "vmss_name" {
  description = "Name of the backend VM Scale Set"
  value       = azurerm_linux_virtual_machine_scale_set.web.name
}

output "backend_subnet" {
  description = "Backend subnet CIDR"
  value       = azurerm_subnet.backend.address_prefixes
}