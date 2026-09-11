terraform {
  required_providers {
    azurerm = { source = "hashicorp/azurerm" }
  }
}

provider "azurerm" {
  features {}
}

# 1. Resource group -- the role is scoped to exactly this RG, nothing wider.
resource "azurerm_resource_group" "demo" {
  name     = "rg-custom-role-demo"
  location = "Central India"
}

# 2. Custom role: "VM Operator (Custom)" -- read everything in the RG and
# start/restart VMs, but no create/delete/write on VMs or anything else.
# assignable_scopes pins it to this one RG; it won't show up as assignable
# anywhere else in the subscription.
resource "azurerm_role_definition" "vm_operator" {
  name        = "VM Operator (Custom) - ${azurerm_resource_group.demo.name}"
  scope       = azurerm_resource_group.demo.id
  description = "Can read all resources in the RG and start/restart VMs. Cannot create, delete, or otherwise modify anything."

  permissions {
    actions = [
      "*/read",
      "Microsoft.Compute/virtualMachines/start/action",
      "Microsoft.Compute/virtualMachines/restart/action",
    ]
    not_actions = []
  }

  assignable_scopes = [
    azurerm_resource_group.demo.id,
  ]
}

# 3. Who's applying this -- used to bind the role below so there's a
# principal to actually verify the assignment against.
data "azurerm_client_config" "current" {}

# 4. Bind the custom role to whoever ran `terraform apply`. RBAC is
# additive, so this doesn't take anything away if that principal already
# has broader access (e.g. Owner) -- it just proves the role assigns and
# resolves cleanly.
resource "azurerm_role_assignment" "vm_operator_binding" {
  scope              = azurerm_resource_group.demo.id
  role_definition_id = azurerm_role_definition.vm_operator.role_definition_resource_id
  principal_id       = data.azurerm_client_config.current.object_id
}

output "role_definition_id" {
  value = azurerm_role_definition.vm_operator.role_definition_resource_id
}

output "role_definition_name" {
  value = azurerm_role_definition.vm_operator.name
}

output "resource_group_id" {
  value = azurerm_resource_group.demo.id
}
