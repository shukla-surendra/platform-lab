# Why AKS creates a load balancer with the cluster and EKS doesn't

Observation: a new AKS cluster comes with a load balancer; this EKS cluster has **none**.
Checked in this account (us-east-1): no ALB/NLB, no Classic LB, no NAT gateway. The two nodes have public IPs. (Azure side described from general knowledge; verify in your own AKS resource group.)

## Short answer

That AKS load balancer is mostly **not for incoming traffic**. By default AKS uses a Standard Load Balancer (usually named `kubernetes`, plus a public IP) to give nodes **outbound internet access** (SNAT). EKS nodes in public subnets reach the internet directly through the internet gateway, so no balancer is needed. Incoming-traffic load balancers appear in **both** only when you create a Service/Ingress that asks for one.

## Where each one comes from

| | AKS | EKS (this lab) |
|---|---|---|
| Extra resources at cluster creation | A managed resource group (`MC_...`) with VM scale set, VNet, NSG, **Standard Load Balancer + public IP** | None beyond what you defined: VPC, subnets, IGW, roles, control plane, node group |
| Who creates them | Azure, automatically, outside your Terraform | You, explicitly, in Terraform (`01_network.tf`...) |
| Default outbound path | Load balancer SNAT (`outboundType = loadBalancer`) | Node public IP -> internet gateway (public subnets) |
| Alternatives for outbound | NAT gateway, user-defined routing | NAT gateway in a private-subnet design |
| Inbound traffic | Load balancer rules appear when you create a `LoadBalancer` Service | A load balancer is created when you create a `LoadBalancer` Service / Ingress |
| Control plane endpoint | Hidden, run by Azure | Hidden, run by AWS (you never see its load balancer/NLB) |

## Why the designs differ

- **AKS is more "batteries included"**: networking, NSG and the outbound load balancer are provisioned for you in a managed resource group, so the cluster works with zero network setup.
- **EKS is "bring your own network"**: you supply VPC and subnets; AWS creates only the cluster (and ENIs in your subnets). Nothing else exists until you add it.
- Outbound in AKS is solved with the load balancer; in EKS it is solved by your own routing (IGW or NAT).

## Contrast in practice

- Hidden cost: the AKS Standard Load Balancer and public IP are billed (small), you didn't ask for them. In EKS you pay only for what you declared. Careful: **a NAT gateway (the production EKS equivalent) costs ~$33/month each**, far more than the AKS outbound load balancer. This lab avoided it by using public subnets.
- Cleanup: in AKS the `MC_` resource group is deleted with the cluster. In EKS, load balancers created *by Kubernetes Services* are NOT in Terraform and must be deleted first, or `terraform destroy` hangs on the VPC.
- Visibility: AKS surprises you with extra resources; EKS surprises you later (a Service of type `LoadBalancer` silently creates an AWS load balancer).

## When an EKS load balancer appears

| You create | AWS creates |
|---|---|
| Service `type: LoadBalancer` (plain) | Classic Load Balancer |
| Service with AWS Load Balancer Controller annotations | NLB |
| Ingress with AWS Load Balancer Controller | ALB |
| Private-subnet nodes needing internet | NAT gateway (you add it in Terraform) |

See `ACCESSING_THE_APP.md` for the access options in this lab.
