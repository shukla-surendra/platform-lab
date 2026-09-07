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
resource "azurerm_resource_group" "cosmos" {
  name     = "rg-cosmos-demo"
  location = "Central India"
}

# 2. Cosmos DB account names are globally unique across all of Azure.
resource "random_string" "suffix" {
  length  = 6
  special = false
  upper   = false
}

# 3. Cosmos DB Account -- "GlobalDocumentDB" kind means the SQL (Core)
# API, the default/most common of Cosmos DB's five wire-protocol options
# (the others emulate MongoDB, Cassandra, Gremlin, Table). free_tier_enabled
# claims your subscription's ONE allowed free Cosmos account (1000 RU/s +
# 25GB storage, genuinely free) -- if you've already used it elsewhere,
# this apply fails rather than silently billing you.
resource "azurerm_cosmosdb_account" "demo" {
  name                = "cosmos-demo-${random_string.suffix.result}"
  resource_group_name = azurerm_resource_group.cosmos.name
  location            = azurerm_resource_group.cosmos.location
  offer_type          = "Standard"
  kind                = "GlobalDocumentDB"
  free_tier_enabled   = true

  consistency_policy {
    consistency_level = "Session"
  }

  geo_location {
    location          = azurerm_resource_group.cosmos.location
    failover_priority = 0
  }
}

# 4. Database -- a namespace for containers, roughly analogous to a
# schema/keyspace, not itself where RU/s or partitioning are configured.
resource "azurerm_cosmosdb_sql_database" "demo" {
  name                = "demo-database"
  resource_group_name = azurerm_resource_group.cosmos.name
  account_name        = azurerm_cosmosdb_account.demo.name
}

# 5. Container -- where documents actually live, and where the partition
# key (Cosmos DB's horizontal-scaling unit) is set. Autoscale 1000 RU/s
# max stays within the free-tier grant as long as this is the account's
# only container.
resource "azurerm_cosmosdb_sql_container" "demo" {
  name                = "demo-container"
  resource_group_name = azurerm_resource_group.cosmos.name
  account_name        = azurerm_cosmosdb_account.demo.name
  database_name       = azurerm_cosmosdb_sql_database.demo.name
  partition_key_paths = ["/id"]

  autoscale_settings {
    max_throughput = 1000
  }
}

output "cosmosdb_endpoint" {
  value = azurerm_cosmosdb_account.demo.endpoint
}

output "primary_key" {
  value     = azurerm_cosmosdb_account.demo.primary_key
  sensitive = true
}
