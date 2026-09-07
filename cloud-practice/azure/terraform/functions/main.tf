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
resource "azurerm_resource_group" "func" {
  name     = "rg-functions-demo"
  location = "Central India"
}

resource "random_string" "suffix" {
  length  = 6
  special = false
  upper   = false
}

# 2. Function Apps require a Storage Account of their own -- not for your
# function's data, but for the platform's internal state (triggers,
# logs, deployment packages).
resource "azurerm_storage_account" "func" {
  name                     = "stfunc${random_string.suffix.result}"
  resource_group_name      = azurerm_resource_group.func.name
  location                 = azurerm_resource_group.func.location
  account_tier             = "Standard"
  account_replication_type = "LRS"
}

# 3. Consumption plan ("Y1") -- pay-per-execution, scales to zero when
# idle. This is what makes Functions "serverless"; an App Service Plan
# here instead would bill for reserved capacity even at zero traffic.
resource "azurerm_service_plan" "func" {
  name                = "asp-functions-demo"
  resource_group_name = azurerm_resource_group.func.name
  location            = azurerm_resource_group.func.location
  os_type             = "Linux"
  sku_name            = "Y1"
}

# 4. The Function App itself. This provisions the empty app/runtime --
# actually deploying function code is a separate step (`func azure
# functionapp publish`, or a CI pipeline), not something Terraform does.
resource "azurerm_linux_function_app" "demo" {
  name                       = "func-demo-${random_string.suffix.result}"
  resource_group_name        = azurerm_resource_group.func.name
  location                   = azurerm_resource_group.func.location
  service_plan_id            = azurerm_service_plan.func.id
  storage_account_name       = azurerm_storage_account.func.name
  storage_account_access_key = azurerm_storage_account.func.primary_access_key

  site_config {
    application_stack {
      node_version = "18"
    }
  }
}

output "function_app_name" {
  value = azurerm_linux_function_app.demo.name
}

output "default_hostname" {
  value = azurerm_linux_function_app.demo.default_hostname
}
