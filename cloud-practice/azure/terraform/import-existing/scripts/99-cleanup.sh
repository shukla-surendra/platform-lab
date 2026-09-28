#!/usr/bin/env bash
# Tear everything down. We delete the resource group with az rather than
# `terraform destroy` because stage 03 sets prevent_destroy on the storage
# account (which is the point -- Terraform refuses to delete it).
set -euo pipefail
cd "$(dirname "$0")/.."
source .lab.env 2>/dev/null || RG=rg-import-lab

echo "Deleting resource group $RG (async)..."
az group delete -n "$RG" --yes --no-wait
rm -f .lab.env tf/terraform.tfvars tf/terraform.tfstate tf/terraform.tfstate.backup \
      tf/main.tf tf/imports.tf tf/generated.tf tf/tfplan
echo "Local state removed. 'az group show -n $RG' will 404 once deletion finishes."
