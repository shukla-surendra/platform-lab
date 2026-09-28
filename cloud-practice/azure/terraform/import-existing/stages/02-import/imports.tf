# Import blocks (Terraform >= 1.5): "this resource address should adopt the
# Azure object with this ID". They are part of the plan, so `terraform plan`
# previews the import *and* any diff between this config and reality before
# anything is written to state.
#
# Once applied, the resources live in state and these blocks become no-ops --
# stage 03 deletes this file entirely.

import {
  to = azurerm_resource_group.lab
  id = local.rg_id
}

import {
  to = azurerm_storage_account.lab
  id = "${local.rg_id}/providers/Microsoft.Storage/storageAccounts/${var.storage_account_name}"
}

import {
  to = azurerm_storage_container.appdata
  id = "${local.rg_id}/providers/Microsoft.Storage/storageAccounts/${var.storage_account_name}/blobServices/default/containers/appdata"
}

import {
  to = azurerm_network_security_group.lab
  id = "${local.rg_id}/providers/Microsoft.Network/networkSecurityGroups/nsg-import-lab"
}

import {
  to = azurerm_network_security_rule.allow_ssh
  id = "${local.rg_id}/providers/Microsoft.Network/networkSecurityGroups/nsg-import-lab/securityRules/allow-ssh"
}

import {
  to = azurerm_virtual_network.lab
  id = "${local.rg_id}/providers/Microsoft.Network/virtualNetworks/vnet-import-lab"
}

import {
  to = azurerm_subnet.app
  id = "${local.rg_id}/providers/Microsoft.Network/virtualNetworks/vnet-import-lab/subnets/snet-app"
}

# The association is not a real Azure object -- it is the subnet's
# networkSecurityGroup property -- so its import ID is the subnet ID.
import {
  to = azurerm_subnet_network_security_group_association.app
  id = "${local.rg_id}/providers/Microsoft.Network/virtualNetworks/vnet-import-lab/subnets/snet-app"
}
