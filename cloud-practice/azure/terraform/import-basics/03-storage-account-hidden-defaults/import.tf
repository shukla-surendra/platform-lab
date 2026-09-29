# Two import blocks, one per resource. Notice the IDs nest like folders:
# the storage account lives INSIDE the resource group.

import {
  to = azurerm_resource_group.lesson
  id = "/subscriptions/${var.subscription_id}/resourceGroups/rg-lesson03"
}

import {
  to = azurerm_storage_account.lesson
  id = "/subscriptions/${var.subscription_id}/resourceGroups/rg-lesson03/providers/Microsoft.Storage/storageAccounts/${var.storage_account_name}"
}
