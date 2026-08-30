#!/usr/bin/env bash
# Deliberate order, for safety on a shared cluster: build the image, deploy the server, wait
# for it to actually be healthy, and ONLY THEN register the webhook configs - so there's never
# a window where a WebhookConfiguration points at a not-yet-running server (failurePolicy:
# Ignore covers that anyway, but no reason to rely on it when avoiding it is free).
set -euo pipefail
cd "$(dirname "$0")"

echo "[1/7] generating a fresh self-signed cert (never commit tls.crt/tls.key - regenerated every run)..."
openssl req -x509 -newkey rsa:2048 -nodes \
  -keyout tls.key -out tls.crt -days 365 \
  -subj "/CN=admission-webhook.default.svc" \
  -addext "subjectAltName=DNS:admission-webhook.default.svc,DNS:admission-webhook.default.svc.cluster.local" \
  2>/dev/null

echo "[2/7] building image on all minikube nodes..."
minikube image build --all -t admission-webhook-demo:local .

echo "[3/7] creating the scoped demo namespace..."
kubectl create namespace admission-webhook-demo --dry-run=client -o yaml | kubectl apply -f -
kubectl label namespace admission-webhook-demo admission-webhook-demo=enabled --overwrite

echo "[4/7] creating the TLS secret from the generated cert..."
kubectl create secret tls admission-webhook-tls \
  --cert=tls.crt --key=tls.key -n default \
  --dry-run=client -o yaml | kubectl apply -f -

echo "[5/7] deploying the webhook server..."
kubectl apply -f deployment.yaml
kubectl rollout status deployment/admission-webhook -n default --timeout=60s

echo "[6/7] registering the webhook configs (namespaceSelector-scoped, failurePolicy: Ignore)..."
CA_BUNDLE=$(base64 < tls.crt | tr -d '\n')
sed "s/CA_BUNDLE_PLACEHOLDER/${CA_BUNDLE}/" webhook-config.yaml.tmpl | kubectl apply -f -

echo "[7/7] done. Only namespaces labeled admission-webhook-demo=enabled are affected."
