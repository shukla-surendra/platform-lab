#!/usr/bin/env bash
# Runs etcdctl *inside* the real etcd-minikube pod, using the same client cert the
# kube-apiserver itself uses to talk to etcd (mTLS - etcd trusts nothing else). This is
# the actual etcd backing this repo's shared minikube cluster, not a separate instance.
set -euo pipefail

kubectl exec -n kube-system etcd-minikube -- sh -c \
  "etcdctl --cacert=/var/lib/minikube/certs/etcd/ca.crt \
           --cert=/var/lib/minikube/certs/etcd/server.crt \
           --key=/var/lib/minikube/certs/etcd/server.key \
           --endpoints=https://127.0.0.1:2379 $*"
