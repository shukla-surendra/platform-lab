# Only import blocks, and no matching resource blocks anywhere.
# `terraform plan -generate-config-out=generated.tf` fills that gap.

import {
  to = azurerm_resource_group.lesson
  id = "/subscriptions/${var.subscription_id}/resourceGroups/rg-lesson04"
}

import {
  to = azurerm_network_security_group.web
  id = "/subscriptions/${var.subscription_id}/resourceGroups/rg-lesson04/providers/Microsoft.Network/networkSecurityGroups/nsg-web"
}
