# Azure VNet with Terraform — Learning Guide

This project creates a complete Azure Virtual Network (VNet) environment using Terraform.

The purpose of this project is not only to create the infrastructure, but also to understand the fundamental concepts of **Azure networking**:

- Virtual Network (VNet)
- Subnets
- CIDR / IP addressing
- Network Security Groups (NSGs)
- Route Tables
- NAT Gateway
- Public vs Private subnets
- Public IPs
- How resources communicate inside a VNet
- How resources access the Internet
- How Azure networking compares with AWS VPC networking

---

# 1. Architecture

The Terraform configuration creates the following architecture:

```text
                              INTERNET
                                  |
                                  |
                         ┌────────▼────────┐
                         │   NAT Gateway   │
                         │   Public IP     │
                         └────────┬────────┘
                                  |
              ┌───────────────────┴──────────────────┐
              │                                     │
              │              Azure VNet             │
              │             10.0.0.0/16             │
              │                                     │
              │                                     │
      ┌───────▼────────┐                    ┌───────▼────────┐
      │ Public Subnet  │                    │ Private Subnet │
      │  10.0.1.0/24   │                    │ 10.0.11.0/24  │
      │                 │                    │                 │
      │      NSG        │                    │      NSG        │
      └─────────────────┘                    │                 │
                                             │  Route Table    │
      ┌─────────────────┐                    │                 │
      │ Public Subnet 2 │                    │  NAT Gateway    │
      │  10.0.2.0/24   │                    │                 │
      │                 │                    └─────────────────┘
      │      NSG        │
      └─────────────────┘                    ┌─────────────────┐
                                             │ Private Subnet 2│
                                             │ 10.0.12.0/24    │
                                             │                 │
                                             │      NSG         │
                                             │  Route Table     │
                                             │  NAT Gateway     │
                                             └─────────────────┘
```

The VNet is:

```text
10.0.0.0/16
```

Inside it we create four subnets:

```text
Public Subnet 1     10.0.1.0/24
Public Subnet 2     10.0.2.0/24

Private Subnet 1    10.0.11.0/24
Private Subnet 2    10.0.12.0/24
```

---

# 2. What is a VNet?

**VNet = Virtual Network**

An Azure VNet is your private network inside Azure.

It is similar to an AWS:

```text
Azure VNet
     ≈
AWS VPC
```

For example:

```text
VNet
10.0.0.0/16
```

means:

> Create a private network whose address space is 10.0.0.0 through 10.0.255.255.

Resources such as:

- Virtual Machines
- Azure Kubernetes Service
- Azure App Services with VNet integration
- Private Endpoints
- Azure Database services
- Network Interfaces

can communicate through Azure networking when configured appropriately.

---

# 3. VNet vs Subnet

A VNet is the larger network.

A subnet is a smaller network inside the VNet.

Think about it like this:

```text
VNet
10.0.0.0/16
│
├── Subnet A
│   10.0.1.0/24
│
├── Subnet B
│   10.0.2.0/24
│
├── Subnet C
│   10.0.11.0/24
│
└── Subnet D
    10.0.12.0/24
```

The VNet defines the overall address space.

Subnets divide that address space into smaller networks.

---

# 4. Understanding CIDR

The VNet uses:

```text
10.0.0.0/16
```

The `/16` means that the first 16 bits are the network portion.

An IPv4 address has 32 bits.

```text
10.0.0.0

10       . 0        . 0        . 0
8 bits    8 bits      8 bits      8 bits
```

Therefore:

```text
32 total bits
-
16 network bits
=
16 host bits
```

That gives:

```text
2^16 = 65,536 addresses
```

So:

```text
10.0.0.0/16
```

covers:

```text
10.0.0.0
      ...
10.0.255.255
```

---

# 5. What does /24 mean?

Our subnet is:

```text
10.0.1.0/24
```

A `/24` leaves 8 bits for hosts.

Therefore:

```text
2^8 = 256
```

addresses exist in the CIDR range.

The range is:

```text
10.0.1.0
through
10.0.1.255
```

Azure reserves some addresses in each subnet, so the number of usable IPs is smaller than the raw CIDR count.

---

