# Azure Load Balancer with Terraform

This project creates a simple **Azure Load Balancer lab** using Terraform.

The setup demonstrates how an Azure Load Balancer distributes HTTP traffic across multiple virtual machines running inside a **Virtual Machine Scale Set (VMSS)**.

The infrastructure is completely managed by Terraform, including the **Network Security Group (NSG)** and its association with the backend subnet. No manual Azure CLI configuration is required after deployment.

---

## 1. What are we building?

The architecture looks like this:

```text
                         Internet
                            |
                            | HTTP :80
                            |
                            v
                +------------------------+
                |   Public IP Address    |
                |      pip-lb             |
                +-----------+------------+
                            |
                            v
                +------------------------+
                |   Azure Load Balancer  |
                |      lb-public         |
                +-----------+------------+
                            |
                   Load Balancer Rule
                       TCP :80
                            |
                            v
                +------------------------+
                |    Backend Pool        |
                |     backend-web        |
                +-----------+------------+
                            |
                +-----------+-----------+
                |                       |
                v                       v
        +---------------+       +---------------+
        | VMSS Instance |       | VMSS Instance |
        |      #0       |       |      #1       |
        |    nginx      |       |    nginx      |
        |     :80       |       |     :80       |
        +-------+-------+       +-------+-------+
                |                       |
                +-----------+-----------+
                            |
                            v
                    Backend Subnet
                      10.20.1.0/24
                            |
                            v
                    Network Security
                         Group
                       nsg-backend
```

When you access:

```text
http://<load-balancer-public-ip>
```

Azure Load Balancer chooses one of the healthy VMSS instances and forwards the request to port `80`.

Each VM returns its hostname, so you can see which backend handled the request.

---

# 2. What will Terraform create?

Terraform creates the following Azure resources:

| Resource | Azure Name | Purpose |
|---|---|---|
| Resource Group | `rg-lb-lab` | Container for all resources |
| Virtual Network | `vnet-lb-lab` | Private network |
| Subnet | `snet-backend` | Network where VMSS instances live |
| Network Security Group | `nsg-backend` | Controls inbound/outbound network traffic |
| NSG Association | `snet-backend → nsg-backend` | Applies NSG rules to the subnet |
| Public IP | `pip-lb` | Public address for the Load Balancer |
| Load Balancer | `lb-public` | Distributes traffic |
| Frontend | `frontend-public` | Load Balancer's public-facing endpoint |
| Backend Pool | `backend-web` | Group of VMSS instances receiving traffic |
| Health Probe | `probe-http` | Checks whether backend instances are healthy |
| Load Balancer Rule | `rule-http` | Maps public port 80 to backend port 80 |
| VM Scale Set | `vmss-web` | Creates and manages 2 Linux VMs |
| SSH Key | Terraform-generated | Allows SSH access to VMSS instances |

---

# 3. Terraform resources vs Azure resources

One important concept when learning Terraform:

Terraform has its own **resource blocks**, while Azure has the actual **Azure resources**.

For example:

```hcl
resource "azurerm_virtual_network" "main" {
  name = "vnet-lb-lab"
}
```

Here:

```text
azurerm_virtual_network
        |
        +-- Terraform resource TYPE

main
        |
        +-- Terraform resource NAME

vnet-lb-lab
        |
        +-- Actual Azure resource NAME
```

Therefore:

```hcl
azurerm_virtual_network.main.id
```

means:

> Give me the Azure resource ID of the Virtual Network represented by the Terraform resource `main`.

---

# 4. Resource Group

Terraform:

```hcl
resource "azurerm_resource_group" "main" {
  name     = var.resource_group_name
  location = var.location
}
```

Creates:

```text
rg-lb-lab
```

## What is a Resource Group?

A Resource Group is a logical container for Azure resources.

Think of it as a folder:

```text
rg-lb-lab
│
├── vnet-lb-lab
├── snet-backend
├── nsg-backend
├── pip-lb
├── lb-public
└── vmss-web
```

It does not provide networking itself.

It simply helps organize and manage related Azure resources.

For this lab, everything belongs to:

```text
rg-lb-lab
```

---

# 5. Virtual Network (VNet)

Terraform:

```hcl
resource "azurerm_virtual_network" "main" {
  name = "vnet-lb-lab"

  address_space = [
    "10.20.0.0/16"
  ]
}
```

Creates:

```text
vnet-lb-lab
10.20.0.0/16
```

## What is a VNet?

An Azure Virtual Network is your private network inside Azure.

You can think of it as the equivalent of a traditional:

```text
Corporate network
        |
        +-- Private IP addresses
        +-- Subnets
        +-- Servers
```

