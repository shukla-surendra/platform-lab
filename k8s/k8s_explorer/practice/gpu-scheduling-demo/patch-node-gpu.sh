#!/usr/bin/env bash
# Advertise a fake GPU-shaped extended resource on one node, without any real GPU hardware.
# This is the documented pattern from the Kubernetes docs ("Advertise Extra Resources on a
# Node") for exactly this purpose: testing extended-resource scheduling behavior. It's what a
# real device plugin's ListAndWatch call does under the hood — patch node status, nothing more.
set -euo pipefail

NODE="${1:-minikube-m03}"
COUNT="${2:-2}"

kubectl patch node "$NODE" --subresource=status --type='merge' -p \
  "{\"status\": {\"capacity\": {\"example.com/toygpu\": \"$COUNT\"}, \"allocatable\": {\"example.com/toygpu\": \"$COUNT\"}}}"

echo "Patched $NODE with example.com/toygpu=$COUNT (capacity and allocatable)."
kubectl get node "$NODE" -o jsonpath='{.metadata.name}{" capacity="}{.status.capacity.example\.com/toygpu}{" allocatable="}{.status.allocatable.example\.com/toygpu}{"\n"}'