# 6. Why use /16 for VNet and /24 for Subnets?

A common design is:

```text
VNet
10.0.0.0/16
```

Then divide it:

```text
10.0.1.0/24
10.0.2.0/24
10.0.3.0/24
...
10.0.254.0/24
```

This gives us room to create many subnets later.

For example:

```text
10.0.1.0/24    Web
10.0.2.0/24    Application
10.0.3.0/24    Database
10.0.4.0/24    AKS
10.0.5.0/24    Private Endpoints
```

The exact CIDR design depends on the workload.

---

# 7. Why can't subnets overlap?

Suppose the VNet is:

```text
10.0.0.0/16
```

This is valid:

```text
10.0.1.0/24
10.0.2.0/24
10.0.3.0/24
```

But this is invalid:

```text
10.0.1.0/24
10.0.1.0/24
```

because both subnets represent the same address range.

Also avoid partially overlapping ranges.

For example:

```text
10.0.1.0/24
10.0.1.128/25
```

These overlap.

Subnet CIDRs should be carefully planned before deploying a production network.

---

# 8. Terraform: Creating the VNet

The VNet is created with:

```hcl
resource "azurerm_virtual_network" "main" {
  name                = "vnet-demo"
  location            = azurerm_resource_group.network.location
  resource_group_name = azurerm_resource_group.network.name

  address_space = ["10.0.0.0/16"]
}
```

The important property is:

```hcl
address_space = ["10.0.0.0/16"]
```

This defines the address space of the VNet.

---

# 9. Creating a Subnet

Example:

```hcl
resource "azurerm_subnet" "public_1" {
  name                 = "snet-public-1"
  resource_group_name  = azurerm_resource_group.network.name
  virtual_network_name = azurerm_virtual_network.main.name

  address_prefixes = ["10.0.1.0/24"]
}
```

The important part is:

```hcl
address_prefixes = ["10.0.1.0/24"]
```

This subnet must fit inside the VNet's address space:

```text
VNet:

10.0.0.0/16

       ↓

Subnet:

10.0.1.0/24
```

---

# 10. Public vs Private Subnet

This is an important concept.

Azure does not have a property like:

```text
public = true
```

or:

```text
private = true
```

on a subnet.

A subnet becomes effectively "public" or "private" based on how the resources and networking are configured.

For example:

```text
Internet
   |
   ▼
Public IP
   |
   ▼
VM NIC
   |
   ▼
Public Subnet
```

A VM with a public IP can potentially be reached from the Internet, assuming NSG and other networking rules allow it.

A private VM might look like:

```text
Internet
   X
   |
   |
Private VM
   |
   ▼
NAT Gateway
   |
   ▼
Internet
```

The private VM can initiate outbound connections but does not become directly reachable from the Internet simply because it has outbound Internet access.

---

# 11. Important: A Public Subnet Doesn't Automatically Make a VM Public

This is a very common misunderstanding.

Suppose we have:

```text
VNet
 |
 └── Public Subnet
       |
       └── VM
```

The VM does NOT automatically get a public IP.

You would need to configure a public IP on the VM's network interface.

Conceptually:

```text
Public Subnet
     |
     └── NIC
           |
           ├── Private IP
           |
           └── Public IP
```

Therefore, "public subnet" is mostly a design convention.

---

# 12. What is an NSG?

NSG stands for:

**Network Security Group**

It is Azure's network traffic filtering mechanism.

An NSG contains rules such as:

```text
Allow TCP 80
Allow TCP 443
Allow TCP 22
Deny traffic
```

An NSG can be associated with:

1. A subnet
2. A network interface (NIC)

For example:

```text
NSG
 |
 ▼
Subnet
 |
 ▼
NIC
 |
 ▼
VM
```

or:

```text
NSG
 |
 ▼
NIC
 |
 ▼
VM
```

---

# 13. NSG is NOT the VNet Firewall

This distinction is important.

A VNet and an NSG are separate Azure resources.

```text
VNet
 |
 ├── Subnet
 │     |
 │     └── NSG
 │
 └── Subnet
       |
       └── NSG
```

The VNet provides the networking environment.

The NSG controls allowed/denied network traffic.

---

