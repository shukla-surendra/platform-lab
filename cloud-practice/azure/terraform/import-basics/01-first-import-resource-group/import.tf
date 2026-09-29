# The import block: "the resource in main.tf is NOT new. It already exists
# in Azure at this ID, so adopt it instead of creating it."
#
# Every Azure resource has an ID shaped like a file path:
#   /subscriptions/<subscription-id>/resourceGroups/<resource-group-name>
#
# Once the import has been applied, this file has done its job. Delete it.
import {
  to = azurerm_resource_group.lesson
  id = "/subscriptions/${var.subscription_id}/resourceGroups/rg-lesson01"
}
