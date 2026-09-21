# vpc-multi-subnet

A standalone VPC module: one public subnet and one private subnet per AZ
(2 AZs by default -> 2 public + 2 private subnets; add AZs for more of each).

- Public subnets route to the internet via an Internet Gateway and auto-assign
  public IPs.
- Private subnets have no direct internet route; they reach the internet
  outbound-only via NAT Gateway(s) sitting in the public subnets.
- `single_nat_gateway = true` (default) shares one NAT Gateway across all AZs
  (cheap, single point of failure). Set to `false` for one NAT GW per AZ (HA,
  no cross-AZ NAT data charges, but more $).

## Usage

```bash
cp terraform.tfvars.example terraform.tfvars
# edit terraform.tfvars as needed
terraform init
terraform plan
# terraform apply   # not run here — review the plan first
```

## Layout

| File | Purpose |
|---|---|
| `main.tf` | VPC, IGW, subnets, NAT Gateway(s), route tables/associations |
| `variables.tf` | Inputs (region, CIDR, AZs, NAT strategy, tags) |
| `outputs.tf` | VPC ID, subnet IDs/CIDRs, NAT GW IDs, route table IDs |
| `versions.tf` | Terraform + AWS provider version pins |
| `terraform.tfvars.example` | Example variable values |

This module was not applied/deployed — files only.