# 14. What does an NSG rule look like?

Example:

```hcl
security_rule {
  name                       = "Allow-HTTP"
  priority                   = 110
  direction                  = "Inbound"
  access                     = "Allow"
  protocol                   = "Tcp"

  source_port_range          = "*"
  destination_port_range     = "80"

  source_address_prefix      = "*"
  destination_address_prefix = "*"
}
```

This means:

```text
Inbound
TCP
Destination port = 80
Allow
```

In simple terms:

> Allow incoming HTTP traffic on TCP port 80.

---

# 15. Why is priority required?

NSG rules have priorities.

Example:

```text
100  Allow SSH
110  Allow HTTP
120  Allow HTTPS
```

Lower number = higher priority.

For example:

```text
100
110
120
```

Rule 100 is evaluated before rule 110.

Azure also has default NSG rules.

Your custom rules are evaluated according to priority relative to those defaults.

---

# 16. What is a Route Table?

A route table determines where network traffic should go.

Conceptually:

```text
Source
  |
  ▼
Route Table
  |
  ├── VNet
  ├── Internet
  └── Other network
```

For example:

```text
0.0.0.0/0 → Internet
```

means:

> For destinations that don't match a more specific route, send traffic toward the Internet.

---

# 17. System Routes

Azure automatically creates several routes.

You don't have to manually create routes for basic VNet communication.

For example:

```text
10.0.0.0/16
```

is the VNet address space.

If one VM communicates with another VM inside the VNet:

```text
VM A
10.0.1.4
   |
   ▼
Azure networking
   |
   ▼
VM B
10.0.11.5
```

Azure already knows that both addresses belong to the VNet.

You don't normally need to create a custom route for this.

---

# 18. What is a NAT Gateway?

NAT stands for:

**Network Address Translation**

A NAT Gateway provides outbound Internet connectivity for resources in a subnet.

Example:

```text
Private VM
10.0.11.5
     |
     ▼
NAT Gateway
     |
     ▼
Public IP
     |
     ▼
Internet
```

The VM has a private IP.

The Internet sees the NAT Gateway's public IP.

---

# 19. Why do we need NAT Gateway?

Imagine a private VM:

```text
Private VM
10.0.11.5
```

The VM might need to:

```text
apt update
download packages
call an external API
download files
access GitHub
```

But you don't want to give the VM its own public IP.

NAT Gateway provides:

```text
Private VM
     |
     ▼
NAT Gateway
     |
     ▼
Public IP
     |
     ▼
Internet
```

This gives the VM outbound Internet access without directly exposing the VM to inbound Internet connections.

---

# 20. NAT Gateway vs Public IP on VM

Without NAT:

```text
VM
 |
 └── Public IP
       |
       └── Internet
```

With NAT:

```text
VM
 |
 └── Private IP
       |
       └── NAT Gateway
              |
              └── Public IP
                    |
                    └── Internet
```

The second architecture is generally preferable for private workloads.

---

# 21. What is a Route Table Association?

Creating a route table is not enough.

We need to associate it with a subnet.

For example:

```hcl
resource "azurerm_subnet_route_table_association" "private_1" {
  subnet_id      = azurerm_subnet.private_1.id
  route_table_id = azurerm_route_table.private.id
}
```

This means:

```text
Route Table
     |
     ▼
Private Subnet 1
```

The subnet will then use the custom routes defined in that route table.

---

# 22. NAT Gateway Association

Similarly, creating a NAT Gateway is not enough.

We associate it with the subnet:

```hcl
resource "azurerm_subnet_nat_gateway_association" "private_1" {
  subnet_id      = azurerm_subnet.private_1.id
  nat_gateway_id = azurerm_nat_gateway.main.id
}
```

Conceptually:

```text
Private Subnet
      |
      ▼
NAT Gateway
      |
      ▼
Public IP
      |
      ▼
Internet
```

---

# 23. Public IP for NAT Gateway

The NAT Gateway itself needs a public IP:

```hcl
resource "azurerm_public_ip" "nat" {
  name                = "pip-nat-gateway"
  location            = azurerm_resource_group.network.location
  resource_group_name = azurerm_resource_group.network.name

  allocation_method = "Static"
  sku               = "Standard"
}
```

