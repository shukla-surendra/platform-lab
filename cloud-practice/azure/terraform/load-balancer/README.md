# Terraform: Azure Load Balancer (minimal)

RG + VNet/subnet + a Standard Load Balancer (public frontend IP, backend
pool, TCP health probe, port-80 rule) + a 2-instance Linux VM Scale Set
in that backend pool, each instance running nginx with a
hostname-stamped `index.html`. Unlike the other projects here, this one
deliberately pairs the LB with real compute -- an LB with nothing behind
it has nothing to route to and nothing to observe.

> ⚠️ **This creates billable resources** -- two `Standard_B1s` VM
> instances plus a Standard Load Balancer and Standard public IP, all
> billed while running. The most expensive project in this folder to
> leave up by mistake. Run `terraform destroy` when done.

## Usage

```bash
terraform init
terraform apply
```

Prove it's actually load-balancing (run a few times, watch the hostname change):

```bash
for i in 1 2 3 4; do curl -s http://$(terraform output -raw load_balancer_ip); echo; done
```

(Give the VMSS instances a couple of minutes to finish `apt-get install
nginx` via `custom_data` before the first request succeeds.)

## What's deliberately not here

TCP health probe instead of HTTP (simpler, doesn't check response status
-- an HTTP probe checking a specific path/code is the more realistic
choice for a real web backend), no autoscale rules on the scale set (a
fixed `instances = 2`), no NSG (the subnet has no explicit one -- fine
for a demo, not for anything real), no zone redundancy.

## Teardown

```bash
terraform destroy
```
