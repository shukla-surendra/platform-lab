#!/usr/bin/env bash
# A tiny "application" that uses the storage account as its datastore.
# It stands in for a real workload whose data must survive Terraform adopting
# (importing) and then modifying the infrastructure underneath it.
#
#   app.sh write   -- write orders/order-<n>.json and bump a counter blob
#   app.sh read    -- list every order and print the counter
#   app.sh check   -- exit 0 if the counter blob exists and all orders are readable
set -euo pipefail
cd "$(dirname "$0")/.."
source .lab.env

CONTAINER=appdata
# Data-plane calls use the account key (fetched by az on our behalf), so this
# works without granting yourself a Storage Blob Data role.
az_blob() { az storage blob "$@" --account-name "$SA" --container-name "$CONTAINER" --auth-mode key --only-show-errors; }

# az can't download to /dev/stdout, so go via a temp file.
fetch() {
  local tmp; tmp="$(mktemp)"
  az_blob download --name "$1" --file "$tmp" --no-progress -o none 2>/dev/null && cat "$tmp"
  local rc=$?; rm -f "$tmp"; return $rc
}

counter() { fetch counter.txt || echo 0; }

case "${1:-}" in
  write)
    n=$(( $(counter) + 1 ))
    tmp="$(mktemp)"
    printf '{"order": %d, "item": "widget-%d", "written_at": "%s"}\n' "$n" "$n" "$(date -u +%FT%TZ)" >"$tmp"
    az_blob upload --name "orders/order-$n.json" --file "$tmp" --overwrite --no-progress -o none
    echo "$n" >"$tmp"
    az_blob upload --name counter.txt --file "$tmp" --overwrite --no-progress -o none
    rm -f "$tmp"
    echo "wrote order $n"
    ;;
  read)
    echo "counter = $(counter)"
    for b in $(az_blob list --prefix orders/ --query '[].name' -o tsv); do
      fetch "$b"
    done
    ;;
  check)
    n=$(counter)
    [[ "$n" -ge 1 ]] || { echo "no data found"; exit 1; }
    found=$(az_blob list --prefix orders/ --query 'length(@)' -o tsv)
    [[ "$found" -eq "$n" ]] || { echo "counter=$n but $found orders"; exit 1; }
    echo "data intact: $n orders"
    ;;
  *) echo "usage: $0 write|read|check"; exit 2 ;;
esac
