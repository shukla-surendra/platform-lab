# 03 — EC2 with workspaces

One `main.tf`, one EC2 instance **per workspace**. No tfvars files here: the per-env
settings sit in a `locals.settings` map and `terraform.workspace` picks the entry.

| workspace | instance | disk | resulting name |
|---|---|---|---|
| dev  | t3.micro | 8 GB  | wsdemo-dev-app  |
| qa   | t3.micro | 8 GB  | wsdemo-qa-app   |
| prod | t3.small | 20 GB | wsdemo-prod-app |

## Run it

```bash
cd 03-ec2
terraform init
terraform workspace new dev          # create + switch
terraform plan                       # Plan: 3 to add (sg, egress rule, instance)
terraform apply

terraform workspace new prod
terraform plan                       # again "3 to add": prod state is empty
terraform apply

terraform workspace list             # dev, prod (* = current)
aws ec2 describe-instances \
  --filters "Name=tag:Name,Values=wsdemo-*-app" "Name=instance-state-name,Values=running" \
  --query "Reservations[].Instances[].[Tags[?Key=='Name']|[0].Value,InstanceType]" --output text
```

Expected: `wsdemo-dev-app t3.micro` and `wsdemo-prod-app t3.small`.

## Things to try
- `terraform workspace select dev && terraform destroy` removes only dev's instance.
- `terraform workspace select default && terraform plan` errors with "Invalid index" (no `default` key in the map),
  which protects you from deploying into an unnamed workspace.
- Edit `prod`'s `instance_type`, then `plan` in `dev` (no change) and in `prod` (in-place change).

## Clean up (instances cost money)
```bash
for e in dev prod; do terraform workspace select $e && terraform destroy -auto-approve; done
```
