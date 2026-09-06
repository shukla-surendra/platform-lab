## Common Terraform Setup For AKS

```
Terraform
│
├── Resource Group
├── Networking
│   ├── VNet
│   ├── Subnet
│   └── NSG / UDR (optional)
│
├── Identity
│   ├── Managed Identity
│   └── RBAC
│
├── AKS
│   ├── Control Plane
│   ├── System Node Pool
│   └── User Node Pool(s)
│
├── Container Registry
│   └── Azure Container Registry (ACR)
│
├── Security
│   ├── Key Vault
│   ├── Workload Identity
│   └── Azure RBAC
│
├── Monitoring
│   ├── Azure Monitor
│   └── Log Analytics
│
└── Optional
    ├── Application Gateway / Ingress
    ├── Private DNS
    ├── NAT Gateway
    └── Private Endpoint
```

## Node pools

In AKS, the Azure-managed control plane is separate and you don't manage its VMs/node pool. You need at least one node pool for worker nodes where your application pods run. Typically, the first/default node pool is the system node pool, which runs Kubernetes system components, and you can add user node pools for application workloads.

```
AKS
├── Control Plane → Managed by Azure
└── Node Pool(s) → Worker nodes you manage/configure
    ├── System node pool
    └── User node pool(s)
```

Don't put everything into the default node pool.

For a minimal AKS setup, you only need one System Node Pool.

```
AKS
├── Control Plane → Managed by Azure
└── System Node Pool → Worker nodes + system pods + your application pods
```

A common design is:

```
AKS
│
├── System Node Pool
│      └── CoreDNS
│      └── metrics
│      └── system workloads
│
├── User Node Pool
│      └── Application workloads
│
└── Optional GPU Node Pool
       └── ML workloads
```

There isn't a pre-existing default VNet specifically for AKS.

If you don't provide a VNet/subnet, AKS creates the required networking resources for you during cluster creation.

So:

- No VNet provided → AKS creates networking
- VNet provided → AKS uses your VNet/subnet.

VNet in Azure, the minimal things are:

- Resource Group – where the VNet lives.
- VNet – with an address space, e.g. 10.0.0.0/16.
- Subnet – a smaller range inside the VNet, e.g. 10.0.1.0/24.

That's basically it for a minimal VNet:

```
Resource Group
    └── VNet (10.0.0.0/16)
          └── Subnet (10.0.1.0/24)
```

Things like NSG, Route Table, NAT Gateway, Azure Firewall, etc. are optional and depend on your networking requirements.

```
network_profile {
  network_plugin    = "azure"
  service_cidr      = "10.1.0.0/16"
  dns_service_ip    = "10.1.0.10"
}
```

- `network_plugin = "azure"` → Tells AKS to use Azure CNI for pod networking.
- service_cidr → IP range reserved for Kubernetes Services (e.g. 10.1.0.20 for an nginx Service).
- dns_service_ip → IP of the Kubernetes internal DNS Service (e.g. 10.1.0.10).

```
VNet 10.0.0.0/16
 └── Subnet 10.0.1.0/24 → Nodes/Pods

Service CIDR 10.1.0.0/16 → Kubernetes Services
                           └── DNS: 10.1.0.10
```

```
Kubernetes CNI
│
├── Azure CNI         → Azure native networking
├── AWS VPC CNI       → AWS VPC native pod networking
├── GCP GKE CNI       → Google VPC native pod networking
├── Calico            → Networking + NetworkPolicy
├── Cilium            → eBPF + Networking + Security
└── Flannel           → Simple pod networking
```

Connecting this this setup created by folder "platform-lab/k8s/aks_setup/minimul_aks"

```
az aks get-credentials --resource-group rg-aks-dev --name aks-dev
```

```
kubectl config get-contexts
```

```
kubectl get nodes
```

```
aks-system-37475490-vmss000000   Ready
```

This is your worker node/VM created by the AKS System Node Pool.

You did define a node pool, indirectly. default_node_pool { ... } in your azurerm_kubernetes_cluster creates the System Node Pool. AKS requires at least one node pool, so that is why you see aks-system-....

```
AKS
├── Control Plane → Azure manages it
└── System Node Pool
    └── aks-system-... → Your worker node
```

```
kubectl get all
```

```
service/kubernetes   ClusterIP   10.1.0.1   443
```

This is a built-in Kubernetes Service that represents access to the Kubernetes API.

10.1.0.1 comes from your: service_cidr = 10.1.0.0/16

service/kubernetes is a Kubernetes Service, but you did not create it. Kubernetes automatically creates this built-in Service when the cluster is created.

So currently you have 1 worker node + the default Kubernetes API service.

ClusterIP 10.1.0.1 is the internal virtual IP of that Service. It provides a stable internal endpoint for the Kubernetes API server

10.1.0.1 (kubernetes ClusterIP) → used as an internal Service address for accessing the Kubernetes API. It is not specifically the control-plane → node communication IP.
Control plane and nodes do not have to be in the same VNet in AKS. AKS uses Azure-managed networking to connect the control plane to your nodes.
Your nodes are in your VNet/subnet because you explicitly configured vnet_subnet_id.

```
AKS
│
├── Control Plane → Azure managed
│        │
│        │ Azure-managed connectivity
│        ▼
│   Nodes → Your VNet/Subnet
│
└── kubernetes Service
       └── 10.1.0.1 → Kubernetes API endpoint
```

So VNet is primarily where your AKS nodes/pods live; the managed control plane is separate.