The VNet has:

```text
10.20.0.0/16
```

available as its address space.

---

# 6. Understanding `10.20.0.0/16`

The `/16` means the first 16 bits identify the network.

The VNet therefore has a range of:

```text
10.20.0.0
        to
10.20.255.255
```

We don't put all of those addresses directly on VMs.

Instead, we divide the VNet into subnets.

---

# 7. Subnet

Terraform:

```hcl
resource "azurerm_subnet" "backend" {
  name = "snet-backend"

  address_prefixes = [
    "10.20.1.0/24"
  ]
}
```

Creates:

```text
snet-backend
10.20.1.0/24
```

The subnet exists inside the VNet:

```text
VNet
10.20.0.0/16
│
└── Subnet
    10.20.1.0/24
```

The VMSS instances are placed inside this subnet.

---

# 8. Network Security Group (NSG)

Terraform:

```hcl
resource "azurerm_network_security_group" "backend" {
  name = "nsg-backend"
}
```

Creates:

```text
nsg-backend
```

## What is an NSG?

An NSG controls network traffic.

You can think of it as a firewall attached to Azure networking.

For example:

```text
Internet
   |
   | TCP 80
   v
NSG
   |
   | ALLOW
   v
VM
```

Our NSG contains two important rules.

---

# 9. NSG Rule: Allow HTTP

```hcl
security_rule {
  name                       = "Allow-HTTP-From-Internet"
  priority                   = 100
  direction                  = "Inbound"
  access                     = "Allow"
  protocol                   = "Tcp"

  source_port_range          = "*"
  destination_port_range     = "80"

  source_address_prefix     = "Internet"
  destination_address_prefix = "*"
}
```

This means:

```text
Source:
Internet

Destination:
Backend instances

Protocol:
TCP

Port:
80

Action:
ALLOW
```

Therefore:

```text
Internet
    |
    | TCP 80
    v
NSG
    |
    | ALLOW
    v
VMSS
```

Without this rule, external users would not be able to reach the web servers.

---

# 10. NSG Rule: Allow Azure Load Balancer

```hcl
security_rule {
  name                       = "Allow-HTTP-From-AzureLoadBalancer"
  priority                   = 110
  direction                  = "Inbound"
  access                     = "Allow"
  protocol                   = "Tcp"

  source_port_range          = "*"
  destination_port_range     = "80"

  source_address_prefix     = "AzureLoadBalancer"
  destination_address_prefix = "*"
}
```

This rule allows Azure Load Balancer health probes to reach port 80.

The Load Balancer needs to ask:

```text
"Is this VM healthy?"
```

It does that using the health probe.

The traffic path is:

```text
Azure Load Balancer
        |
        | Health Probe TCP/HTTP 80
        v
      NSG
        |
        | ALLOW
        v
      nginx
```

---

# 11. NSG Association

This resource is particularly important:

```hcl
resource "azurerm_subnet_network_security_group_association" "backend" {
  subnet_id                 = azurerm_subnet.backend.id
  network_security_group_id = azurerm_network_security_group.backend.id
}
```

It connects:

```text
Subnet
   |
   v
snet-backend
   |
   |
   v
nsg-backend
```

This is why you no longer need to manually run:

```bash
az network vnet subnet update
```

Terraform manages the association.

This is an important Terraform principle:

> If Terraform owns a piece of infrastructure, don't manually change it with Azure CLI unless you intentionally want to change the Terraform configuration as well.

Otherwise you can create **configuration drift**.

---

# 12. Public IP

Terraform:

```hcl
resource "azurerm_public_ip" "load_balancer" {
  name = "pip-lb"

  allocation_method = "Static"
  sku               = "Standard"
}
```

Creates:

```text
pip-lb
```

This gives the Load Balancer a public IP address.

For example:

```text
20.x.x.x
```

The user connects to this address:

```text
Internet
   |
   v
20.x.x.x
```

The public IP belongs to the Load Balancer frontend.

It does **not** belong directly to the VMSS instances.

---

# 13. Azure Load Balancer

Terraform:

```hcl
resource "azurerm_lb" "public" {
  name = "lb-public"
  sku  = "Standard"
}
```

Creates:

```text
lb-public
```

The Load Balancer is responsible for distributing traffic across backend instances.

For example:

```text
                 Load Balancer
                       |
              +--------+--------+
              |                 |
              v                 v
            VM #0             VM #1
```

If VM #0 becomes unhealthy:

```text
                 Load Balancer
                       |
                       X
                    VM #0

                       |
                       v
                    VM #1
```

