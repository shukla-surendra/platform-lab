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
resource "azurerm_resource_group" "sb" {
  name     = "rg-servicebus-demo"
  location = "Central India"
}

# 2. Namespace names are globally unique across all of Azure.
resource "random_string" "suffix" {
  length  = 6
  special = false
  upper   = false
}

# 3. Namespace -- the container for queues/topics, and what carries the
# connection string. "Basic" tier only supports Queues (point-to-point);
# Topics/Subscriptions (pub/sub, one message fanned out to many
# subscribers) need at least "Standard".
resource "azurerm_servicebus_namespace" "demo" {
  name                = "sb-demo-${random_string.suffix.result}"
  resource_group_name = azurerm_resource_group.sb.name
  location            = azurerm_resource_group.sb.location
  sku                 = "Basic"
}

# 4. A Queue -- one producer, one logical consumer group, each message
# processed exactly once (vs. a Topic, where every Subscription gets its
# own copy of each message).
resource "azurerm_servicebus_queue" "demo" {
  name         = "demo-queue"
  namespace_id = azurerm_servicebus_namespace.demo.id
}

# 5. Authorization rule scoped to this one queue -- narrower than using
# the namespace's own root manage key, which would grant access to every
# queue/topic in the namespace, not just this one.
resource "azurerm_servicebus_queue_authorization_rule" "demo" {
  name     = "demo-queue-access"
  queue_id = azurerm_servicebus_queue.demo.id

  listen = true
  send   = true
  manage = false
}

output "namespace_name" {
  value = azurerm_servicebus_namespace.demo.name
}

output "queue_name" {
  value = azurerm_servicebus_queue.demo.name
}

output "connection_string" {
  value     = azurerm_servicebus_queue_authorization_rule.demo.primary_connection_string
  sensitive = true
}
