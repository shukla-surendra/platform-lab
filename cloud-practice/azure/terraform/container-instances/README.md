# Terraform: Azure Container Instances (minimal)

RG + one Container Group running Microsoft's own `aci-helloworld` demo
image on a public IP + DNS label. This is Azure's "just run a container,
no cluster" service -- the lightweight alternative to AKS when you don't
need orchestration (scheduling, self-healing, multi-node bin-packing)
across more than one container.

> ⚠️ **This creates billable resources**, billed per-second while the
> container group is running (vCPU + GB-seconds), not per-month like a VM.
> Cheap for a quick test, adds up if left running. Run `terraform destroy`
> when done.

## Usage

```bash
terraform init
terraform apply
curl http://$(terraform output -raw fqdn)
```

## What's deliberately not here

No VNet integration (this uses ACI's default public networking, not a
private subnet), no multi-container group (sidecar pattern), no restart
policy override (defaults to `Always`), no volume mounts, no managed
identity.

## Teardown

```bash
terraform destroy
```