The Load Balancer can stop sending traffic to the unhealthy instance.

---

# 14. Frontend IP Configuration

Inside the Load Balancer:

```hcl
frontend_ip_configuration {
  name = "frontend-public"

  public_ip_address_id = azurerm_public_ip.load_balancer.id
}
```

The frontend is the **entry point**.

Think of it as:

```text
Public Internet
       |
       v
frontend-public
       |
       v
Load Balancer
```

It uses the public IP:

```text
pip-lb
```

---

# 15. Backend Address Pool

Terraform:

```hcl
resource "azurerm_lb_backend_address_pool" "web" {
  name            = "backend-web"
  loadbalancer_id = azurerm_lb.public.id
}
```

The backend pool contains the servers that will receive traffic.

In our case:

```text
backend-web
     |
     +---- VMSS instance #0
     |
     +---- VMSS instance #1
```

The VMSS network interface configuration adds the instances to this pool:

```hcl
load_balancer_backend_address_pool_ids = [
  azurerm_lb_backend_address_pool.web.id
]
```

---

# 16. Health Probe

Terraform:

```hcl
resource "azurerm_lb_probe" "http" {
  name            = "probe-http"
  loadbalancer_id = azurerm_lb.public.id

  protocol    = "Http"
  port        = 80
  request_path = "/"
}
```

The health probe checks:

```text
VM
 |
 | HTTP GET /
 v
nginx
```

If the VM responds successfully, Azure considers the backend healthy.

Conceptually:

```text
             Health Probe
                  |
       +----------+----------+
       |                     |
       v                     v
     VM #0                 VM #1
    Healthy               Healthy
```

If VM #1 stops responding:

```text
     VM #0                 VM #1
    Healthy              Unhealthy
       ^                     X
       |
       +---- Traffic
```

The Load Balancer will avoid sending new traffic to the unhealthy backend.

---

# 17. Load Balancer Rule

Terraform:

```hcl
resource "azurerm_lb_rule" "http" {
  name = "rule-http"

  frontend_port = 80
  backend_port  = 80

  protocol = "Tcp"
}
```

This defines how traffic should be forwarded.

In our case:

```text
Public IP
    |
    | TCP :80
    v
Load Balancer
    |
    | TCP :80
    v
Backend VM
```

So:

```text
Frontend port 80
        |
        v
Backend port 80
```

This is the rule that connects the public-facing Load Balancer endpoint to the backend servers.

---

# 18. TLS Private Key

Terraform:

```hcl
resource "tls_private_key" "vmss" {
  algorithm = "RSA"
  rsa_bits  = 4096
}
```

Terraform generates an SSH key pair.

There are two parts:

```text
Private key
Public key
```

The public key is placed on the VMSS:

```hcl
admin_ssh_key {
  username   = var.admin_username
  public_key = tls_private_key.vmss.public_key_openssh
}
```

The private key is kept in Terraform state.

### Important

This is acceptable for this learning lab, but **not ideal for production**.

In a real environment, you would normally manage SSH keys separately and avoid storing private keys in Terraform state.

---

# 19. Virtual Machine Scale Set (VMSS)

Terraform:

```hcl
resource "azurerm_linux_virtual_machine_scale_set" "web" {
  name      = "vmss-web"
  instances = 2
}
```

Creates a VM Scale Set containing two Linux VMs.

Conceptually:

```text
vmss-web
   |
   +---- Instance 0
   |
   +---- Instance 1
```

A VM Scale Set is useful when you need multiple similar VMs.

Instead of manually creating:

```text
VM1
VM2
VM3
VM4
...
```

you define:

```text
instances = 2
```

and Azure manages the VM instances as a group.

---

# 20. Why are the VMs in a VMSS?

The Load Balancer needs backend servers.

Therefore:

```text
Load Balancer
      |
      v
Backend Pool
      |
      +---- VMSS Instance 0
      |
      +---- VMSS Instance 1
```

This gives us a realistic load-balancing scenario.

---

# 21. Nginx

The VMSS uses this startup script:

```bash
apt-get update
apt-get install -y nginx
```

This installs the Nginx web server.

Then we create:

```text
/var/www/html/index.html
```

with:

```text
Hello from <hostname>
```

Therefore each VM has a different response.

For example:

```text
VM #0

Hello from vmss-web000000
```

and:

```text
VM #1

Hello from vmss-web000001
```

This makes it easy to see the Load Balancer distributing requests.

---

# 22. Network Interface

Inside the VMSS:

