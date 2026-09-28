#!/usr/bin/env bash
# Assert what Azure (and Terraform) should look like at each phase.
#   tests/verify.sh manual     after scripts/01-manual-create.sh
#   tests/verify.sh imported   after stage 02 apply
#   tests/verify.sh modified   after stage 03 apply
#   tests/verify.sh drift      after a hand-made change (expects plan to see it)
set -uo pipefail
cd "$(dirname "$0")/.."
source .lab.env
phase="${1:?usage: $0 manual|imported|modified|drift}"

pass=0; fail=0
check() { # check "description" "actual" "expected"
  if [[ "$2" == "$3" ]]; then echo "  PASS  $1"; pass=$((pass+1))
  else echo "  FAIL  $1  (got '$2', want '$3')"; fail=$((fail+1)); fi
}
q() { az "$@" -o tsv 2>/dev/null; }

# Terraform plan exit codes with -detailed-exitcode: 0 = no diff, 2 = diff, 1 = error
plan_code() { terraform -chdir=tf plan -detailed-exitcode -input=false -lock=false >/dev/null 2>&1; echo $?; }
in_state()  { terraform -chdir=tf state list 2>/dev/null | grep -qx "$1" && echo yes || echo no; }

echo "== common: identity + data survive every phase =="
check "storage account creationTime unchanged (never recreated)" \
  "$(q storage account show -n "$SA" -g "$RG" --query creationTime)" "$SA_CREATED"
check "vnet resourceGuid unchanged (never recreated)" \
  "$(q network vnet show -n vnet-import-lab -g "$RG" --query resourceGuid)" "$VNET_GUID"
check "app data readable" "$(program/app.sh check >/dev/null 2>&1 && echo ok || echo broken)" "ok"
check "subnet has NSG attached" \
  "$(q network vnet subnet show -g "$RG" --vnet-name vnet-import-lab -n snet-app --query 'networkSecurityGroup.id' | awk -F/ '{print $NF}')" "nsg-import-lab"

case "$phase" in
  manual)
    echo "== manual: exists in Azure, unknown to Terraform =="
    check "rg tag owner" "$(q group show -n "$RG" --query tags.owner)" "manual"
    check "ssh rule source" "$(q network nsg rule show -g "$RG" --nsg-name nsg-import-lab -n allow-ssh --query sourceAddressPrefix)" "203.0.113.0/24"
    check "storage account not in state" "$(in_state azurerm_storage_account.lab)" "no"
    ;;
  imported)
    echo "== imported: in state, config == reality, nothing changed in Azure =="
    for addr in azurerm_resource_group.lab azurerm_storage_account.lab azurerm_storage_container.appdata \
                azurerm_network_security_group.lab azurerm_network_security_rule.allow_ssh \
                azurerm_virtual_network.lab azurerm_subnet.app azurerm_subnet_network_security_group_association.app; do
      check "in state: $addr" "$(in_state "$addr")" "yes"
    done
    check "rg tag owner still manual" "$(q group show -n "$RG" --query tags.owner)" "manual"
    check "ssh rule source untouched" "$(q network nsg rule show -g "$RG" --nsg-name nsg-import-lab -n allow-ssh --query sourceAddressPrefix)" "203.0.113.0/24"
    check "terraform plan is clean (exit 0)" "$(plan_code)" "0"
    ;;
  modified)
    echo "== modified: Terraform changed things in place =="
    check "rg tag managed_by" "$(q group show -n "$RG" --query tags.managed_by)" "terraform"
    check "storage tag owner" "$(q storage account show -n "$SA" -g "$RG" --query tags.owner)" "platform-team"
    check "blob versioning on" "$(q storage account blob-service-properties show -n "$SA" -g "$RG" --query isVersioningEnabled)" "true"
    check "blob soft delete 7d" "$(q storage account blob-service-properties show -n "$SA" -g "$RG" --query deleteRetentionPolicy.days)" "7"
    check "ssh rule source tightened" "$(q network nsg rule show -g "$RG" --nsg-name nsg-import-lab -n allow-ssh --query sourceAddressPrefix)" "198.51.100.0/24"
    check "https rule created" "$(q network nsg rule show -g "$RG" --nsg-name nsg-import-lab -n allow-https --query destinationPortRange)" "443"
    check "snet-app service endpoint" "$(q network vnet subnet show -g "$RG" --vnet-name vnet-import-lab -n snet-app --query 'serviceEndpoints[0].service')" "Microsoft.Storage"
    check "snet-data created" "$(q network vnet subnet show -g "$RG" --vnet-name vnet-import-lab -n snet-data --query addressPrefix)" "10.50.2.0/24"
    check "terraform plan is clean (exit 0)" "$(plan_code)" "0"
    ;;
  drift)
    echo "== drift: someone changed Azure by hand; Terraform must notice =="
    check "terraform plan shows a diff (exit 2)" "$(plan_code)" "2"
    ;;
  *) echo "unknown phase $phase"; exit 2 ;;
esac

echo
echo "$pass passed, $fail failed"
[[ $fail -eq 0 ]]
