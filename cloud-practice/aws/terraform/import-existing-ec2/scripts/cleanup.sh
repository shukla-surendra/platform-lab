#!/usr/bin/env bash
# Tears down the practice instance + security group + Elastic IP AND
# removes them from Terraform state, leaving nothing behind. Run this
# yourself; it is not run for you.
#
# Usage: ./cleanup.sh <instance-id> <security-group-id> <eip-allocation-id> [region]
set -euo pipefail

INSTANCE_ID="${1:?Usage: $0 <instance-id> <security-group-id> <eip-allocation-id> [region]}"
SG_ID="${2:?Usage: $0 <instance-id> <security-group-id> <eip-allocation-id> [region]}"
EIP_ALLOC_ID="${3:?Usage: $0 <instance-id> <security-group-id> <eip-allocation-id> [region]}"
REGION="${4:-us-east-1}"

echo "Removing resources from Terraform state (state only, AWS untouched)..."
terraform -chdir="$(dirname "$0")/.." state rm aws_instance.imported || true
terraform -chdir="$(dirname "$0")/.." state rm aws_security_group.imported || true
terraform -chdir="$(dirname "$0")/.." state rm aws_eip.imported || true

echo "Releasing Elastic IP $EIP_ALLOC_ID ..."
aws ec2 disassociate-address --region "$REGION" --allocation-id "$EIP_ALLOC_ID" || true
aws ec2 release-address --region "$REGION" --allocation-id "$EIP_ALLOC_ID"

echo "Terminating $INSTANCE_ID ..."
aws ec2 terminate-instances --region "$REGION" --instance-ids "$INSTANCE_ID" >/dev/null
aws ec2 wait instance-terminated --region "$REGION" --instance-ids "$INSTANCE_ID"

echo "Deleting security group $SG_ID ..."
aws ec2 delete-security-group --region "$REGION" --group-id "$SG_ID"

echo "Done. Instance terminated, EIP released, security group deleted, Terraform state clean."
