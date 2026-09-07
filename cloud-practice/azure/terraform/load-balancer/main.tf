terraform {
  required_providers {
    azurerm = { source = "hashicorp/azurerm" }
    tls     = { source = "hashicorp/tls" }
  }
}

provider "azurerm" {
  features {}
}

# 1. Resource Group
resource "azurerm_resource_group" "lb" {
  name     = "rg-lb-demo"
  location = "Central India"
}

# 2. Virtual Network + Subnet
resource "azurerm_virtual_network" "lb" {
  name                = "vnet-lb-demo"
  location            = azurerm_resource_group.lb.location
  resource_group_name = azurerm_resource_group.lb.name
  address_space       = ["10.20.0.0/16"]
}

resource "azurerm_subnet" "lb" {
  name                 = "snet-lb-demo"
  resource_group_name  = azurerm_resource_group.lb.name
  virtual_network_name = azurerm_virtual_network.lb.name
  address_prefixes     = ["10.20.1.0/24"]
}

# 3. Public IP for the Load Balancer's frontend -- Standard SKU, required
# to pair with a Standard LB.
resource "azurerm_public_ip" "lb" {
  name                = "pip-lb-demo"
  resource_group_name = azurerm_resource_group.lb.name
  location            = azurerm_resource_group.lb.location
  allocation_method   = "Static"
  sku                 = "Standard"
}

# 4. The Load Balancer -- frontend config only; backend pool, probe, and
# rule are separate resources below because in Terraform's azurerm
# provider they're independently addressable, not nested blocks.
resource "azurerm_lb" "demo" {
  name                = "lb-demo"
  resource_group_name = azurerm_resource_group.lb.name
  location            = azurerm_resource_group.lb.location
  sku                 = "Standard"

  frontend_ip_configuration {
    name                 = "frontend"
    public_ip_address_id = azurerm_public_ip.lb.id
  }
}

resource "azurerm_lb_backend_address_pool" "demo" {
  name            = "backend-pool"
  loadbalancer_id = azurerm_lb.demo.id
}

# 5. Health probe -- the LB only routes to instances answering here.
# TCP is the simplest option; an HTTP probe (checking a specific path and
# status code) is the more realistic choice for a real web backend.
resource "azurerm_lb_probe" "demo" {
  name            = "http-probe"
  loadbalancer_id = azurerm_lb.demo.id
  protocol        = "Tcp"
  port            = 80
}

resource "azurerm_lb_rule" "demo" {
  name                           = "http-rule"
  loadbalancer_id                = azurerm_lb.demo.id
  protocol                       = "Tcp"
  frontend_port                  = 80
  backend_port                   = 80
  frontend_ip_configuration_name = "frontend"
  backend_address_pool_ids       = [azurerm_lb_backend_address_pool.demo.id]
  probe_id                       = azurerm_lb_probe.demo.id
}

# 6. SSH keypair for the scale set instances (same reasoning as vm/main.tf).
resource "tls_private_key" "lb" {
  algorithm = "RSA"
  rsa_bits  = 4096
}

# 7. A 2-instance VM Scale Set behind the LB -- this is what makes the LB
# actually testable end-to-end: curl the LB's public IP repeatedly and
# see the response alternate between the two instances (their hostname is
# written into index.html by custom_data at boot). Without something in
# the backend pool, the LB has nothing to route to and there's nothing to
# actually observe.
resource "azurerm_linux_virtual_machine_scale_set" "demo" {
  name                = "vmss-lb-demo"
  resource_group_name = azurerm_resource_group.lb.name
  location            = azurerm_resource_group.lb.location
  sku                 = "Standard_B1s"
  instances           = 2
  admin_username      = "azureuser"

  admin_ssh_key {
    username   = "azureuser"
    public_key = tls_private_key.lb.public_key_openssh
  }

  source_image_reference {
    publisher = "Canonical"
    offer     = "0001-com-ubuntu-server-jammy"
    sku       = "22_04-lts-gen2"
    version   = "latest"
  }

  os_disk {
    caching              = "ReadWrite"
    storage_account_type = "Standard_LRS"
  }

  # nginx + a per-instance index.html so each backend visibly identifies
  # itself in the LB's round-robin response.
  custom_data = base64encode(<<-EOF
    #!/bin/bash
    apt-get update && apt-get install -y nginx
    echo "Hello from $(hostname)" > /var/www/html/index.html
  EOF
  )

  network_interface {
    name    = "nic"
    primary = true

    ip_configuration {
      name                                   = "internal"
      primary                                = true
      subnet_id                              = azurerm_subnet.lb.id
      load_balancer_backend_address_pool_ids = [azurerm_lb_backend_address_pool.demo.id]
    }
  }
}

output "load_balancer_ip" {
  value = azurerm_public_ip.lb.ip_address
}
