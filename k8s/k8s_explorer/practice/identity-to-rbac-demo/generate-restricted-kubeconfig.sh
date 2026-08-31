#!/usr/bin/env bash
# Builds a standalone kubeconfig for the restricted-sa ServiceAccount, so the impersonation
# test below uses a genuinely separate, lower-privileged identity - not just `--as` on top of
# an already-admin kubeconfig, which would prove nothing about whether impersonation itself
# is access-controlled.
set -euo pipefail

SERVER=$(kubectl config view --minify -o jsonpath='{.clusters[0].cluster.server}')
TOKEN=$(kubectl create token restricted-sa -n default --duration=1h)
OUT="${1:-restricted-sa.kubeconfig}"

# insecure-skip-tls-verify: fine here, this is testing RBAC authorization logic against a
# local minikube cluster, not a TLS trust boundary - not something to carry into production.
cat > "$OUT" <<EOF
apiVersion: v1
kind: Config
clusters:
  - name: minikube
    cluster:
      server: ${SERVER}
      insecure-skip-tls-verify: true
contexts:
  - name: restricted-sa
    context:
      cluster: minikube
      user: restricted-sa
current-context: restricted-sa
users:
  - name: restricted-sa
    user:
      token: ${TOKEN}
EOF

echo "Wrote $OUT (token valid 1h)."