The relationship is:

```text
Public IP
    |
    ▼
NAT Gateway
    |
    ▼
Private Subnet
```

---

# 24. Understanding Network Interfaces

A VM doesn't directly attach to a subnet.

The relationship is:

```text
VM
 |
 ▼
NIC
 |
 ▼
Subnet
 |
 ▼
VNet
```

NIC = Network Interface Card.

The NIC has a private IP address.

For example:

```text
VM
 |
 └── NIC
      |
      └── Private IP: 10.0.11.5
```

If the VM needs a public IP:

```text
VM
 |
 └── NIC
      |
      ├── Private IP
      |
      └── Public IP
```

This is important when thinking about NSGs.

An NSG can be attached to:

```text
Subnet
```

or:

```text
NIC
```

---

# 25. Azure NIC vs AWS ENI

If you know AWS, this is a useful comparison.

```text
Azure NIC
    ≈
AWS ENI
```

Both represent a network interface attached to a compute resource.

Conceptually:

```text
Azure:

VM
 |
 NIC
 |
Subnet
 |
VNet
```

AWS:

```text
EC2
 |
 ENI
 |
Subnet
 |
VPC
```

---

# 26. Azure VNet vs AWS VPC

A useful mental mapping is:

| Azure | AWS |
|---|---|
| VNet | VPC |
| Subnet | Subnet |
| NIC | ENI |
| NSG | Security Group |
| Route Table | Route Table |
| NAT Gateway | NAT Gateway |
| Public IP | Elastic/Public IP |
| VNet Peering | VPC Peering |
| VNet-to-VNet | VPC-to-VPC connectivity |
| VPN Gateway | VPN Gateway |
| Azure Firewall | AWS Network Firewall / related firewall services |

The concepts are very similar, although the implementation details are different.

---

# 27. Important Difference: NSG vs AWS Security Group

In AWS, you commonly associate a Security Group with an EC2 instance through its ENI.

In Azure, an NSG can be associated with:

```text
Subnet
```

or:

```text
NIC
```

For example:

```text
                 NSG
                  |
                  ▼
             ┌─────────┐
             │ Subnet  │
             └────┬────┘
                  |
          ┌───────┼────────┐
          ▼       ▼        ▼
         VM1     VM2      VM3
```

This means one NSG associated with a subnet can apply traffic filtering to resources in that subnet.

You can also attach an NSG directly to an individual NIC when more granular control is required.

---

# 28. Traffic Flow: VM to VM

Suppose:

```text
VM1
10.0.1.10

VM2
10.0.11.10
```

Both are inside:

```text
10.0.0.0/16
```

Traffic conceptually looks like:

```text
VM1
 |
 ▼
NIC
 |
 ▼
Subnet
 |
 ▼
Azure VNet routing
 |
 ▼
Subnet
 |
 ▼
NIC
 |
 ▼
VM2
```

The VNet provides connectivity between the subnets.

NSGs determine whether the traffic is allowed.

---

# 29. Traffic Flow: Private VM to Internet

Suppose:

```text
Private VM
10.0.11.10
```

It wants to access:

```text
example.com
```

The traffic is conceptually:

```text
Private VM
    |
    ▼
NIC
    |
    ▼
Private Subnet
    |
    ▼
NAT Gateway
    |
    ▼
NAT Public IP
    |
    ▼
Internet
```

The external service sees the NAT Gateway's public IP rather than:

```text
10.0.11.10
```

---

# 30. Traffic Flow: Internet to Private VM

Consider:

```text
Internet
    |
    X
    |
Private VM
```

A NAT Gateway is primarily for outbound connectivity.

It does not turn the private VM into a publicly reachable server.

If you need inbound Internet access to a private application, you would normally use an architecture such as:

```text
Internet
   |
   ▼
Azure Load Balancer / Application Gateway
   |
   ▼
Private Subnet
   |
   ▼
Application VM
```

The exact service depends on the workload.

---

# 31. Why Have Two Public Subnets?

We create:

```text
10.0.1.0/24
10.0.2.0/24
```

instead of only one.

In real environments, multiple subnets can help with:

