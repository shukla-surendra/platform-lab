#!/usr/bin/env bash
# Adds the EKS lab cluster to ~/.kube/config, switches kubectl to it, and shows the nodes.
# Usage: ./connect.sh            (reads cluster name and region from terraform outputs, falls back to defaults)
set -euo pipefail
cd "$(dirname "$0")"

# Terraform outputs only exist while the lab is applied. Defaults match variables.tf.
CLUSTER=$(terraform output -raw cluster_name 2>/dev/null || echo "eks-egress-lab")
REGION=$(terraform output -raw region 2>/dev/null || echo "us-east-1")

echo "Cluster: $CLUSTER   Region: $REGION (always pass --region: your CLI default may differ)"

if ! aws eks describe-cluster --name "$CLUSTER" --region "$REGION" --query 'cluster.status' --output text >/dev/null 2>&1; then
  echo "Cluster '$CLUSTER' not found in $REGION. Not applied yet, or already destroyed." >&2
  exit 1
fi

aws eks update-kubeconfig --name "$CLUSTER" --region "$REGION"

echo
echo "Current context: $(kubectl config current-context)"
echo
kubectl get nodes -o wide
echo
echo "Switch back to minikube with:  kubectl config use-context minikube"
