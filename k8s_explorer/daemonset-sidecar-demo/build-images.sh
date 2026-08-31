#!/usr/bin/env bash
# --all is not optional here: minikube image build defaults to the control-plane node only.
# The DaemonSet needs node-reporter on EVERY node to prove one-pod-per-node - if it were only
# on one node's local image store, the DaemonSet's pod on the other node would sit in
# ImagePullBackOff, silently defeating the entire point of the demo (learned this the hard
# way building toy-controller/ earlier in this repo's history).
set -euo pipefail
cd "$(dirname "$0")"

for img in node-reporter hit-counter log-tailer; do
  echo "== building ${img}:local on all nodes =="
  minikube image build --all -t "${img}:local" "images/${img}"
done