- separation of workloads
- availability-zone design
- security boundaries
- application tiers
- scaling
- service-specific requirements

For example:

```text
Public Subnet 1
    |
    └── Load Balancer

Public Subnet 2
    |
    └── Load Balancer
```

This can be useful for highly available architectures.

---

# 32. Why Have Two Private Subnets?

We create:

```text
10.0.11.0/24
10.0.12.0/24
```

For example:

```text
Private Subnet 1
    |
    ├── Application VM 1
    └── Application VM 2


Private Subnet 2
    |
    ├── Application VM 3
    └── Application VM 4
```

This provides additional network segmentation.

In production, you would usually design the subnets around workload, availability, and service requirements rather than simply creating two because "two is better."

---

# 33. Why use separate NSGs?

This configuration creates:

```text
Public NSG
Private NSG
```

The public NSG allows:

```text
SSH
HTTP
HTTPS
```

The private NSG allows:

```text
SSH from VNet
HTTP from VNet
```

Conceptually:

```text
Public workload
      |
      ▼
Public NSG
      |
      ├── HTTP
      ├── HTTPS
      └── SSH


Private workload
      |
      ▼
Private NSG
      |
      ├── HTTP from VNet
      └── SSH from VNet
```

In production, SSH should normally be restricted to trusted administrative sources rather than allowing it from everywhere.

---

# 34. Why use NSGs if Azure already has a VNet?

Because a VNet provides network connectivity.

It does not mean:

```text
Everything can communicate with everything.
```

You might have:

```text
Web
 |
 ▼
Application
 |
 ▼
Database
```

You may want:

```text
Internet → Web       ALLOW
Web → Application    ALLOW
Application → DB     ALLOW
Internet → DB        DENY
Web → DB             DENY
```

NSGs help enforce this kind of network-level access control.

---

# 35. Resource Dependency

Terraform automatically understands dependencies from references.

For example:

```hcl
virtual_network_name = azurerm_virtual_network.main.name
```

Terraform understands:

```text
VNet
 |
 ▼
Subnet
```

Similarly:

```hcl
subnet_id = azurerm_subnet.private_1.id
```

creates a dependency:

```text
Subnet
 |
 ▼
NAT Gateway association
```

Terraform therefore creates resources in an appropriate dependency order.

---

# 36. Terraform Resource Flow

The overall Terraform dependency graph looks approximately like:

```text
Resource Group
      |
      ▼
     VNet
      |
      ├───────────────┐
      ▼               ▼
 Public Subnets    Private Subnets
      |               |
      ▼               ▼
     NSG          NSG + Route Table
                      |
                      ▼
                 NAT Gateway
                      |
                      ▼
                  Public IP
```

---

# 37. Files in This Project

The simplest project structure is:

```text
azure-vnet/
│
├── main.tf
└── README.md
```

`main.tf` contains the infrastructure.

`README.md` explains the infrastructure.

Later, when you become more comfortable with Terraform, you can split the configuration into:

```text
azure-vnet/
│
├── main.tf
├── variables.tf
├── outputs.tf
├── providers.tf
├── versions.tf
└── README.md
```

For learning, keeping everything in one file initially is perfectly reasonable.

---

# 38. Deploying the Infrastructure

Make sure you are authenticated with Azure CLI:

```bash
az login
```

Then check your subscription:

```bash
az account show
```

If you have multiple subscriptions:

```bash
az account list
```

Select the desired subscription:

```bash
az account set --subscription "<subscription-id>"
```

Then initialize Terraform:

```bash
terraform init
```

Format the configuration:

```bash
terraform fmt
```

Validate it:

```bash
terraform validate
```

Create an execution plan:

```bash
terraform plan
```

Apply it:

```bash
terraform apply
```

Terraform will ask for confirmation.

Enter:

```text
yes
```

---

# 39. Checking the Resources

After deployment:

```bash
terraform output
```

You can also use Azure CLI:

```bash
az network vnet list -o table
```

List subnets:

```bash
az network vnet subnet list \
  --resource-group rg-vnet-demo \
  --vnet-name vnet-demo \
  -o table
```

List NSGs:

```bash
az network nsg list \
  --resource-group rg-vnet-demo \
  -o table
```

