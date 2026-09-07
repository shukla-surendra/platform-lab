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
resource "azurerm_resource_group" "app" {
  name     = "rg-appservice-demo"
  location = "Central India"
}

# 2. Web App names must be globally unique -- they become
# <name>.azurewebsites.net.
resource "random_string" "suffix" {
  length  = 6
  special = false
  upper   = false
}

# 3. App Service Plan -- unlike Functions' Consumption plan, this reserves
# actual capacity and bills whether or not anything is running on it.
# "F1" (Free) has real limits (60 CPU-min/day, no custom domain/TLS, no
# always-on) but costs nothing -- swap to "B1" for a realistic always-on
# test.
resource "azurerm_service_plan" "app" {
  name                = "asp-appservice-demo"
  resource_group_name = azurerm_resource_group.app.name
  location            = azurerm_resource_group.app.location
  os_type             = "Linux"
  sku_name            = "F1"
}

# 4. The Web App itself -- Node 18 runtime, no code deployed yet. Unlike
# a Function App (event-triggered, scales to zero), this is a
# continuously-running app process -- the PaaS equivalent of "a VM
# running a web server," minus the VM/OS management.
resource "azurerm_linux_web_app" "demo" {
  name                = "app-demo-${random_string.suffix.result}"
  resource_group_name = azurerm_resource_group.app.name
  location            = azurerm_resource_group.app.location
  service_plan_id     = azurerm_service_plan.app.id

  site_config {
    application_stack {
      node_version = "18-lts"
    }
  }
}

output "default_hostname" {
  value = azurerm_linux_web_app.demo.default_hostname
}
