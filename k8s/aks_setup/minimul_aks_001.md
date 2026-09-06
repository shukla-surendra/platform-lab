```
resource "azurerm_container_registry" "acr" {
  name                = "aksdevacr123"
  resource_group_name = azurerm_resource_group.aks.name
  location            = azurerm_resource_group.aks.location
  sku                 = "Basic"
}
```
then push

aksdevacr123.azurecr.io/frontend
aksdevacr123.azurecr.io/backend

ACR
├── frontend
│   └── image:tag
└── backend
    └── image:tag



# 5.  A separate User Node Pool
resource "azurerm_kubernetes_cluster_node_pool" "user" {

  name = "userpool"
  kubernetes_cluster_id = azurerm_kubernetes_cluster.aks.id
  vm_size    = "Standard_D2s_v5"
  node_count = 1
  vnet_subnet_id = azurerm_subnet.aks.id

}