List route tables:

```bash
az network route-table list \
  --resource-group rg-vnet-demo \
  -o table
```

---

# 40. Destroying the Environment

Because this is a learning environment, you can remove everything using:

```bash
terraform destroy
```

Terraform will show the resources that will be deleted.

Enter:

```text
yes
```

This is useful for avoiding unnecessary Azure charges from resources that you no longer need.

---

# 41. What This Terraform Does NOT Create

This project creates the networking foundation.

It does not create:

- Virtual Machines
- Application Gateway
- Azure Load Balancer
- Azure Firewall
- Azure Bastion
- VPN Gateway
- VNet Peering
- Private DNS Zones
- Private Endpoints
- Azure Kubernetes Service
- Databases

Those can be added later.

This is intentional.

The goal is to first understand:

```text
VNet
 |
 ├── Subnet
 ├── NSG
 ├── Route Table
 └── NAT Gateway
```

before adding more complicated services.

---

# 42. Recommended Learning Path

If you are new to Azure networking, learn these concepts in this order:

```text
1. IP Address
       ↓
2. CIDR
       ↓
3. VNet
       ↓
4. Subnet
       ↓
5. NIC
       ↓
6. Private IP
       ↓
7. Public IP
       ↓
8. NSG
       ↓
9. Route Table
       ↓
10. NAT Gateway
       ↓
11. Load Balancer
       ↓
12. Application Gateway
       ↓
13. VNet Peering
       ↓
14. Private Endpoint
       ↓
15. VPN Gateway
       ↓
16. Azure Firewall
```

Once these concepts are clear, most Azure networking becomes much easier.

---

# 43. The Most Important Mental Model

Remember this:

```text
                    AZURE
                      |
                      |
                    VNet
                10.0.0.0/16
                      |
          ┌───────────┴───────────┐
          |                       |
       Subnet                  Subnet
   10.0.1.0/24              10.0.11.0/24
          |                       |
         NSG                     NSG
          |                       |
         NIC                     NIC
          |                       |
         VM                      VM
                                  |
                             NAT Gateway
                                  |
                              Public IP
                                  |
                              Internet
```

The important relationships are:

```text
VNet
 └── Subnet
      └── NIC
           └── VM
```

and:

```text
Subnet
 └── NSG
```

and:

```text
Private Subnet
 └── NAT Gateway
       └── Public IP
```

and:

```text
Subnet
 └── Route Table
```

---

# 44. VNet Is Not the Same as Internet Connectivity

A VNet gives resources a private networking environment.

It does not automatically mean that every resource is Internet-accessible.

Think about three different things separately:

### Network

```text
VNet
```

Provides the private network.

### Security

```text
NSG
```

Controls allowed/denied network traffic.

### Routing

```text
Route Table
```

Determines where traffic goes.

### Outbound Internet

```text
NAT Gateway
```

Provides predictable outbound Internet connectivity for private subnets.

### Inbound Internet

Usually requires something such as:

```text
Public IP
+
Load Balancer / Application Gateway
+
NSG
```

depending on the architecture.

---

# 45. A Simple Example

Imagine you are building an application:

```text
                 INTERNET
                    |
                    ▼
             Load Balancer
                    |
                    ▼
          ┌─────────────────┐
          │   Web Subnet    │
          │                 │
          │   Web VM 1      │
          │   Web VM 2      │
          └────────┬────────┘
                   |
                   ▼
          ┌─────────────────┐
          │ Application     │
          │ Subnet          │
          │                 │
          │ App VM 1        │
          │ App VM 2        │
          └────────┬────────┘
                   |
                   ▼
          ┌─────────────────┐
          │ Database Subnet │
          │                 │
          │ Database        │
          └─────────────────┘
```

NSGs can then enforce:

```text
Internet
   |
   ▼
Web
   |
   ▼
Application
   |
   ▼
Database
```

while blocking unwanted paths.

That is one of the fundamental ideas behind cloud network architecture.

---

# 46. Production Considerations

This example is designed for learning.

For production, you would normally reconsider several things.

### SSH

The example allows SSH broadly in the public NSG.

That is not recommended for production.

