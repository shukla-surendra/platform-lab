#!/usr/bin/env bash
# --all is not optional here — same lesson as ../daemonset-sidecar-demo/build-images.sh:
# minikube image build defaults to the control-plane node only. This demo only needs
# one node per Pod's own local image store though (each StatefulSet Pod can land on
# either node), so skipping --all risks whichever node the scheduler picks sitting in
# ImagePullBackOff.
set -euo pipefail
cd "$(dirname "$0")"

echo "== building identity-server:local on all nodes =="
minikube image build --all -t identity-server:local images/identity-server
