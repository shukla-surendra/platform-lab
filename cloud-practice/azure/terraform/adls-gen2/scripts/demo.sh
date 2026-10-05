#!/usr/bin/env bash
# Walk-through + checks for the ADLS Gen2 project. Run AFTER `terraform apply`.
#   ./scripts/demo.sh                 # uses Entra ID login (RBAC)
#   AUTH=key ./scripts/demo.sh        # uses the account key instead
#
# With AUTH=login the role assignment (Storage Blob Data Owner) can take a few
# minutes to propagate after apply; if you get "AuthorizationPermissionMismatch",
# wait and retry, or use AUTH=key.
set -uo pipefail
cd "$(dirname "$0")/.."

AUTH="${AUTH:-login}"
ACCOUNT=$(terraform output -raw storage_account_name)
RG=rg-adls-gen2-demo
PASS=0; FAIL=0

ok()   { printf 'PASS  %s\n' "$1"; PASS=$((PASS+1)); }
bad()  { printf 'FAIL  %s\n' "$1"; FAIL=$((FAIL+1)); }
step() { printf '\n== %s\n' "$1"; }
fs()   { az storage fs "$@" --account-name "$ACCOUNT" --auth-mode "$AUTH" 2>&1; }

echo "account: $ACCOUNT   auth: $AUTH"

step "1. It is a data lake: hierarchical namespace enabled?"
hns=$(az storage account show -n "$ACCOUNT" -g "$RG" --query isHnsEnabled -o tsv)
[ "$hns" = "true" ] && ok "isHnsEnabled = true" || bad "isHnsEnabled = $hns"

step "2. Filesystems (the medallion layers)"
out=$(fs list --query '[].name' -o tsv)
echo "$out"
for l in bronze silver gold; do echo "$out" | grep -qx "$l" && ok "filesystem '$l' exists" || bad "filesystem '$l' missing"; done

step "3. Directories created by Terraform"
out=$(fs directory list -f bronze --path raw --query '[].name' -o tsv); echo "$out"
echo "$out" | grep -q 'raw/sales' && ok "bronze/raw/sales exists" || bad "bronze/raw/sales missing"

step "4. Upload a sample file into bronze/raw/sales"
tmp=$(mktemp); trap 'rm -f "$tmp" "$tmp.down"' EXIT
printf 'order_id,customer,amount,order_date\n1001,alice,25.50,2026-10-01\n1002,bob,13.00,2026-10-01\n1003,carol,99.99,2026-10-02\n' > "$tmp"
fs file upload -f bronze -s "$tmp" -p raw/sales/sales_sample.csv --overwrite true -o none \
  && ok "uploaded raw/sales/sales_sample.csv" || bad "upload failed"

step "5. Read it back"
fs file download -f bronze -p raw/sales/sales_sample.csv -d "$tmp.down" --overwrite true -o none
if [ -f "$tmp.down" ] && diff -q "$tmp" "$tmp.down" >/dev/null; then ok "downloaded content identical"; else bad "download mismatch"; fi
cat "$tmp.down" 2>/dev/null

step "6. Hierarchical namespace in action: atomic directory rename"
echo "(on plain Blob storage a 'rename' copies+deletes every blob; here it is one metadata operation)"
fs directory move -f bronze -n raw/customers -d bronze/raw/customers_renamed -o none \
  && ok "moved raw/customers -> raw/customers_renamed" || bad "rename failed"
fs directory move -f bronze -n raw/customers_renamed -d bronze/raw/customers -o none \
  && ok "moved it back" || bad "rename back failed"

step "7. Same data through the Blob endpoint (multi-protocol access)"
n=$(az storage blob list -c bronze --prefix raw/sales --account-name "$ACCOUNT" --auth-mode "$AUTH" --query 'length(@)' -o tsv 2>&1)
[ "${n:-0}" -ge 1 ] 2>/dev/null && ok "blob API lists the file written through the DFS API ($n blob)" || bad "blob list: $n"

step "8. ACL on gold/reports (shows owner/group/other, plus entries if a reader was configured)"
fs access show -f gold -p reports --query acl -o tsv

step "9. Where to use it from Spark / Delta / Synapse"
terraform output abfss_uris

echo; echo "----"; echo "passed: $PASS  failed: $FAIL"
[ "$FAIL" -eq 0 ]
