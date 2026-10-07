# nginx Deployment in a Namespace

A namespace is a named partition of the cluster. It keeps related objects together and separate from others.

## Files
- `namespace.yml`: creates the `nginx-demo` namespace.
- `deployment.yml`: nginx Deployment (2 replicas) with `metadata.namespace: nginx-demo`.

## Steps
```bash
kubectl apply -f namespace.yml      # 1. namespace first, it must exist
kubectl apply -f deployment.yml     # 2. then the deployment

kubectl get pods -n nginx-demo      # always add -n, or you look in "default"
kubectl get all -n nginx-demo
```

## Tips
- Set a default so you can skip `-n`:
  `kubectl config set-context --current --namespace=nginx-demo`
- Alternative to the YAML field: `kubectl apply -f deployment.yml -n nginx-demo`
  (errors if the file names a different namespace).
- Delete everything at once: `kubectl delete namespace nginx-demo`
- Names only need to be unique within a namespace.
