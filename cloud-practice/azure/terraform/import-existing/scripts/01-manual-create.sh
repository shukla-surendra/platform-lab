#!/usr/bin/env bash
# Phase 1 -- create resources BY HAND (az CLI), the way a colleague might have
# clicked them together in the portal before anyone thought about Terraform.
#
# Creates:
#   rg-import-lab                       resource group
#   stimport<suffix>                    storage account (StorageV2, LRS, Hot)
#     └─ appdata                        private blob container
#   vnet-import-lab (10.50.0.0/16)      virtual network
#     └─ snet-app (10.50.1.0/24)        subnet, NSG attached
#   nsg-import-lab                      network security group
#     └─ allow-ssh (inbound 22 from 203.0.113.0/24)
#
# Writes ../.lab.env (names + original creation timestamps) and
# ../tf/terraform.tfvars so Terraform knows what to import.
set -euo pipefail
cd "$(dirname "$0")/.."

LOCATION="${LOCATION:-centralindia}"
RG="rg-import-lab"

if [[ -f .lab.env ]]; then
  echo ".lab.env already exists -- resources were already created. Run scripts/99-cleanup.sh first to start over."
  exit 1
fi

SUFFIX="$(openssl rand -hex 3)"
SA="stimport${SUFFIX}"
SUB_ID="$(az account show --query id -o tsv)"

echo "==> Resource group $RG ($LOCATION)"
az group create -n "$RG" -l "$LOCATION" --tags env=lab owner=manual -o none

echo "==> Storage account $SA"
az storage account create -n "$SA" -g "$RG" -l "$LOCATION" \
  --sku Standard_LRS --kind StorageV2 --access-tier Hot \
  --min-tls-version TLS1_2 --allow-blob-public-access false \
  --https-only true \
  --tags env=lab owner=manual -o none

echo "==> Blob container appdata (control-plane create, no keys needed)"
az storage container-rm create --storage-account "$SA" -g "$RG" \
  -n appdata --public-access off -o none

echo "==> NSG + rule"
az network nsg create -n nsg-import-lab -g "$RG" -l "$LOCATION" \
  --tags env=lab owner=manual -o none
az network nsg rule create --nsg-name nsg-import-lab -g "$RG" -n allow-ssh \
  --priority 100 --direction Inbound --access Allow --protocol Tcp \
  --source-address-prefixes 203.0.113.0/24 --source-port-ranges '*' \
  --destination-address-prefixes '*' --destination-port-ranges 22 -o none

echo "==> VNet + subnet (NSG attached)"
az network vnet create -n vnet-import-lab -g "$RG" -l "$LOCATION" \
  --address-prefixes 10.50.0.0/16 \
  --subnet-name snet-app --subnet-prefixes 10.50.1.0/24 \
  --tags env=lab owner=manual -o none
az network vnet subnet update -g "$RG" --vnet-name vnet-import-lab -n snet-app \
  --network-security-group nsg-import-lab -o none

# The storage account's creationTime never changes for the life of the
# resource -- if Terraform ever destroys+recreates it, this value changes.
SA_CREATED="$(az storage account show -n "$SA" -g "$RG" --query creationTime -o tsv)"
VNET_GUID="$(az network vnet show -n vnet-import-lab -g "$RG" --query resourceGuid -o tsv)"

cat > .lab.env <<EOF
SUB_ID=$SUB_ID
RG=$RG
LOCATION=$LOCATION
SA=$SA
SA_CREATED=$SA_CREATED
VNET_GUID=$VNET_GUID
EOF

cat > tf/terraform.tfvars <<EOF
subscription_id      = "$SUB_ID"
location             = "$LOCATION"
storage_account_name = "$SA"
EOF

echo
echo "Done. Saved to .lab.env:"
cat .lab.env
echo
echo "Next: program/app.sh write    (put real data in the account)"
echo "      tests/verify.sh manual"
