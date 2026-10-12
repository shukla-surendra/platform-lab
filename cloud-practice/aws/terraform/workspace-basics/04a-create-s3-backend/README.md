# 04a — create the S3 bucket for Terraform state

Run this **before** `../04-ec2-s3-backend`. It creates one private, versioned,
encrypted bucket named `tfstate-<account-id>-us-east-1`.

```bash
terraform init
terraform apply          # 5 resources, cost ~ $0
terraform output bucket_name
```

Copy that name into `bucket = "..."` in `../04-ec2-s3-backend/main.tf`.

This folder uses **local state** (a bucket can't store its own state before it exists).
Keep it, and don't destroy the bucket while 04's workspaces still exist.

## Or without Terraform: the shell script

```bash
./create-bucket.sh
```
Creates the same bucket (versioned, encrypted, private) with the AWS CLI, is safe to re-run,
and fills in the bucket name in `../04-ec2-s3-backend/main.tf` for you.
Use either the script or `terraform apply`, not both: Terraform would try to create a bucket that exists.