Prefer restricting SSH to:

```text
Trusted IP ranges
```

or use:

```text
Azure Bastion
```

or another controlled administration mechanism.

### NSG rules

Use the minimum access required.

For example:

```text
Allow 443
```

is preferable to:

```text
Allow *
```

when HTTPS is all the application needs.

### Subnet sizing

Don't randomly choose CIDRs.

Plan the address space based on:

- number of resources
- scaling requirements
- future subnets
- peering
- VPN connectivity
- on-premises networks

### NAT Gateway

Use NAT Gateway where predictable outbound connectivity is required for private resources.

### Route Tables

Don't create custom routes unless there is a reason.

Azure provides system routes automatically.

---

# 47. Final Mental Model

When looking at an Azure network, ask these questions in order:

### 1. What is my VNet?

Example:

```text
10.0.0.0/16
```

### 2. How have I divided it?

```text
10.0.1.0/24
10.0.2.0/24
10.0.11.0/24
10.0.12.0/24
```

### 3. What resources are inside each subnet?

```text
Web
Application
Database
Private Endpoints
etc.
```

### 4. What security rules apply?

```text
NSG
```

### 5. Where does traffic go?

```text
Route Table
```

### 6. How does private infrastructure reach the Internet?

```text
NAT Gateway
```

### 7. How does Internet traffic reach my application?

Usually through something such as:

```text
Public IP
   ↓
Load Balancer / Application Gateway
   ↓
Application
```

Once you can answer these seven questions, you have a strong foundation in Azure VNet networking.

---

# 48. Azure Networking Cheat Sheet

```text
VNet
    = Your private Azure network

Subnet
    = Smaller network inside VNet

CIDR
    = Defines IP address range

NIC
    = Network interface attached to VM

Private IP
    = Internal address

Public IP
    = Internet-routable address

NSG
    = Network traffic filtering rules

Route Table
    = Controls routing

NAT Gateway
    = Outbound Internet access for private resources

Load Balancer
    = Distributes network traffic

Application Gateway
    = Layer 7 application/load-balancing service

VNet Peering
    = Connects VNets

VPN Gateway
    = Connects Azure to external networks using VPN

Azure Firewall
    = Managed network firewall
```

---

# 49. AWS → Azure Mental Translation

If you already understand AWS, remember:

```text
AWS                         Azure

VPC                  →      VNet

Subnet               →      Subnet

EC2                   →      Virtual Machine

ENI                   →      NIC

Security Group       →      NSG

Route Table          →      Route Table

NAT Gateway          →      NAT Gateway

Internet Gateway     →      Azure Internet connectivity
                              (Azure doesn't use an
                               equivalent IGW resource)

Elastic IP           →      Public IP

VPC Peering          →      VNet Peering

Transit Gateway      →      Virtual WAN / hub-based
                              connectivity patterns
```

The biggest thing to avoid is trying to map every Azure service **1:1** to AWS. The networking concepts are similar, but the architecture and implementation are not always identical.

---

# 50. Summary

The core Azure networking structure is:

```text
                    VNet
                10.0.0.0/16
                     |
       ┌─────────────┼─────────────┐
       |             |             |
    Subnet         Subnet        Subnet
       |             |             |
      NSG           NSG           NSG
       |             |             |
      NIC           NIC           NIC
       |             |             |
      VM            VM            VM
```

For private workloads:

```text
VM
 |
 ▼
Private Subnet
 |
 ▼
NAT Gateway
 |
 ▼
Public IP
 |
 ▼
Internet
```

For controlled inbound application traffic:

```text
Internet
 |
 ▼
Public IP
 |
 ▼
Load Balancer / Application Gateway
 |
 ▼
Private/Application Subnet
 |
 ▼
VM
```

The key concepts to understand are therefore:

```text
VNet
  ↓
Subnet
  ↓
NIC
  ↓
IP Address

and

NSG
  ↓
Security

Route Table
  ↓
Routing

NAT Gateway
  ↓
Outbound Internet
```

Once these concepts are clear, you can start adding Azure Load Balancer, VMs, Application Gateway, Private Endpoints, VNet Peering, VPN Gateway, and other services on top of this foundation.