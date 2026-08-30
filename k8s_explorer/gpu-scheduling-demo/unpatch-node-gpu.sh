#!/usr/bin/env bash
set -euo pipefail
NODE="${1:-minikube-m03}"
kubectl patch node "$NODE" --subresource=status --type='json' -p \
  '[{"op": "remove", "path": "/status/capacity/example.com~1toygpu"}, {"op": "remove", "path": "/status/allocatable/example.com~1toygpu"}]'
echo "Removed example.com/toygpu from $NODE."
