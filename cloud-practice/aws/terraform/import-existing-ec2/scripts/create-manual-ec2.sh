#!/usr/bin/env bash
# Simulates "infrastructure that already exists" by creating a security
# group + EC2 instance with the AWS CLI -- i.e. NOT through Terraform --
# so you have something real to practice importing. Run this yourself; it
# is not run for you. Launches a t3.micro (Free-Tier eligible in most
# accounts) into the account's default VPC.
#
# Usage: ./create-manual-ec2.sh [availability-zone] [region]
set -euo pipefail

AZ="${1:-us-east-1a}"
REGION="${2:-us-east-1}"
NAME="import-practice-ec2"

echo "Looking up default VPC / subnet in $AZ ..."
VPC_ID=$(aws ec2 describe-vpcs --region "$REGION" \
  --filters Name=is-default,Values=true \
  --query 'Vpcs[0].VpcId' --output text)

SUBNET_ID=$(aws ec2 describe-subnets --region "$REGION" \
  --filters Name=vpc-id,Values="$VPC_ID" Name=availability-zone,Values="$AZ" \
  --query 'Subnets[0].SubnetId' --output text)

echo "Looking up latest Amazon Linux 2023 AMI ..."
AMI_ID=$(aws ssm get-parameters --region "$REGION" \
  --names /aws/service/ami-amazon-linux-latest/al2023-ami-kernel-default-x86_64 \
  --query 'Parameters[0].Value' --output text)

echo "Creating security group ..."
SG_ID=$(aws ec2 create-security-group --region "$REGION" \
  --group-name "${NAME}-sg" \
  --description "Manually-created SG for the terraform import practice module" \
  --vpc-id "$VPC_ID" \
  --query 'GroupId' --output text)

aws ec2 authorize-security-group-ingress --region "$REGION" \
  --group-id "$SG_ID" \
  --protocol tcp --port 22 --cidr 0.0.0.0/0 >/dev/null

echo "Launching instance ..."
INSTANCE_ID=$(aws ec2 run-instances --region "$REGION" \
  --image-id "$AMI_ID" \
  --instance-type t3.micro \
  --subnet-id "$SUBNET_ID" \
  --security-group-ids "$SG_ID" \
  --tag-specifications "ResourceType=instance,Tags=[{Key=Name,Value=$NAME}]" \
  --query 'Instances[0].InstanceId' --output text)

echo "Waiting for the instance to reach 'running' ..."
aws ec2 wait instance-running --region "$REGION" --instance-ids "$INSTANCE_ID"

PRIVATE_IP=$(aws ec2 describe-instances --region "$REGION" \
  --instance-ids "$INSTANCE_ID" \
  --query 'Reservations[0].Instances[0].PrivateIpAddress' --output text)

echo "Allocating + associating an Elastic IP (this is what makes the public IP durable) ..."
EIP_ALLOC_ID=$(aws ec2 allocate-address --region "$REGION" \
  --domain vpc --query 'AllocationId' --output text)

aws ec2 associate-address --region "$REGION" \
  --instance-id "$INSTANCE_ID" --allocation-id "$EIP_ALLOC_ID" >/dev/null

EIP_PUBLIC_IP=$(aws ec2 describe-addresses --region "$REGION" \
  --allocation-ids "$EIP_ALLOC_ID" --query 'Addresses[0].PublicIp' --output text)

cat <<EOF

Created (NOT tracked by Terraform yet):
  instance_id        = "$INSTANCE_ID"
  security_group_id  = "$SG_ID"
  ami_id             = "$AMI_ID"
  private_ip         = "$PRIVATE_IP"
  eip_allocation_id  = "$EIP_ALLOC_ID"
  elastic_ip         = "$EIP_PUBLIC_IP"
  availability_zone  = "$AZ"

Next: paste these into terraform.tfvars, then follow README.md.
EOF