```hcl
network_interface {
  name    = "nic-web"
  primary = true

  ip_configuration {
    name      = "ipconfig-web"
    primary   = true
    subnet_id = azurerm_subnet.backend.id

    load_balancer_backend_address_pool_ids = [
      azurerm_lb_backend_address_pool.web.id
    ]
  }
}
```

This connects the VMSS networking to:

```text
snet-backend
```

and:

```text
backend-web
```

So the VMSS instances are both:

```text
Inside subnet
       +
Inside Load Balancer backend pool
```

---

# 23. Complete Traffic Flow

Now we can understand the entire architecture.

Suppose the Load Balancer public IP is:

```text
20.228.239.125
```

You run:

```bash
curl http://20.228.239.125
```

The request travels like this:

```text
Your Computer
     |
     | HTTP :80
     v
Public IP
20.228.239.125
     |
     v
Load Balancer
lb-public
     |
     | Check backend health
     v
Health Probe
probe-http
     |
     +------------------+
     |                  |
     v                  v
  VMSS #0            VMSS #1
  nginx              nginx
  :80                :80
     |                  |
     +--------+---------+
              |
              v
          Response
```

The NSG sits on the backend subnet:

```text
                    Backend Subnet
                   10.20.1.0/24
                         |
                     nsg-backend
                         |
                +--------+--------+
                |                 |
                v                 v
             VMSS #0           VMSS #1
```

The NSG allows:

```text
Internet
   |
   | TCP 80
   v
Backend subnet
```

and:

```text
Azure Load Balancer
   |
   | TCP/HTTP 80
   v
Backend subnet
```

---

# 24. Terraform Dependency Flow

Terraform automatically understands dependencies through references.

For example:

```hcl
subnet_id = azurerm_subnet.backend.id
```

means:

```text
VMSS
 |
 | requires
 v
Subnet
```

Likewise:

```hcl
backend_address_pool_ids = [
  azurerm_lb_backend_address_pool.web.id
]
```

means:

```text
VMSS
 |
 | requires
 v
Backend Pool
```

Terraform builds the dependency graph automatically.

Conceptually:

```text
Resource Group
      |
      +----------------------+
      |                      |
      v                      v
     VNet                   Public IP
      |                      |
      v                      v
   Subnet                Load Balancer
      |                      |
      v             +--------+--------+
     NSG            |        |        |
      |             v        v        v
      +---------> Backend  Probe    Rule
                    Pool
                      |
                      v
                    VMSS
```

---

# 25. Why `depends_on` is used

The VMSS contains:

```hcl
depends_on = [
  azurerm_subnet_network_security_group_association.backend
]
```

This explicitly tells Terraform:

> Create the NSG association before creating the VMSS.

This is useful because we want the backend subnet's security configuration to exist before the VMSS instances are created.

---

# 26. Deploying the Infrastructure

Initialize Terraform:

```bash
terraform init
```

Format the code:

```bash
terraform fmt
```

Validate the configuration:

```bash
terraform validate
```

Create an execution plan:

```bash
terraform plan
```

Apply the infrastructure:

```bash
terraform apply
```

Terraform will ask for confirmation.

Enter:

```text
yes
```

---

# 27. Get the Load Balancer IP

After deployment:

```bash
terraform output -raw load_balancer_public_ip
```

Example:

```text
20.228.239.125
```

You can also get the URL:

```bash
terraform output -raw load_balancer_url
```

---

# 28. Test the Load Balancer

Run:

```bash
curl http://$(terraform output -raw load_balancer_public_ip)
```

You should see something similar to:

```text
Azure Load Balancer Lab
Served by: vmss-web000000
```

Run it multiple times:

```bash
for i in {1..10}; do
  curl -s http://$(terraform output -raw load_balancer_public_ip)
done
```

You should see responses from both VMSS instances over multiple requests.

---

# 29. Check the VMSS

You can list the VMSS instances:

```bash
az vmss list-instances \
  --resource-group rg-lb-lab \
  --name vmss-web \
  -o table
```

You should see two instances.

---

# 30. Check the NSG

You can verify that Terraform created the NSG rules:

```bash
az network nsg rule list \
  --resource-group rg-lb-lab \
  --nsg-name nsg-backend \
  -o table
```

You should see:

```text
Allow-HTTP-From-Internet
Allow-HTTP-From-AzureLoadBalancer
```

---

# 31. Verify the NSG Association

You can verify that the subnet is associated with the NSG:

```bash
az network vnet subnet show \
  --resource-group rg-lb-lab \
  --vnet-name vnet-lb-lab \
  --name snet-backend \
  --query "networkSecurityGroup.id" \
  -o tsv
```

Terraform should have created this association automatically.

---

# 32. Destroy the Lab

