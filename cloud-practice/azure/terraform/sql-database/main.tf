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
resource "azurerm_resource_group" "sql" {
  name     = "rg-sql-demo"
  location = "Central India"
}

# 2. SQL Server names are globally unique across all of Azure too.
resource "random_string" "suffix" {
  length  = 6
  special = false
  upper   = false
}

# 3. The admin password is generated here rather than hardcoded or taken
# as a variable -- keeps this fully self-contained (`terraform apply`
# alone is enough), at the cost of the password only being retrievable via
# `terraform output` (or straight from state) afterward, never logged.
resource "random_password" "admin" {
  length  = 20
  special = true
}

# 4. SQL Server -- the logical server that hosts one or more databases,
# not a VM. This is what carries the admin login and firewall rules.
resource "azurerm_mssql_server" "demo" {
  name                         = "sql-demo-${random_string.suffix.result}"
  resource_group_name          = azurerm_resource_group.sql.name
  location                     = azurerm_resource_group.sql.location
  version                      = "12.0"
  administrator_login          = "sqladmin"
  administrator_login_password = random_password.admin.result
}

# 5. The actual database -- Basic tier, the cheapest option (~$5/mo),
# fine for a demo, nowhere near enough DTUs for real workloads.
resource "azurerm_mssql_database" "demo" {
  name      = "demodb"
  server_id = azurerm_mssql_server.demo.id
  sku_name  = "Basic"
}

# 6. Firewall rule -- 0.0.0.0/0.0.0.0 is Azure's special-cased range
# meaning "allow other Azure services," NOT "allow the whole internet."
# Add your own IP as a second rule before connecting from a local client.
resource "azurerm_mssql_firewall_rule" "allow_azure_services" {
  name             = "AllowAzureServices"
  server_id        = azurerm_mssql_server.demo.id
  start_ip_address = "0.0.0.0"
  end_ip_address   = "0.0.0.0"
}

output "sql_server_fqdn" {
  value = azurerm_mssql_server.demo.fully_qualified_domain_name
}

output "admin_login" {
  value = azurerm_mssql_server.demo.administrator_login
}

output "admin_password" {
  value     = random_password.admin.result
  sensitive = true
}
