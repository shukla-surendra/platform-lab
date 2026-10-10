#!/usr/bin/env bash
# Destroy the resources in EVERY Terraform workspace of this folder, then delete
# the (now empty) workspaces. The S3 bucket itself is not managed here, so it is untouched.
#
# Usage:
#   ./destroy-all.sh        # asks for confirmation first
#   ./destroy-all.sh --yes  # no prompt
set -euo pipefail

cd "$(dirname "$0")"

terraform init -input=false >/dev/null

# `terraform workspace list` marks the current one with '*'; strip that and blanks
workspaces=$(terraform workspace list | sed 's/^[* ]*//' | grep -v '^$')

# "default" can't be deleted and holds no resources here (main.tf only defines dev/qa/prod)
targets=$(echo "$workspaces" | grep -vx 'default' || true)

if [ -z "$targets" ]; then
  echo "No non-default workspaces found. Nothing to destroy."
  exit 0
fi

echo "This will DESTROY all resources in these workspaces:"
echo "$targets" | sed 's/^/  - /'

if [ "${1:-}" != "--yes" ]; then
  read -r -p "Type 'destroy' to continue: " answer
  [ "$answer" = "destroy" ] || { echo "Aborted."; exit 1; }
fi

for ws in $targets; do
  echo
  echo "=== Workspace: $ws ==="
  terraform workspace select "$ws"
  terraform destroy -auto-approve -input=false

  # Can't delete the workspace we're standing in
  terraform workspace select default
  terraform workspace delete "$ws"
done

echo
echo "Done. All workspaces destroyed and removed."