When you're finished practicing:

```bash
terraform destroy
```

Terraform will remove the resources it created.

This is one of the biggest advantages of using Terraform for a lab.

Instead of manually deleting:

```text
Resource Group
VNet
Subnet
NSG
Load Balancer
Public IP
VMSS
```

Terraform knows what it created and can remove it.

---

# 33. Important Azure Concepts Learned

This small project teaches several fundamental Azure concepts:

### Resource Group

Logical container for Azure resources.

```text
rg-lb-lab
```

### VNet

Private Azure network.

```text
10.20.0.0/16
```

### Subnet

Smaller network inside the VNet.

```text
10.20.1.0/24
```

### NSG

Network firewall/security rules.

```text
Allow TCP 80
```

### Public IP

Internet-facing IP address.

```text
20.x.x.x
```

### Load Balancer

Distributes traffic between backend servers.

### Backend Pool

Collection of servers receiving Load Balancer traffic.

### Health Probe

Determines whether a backend server is healthy.

### Load Balancer Rule

Defines how frontend traffic is mapped to backend traffic.

```text
Frontend :80
     |
     v
Backend :80
```

### VMSS

Group of similar VMs managed as a scale set.

### Nginx

Web server running on the VMSS instances.

---

# 34. The Most Important Mental Model

If you're new to Azure, remember this simplified model:

```text
RESOURCE GROUP
     |
     +--- VNET
           |
           +--- SUBNET
                 |
                 +--- NSG
                 |
                 +--- VMSS
                       |
                       +--- VM
                       +--- VM


INTERNET
    |
    v
PUBLIC IP
    |
    v
LOAD BALANCER
    |
    v
BACKEND POOL
    |
    +-------- VM
    |
    +-------- VM
```

The key distinction is:

```text
VNet/Subnet
    =
Where the machines live

NSG
    =
Who is allowed to communicate

Public IP
    =
How something can be reached from the Internet

Load Balancer
    =
Where incoming traffic is distributed

Backend Pool
    =
Which machines receive the traffic

Health Probe
    =
Which machines are healthy

VMSS
    =
The machines themselves
```

Once this mental model is clear, Azure networking becomes much easier to understand.

---

# 35. Why Terraform is useful here

Without Terraform, you could create these resources manually through the Azure Portal.

But then you have to remember:

```text
Create Resource Group
Create VNet
Create Subnet
Create NSG
Create NSG rules
Associate NSG with subnet
Create Public IP
Create Load Balancer
Create Backend Pool
Create Health Probe
Create LB Rule
Create VMSS
Configure networking
Install nginx
```

With Terraform, the infrastructure is described as code.

You can recreate the entire environment with:

```bash
terraform apply
```

And remove it with:

```bash
terraform destroy
```

More importantly, the configuration is **repeatable**.

If you destroy the environment and run:

```bash
terraform apply
```

again, Terraform creates the same architecture without requiring manual Azure CLI fixes.

---

# 36. Key Terraform Principle

The most important lesson from this lab is:

> **Terraform should be the source of truth for infrastructure.**

For example, don't do this:

```text
Terraform
   |
   +-- Creates subnet
   |
   +-- Creates NSG
```

and then manually do:

```bash
az network vnet subnet update ...
```

Instead, describe the relationship in Terraform:

```hcl
resource "azurerm_subnet_network_security_group_association" "backend" {
  subnet_id                 = azurerm_subnet.backend.id
  network_security_group_id = azurerm_network_security_group.backend.id
}
```

Then Terraform knows:

```text
Subnet
  |
  +--- NSG association
```

This prevents configuration drift and makes the environment reproducible.

---

# 37. Cleanup

To delete everything created by this project:

```bash
terraform destroy
```

Verify that the resource group no longer exists:

```bash
az group exists --name rg-lb-lab
```

Expected:

```text
false
```

---

## Summary

This project creates a complete but simple Azure web application architecture:

```text
                   INTERNET
                       |
                       v
                 +-----------+
                 | Public IP |
                 +-----+-----+
                       |
                       v
              +----------------+
              | Load Balancer  |
              +-------+--------+
                      |
                Backend Pool
                      |
              +-------+--------+
              |                |
              v                v
           VMSS #0          VMSS #1
           nginx            nginx
              |                |
              +-------+--------+
                      |
                 Backend Subnet
                   10.20.1.0/24
                      |
                     NSG
```

The entire environment is managed by Terraform, including networking, security, load balancing, VMSS, and the web server configuration.

The lab therefore gives you a practical introduction to the relationship between:

**Azure Networking → Security → Load Balancing → VM Scale Sets → Terraform.**