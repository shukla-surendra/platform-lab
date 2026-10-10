# 04 — same EC2 code, state in S3

The only change from `03-ec2` is the `backend "s3"` block at the top of `main.tf`.

Terraform picks the state path from the workspace automatically:

| workspace | state object |
|---|---|
| dev  | `s3://BUCKET/env/dev/ec2/terraform.tfstate` |
| qa   | `s3://BUCKET/env/qa/ec2/terraform.tfstate` |
| default | `s3://BUCKET/ec2/terraform.tfstate` |

## Run it

```bash
# first run ../04a-create-s3-backend (creates the bucket)
# put the bucket name from 04a (terraform output bucket_name) into main.tf, then:
terraform init
terraform workspace new dev && terraform apply
terraform workspace new qa  && terraform apply
aws s3 ls s3://<bucket-from-04a>/ --recursive     # see env/dev/... and env/qa/...
```

More detail: [`../CONCEPTS.md`](../CONCEPTS.md).
