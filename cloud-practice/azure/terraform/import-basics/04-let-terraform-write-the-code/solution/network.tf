# Tidied version of what Terraform generated:
#   - removed empty values ([], {}, "", null)
#   - security_rule written as a block instead of a list of objects
#   - hard-coded "rg-lesson04" replaced with references
#   - added comments

resource "azurerm_resource_group" "lesson" {
  name     = "rg-lesson04"
  location = "centralindia"
}

resource "azurerm_network_security_group" "web" {
  name                = "nsg-web"
  resource_group_name = azurerm_resource_group.lesson.name
  location            = azurerm_resource_group.lesson.location

  security_rule {
    name                       = "allow-https"
    priority                   = 100
    direction                  = "Inbound"
    access                     = "Allow"
    protocol                   = "Tcp"
    source_port_range          = "*"
    destination_port_range     = "443"
    source_address_prefix      = "*"
    destination_address_prefix = "*"
  }
}
