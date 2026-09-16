# 7. Test and observe

The operator is running (step 6); now put it to work.

## Create a WebApp

```bash
kubectl apply -f /tmp/webapp-operator/config/samples/webapp_v1alpha1_webapp.yaml
kubectl get webapp hello-webapp
```

Expect the printer columns from `webapp_types.go` (step 4):

```
NAME           IMAGE                          REPLICAS   AVAILABLE   AGE
hello-webapp   nginxdemos/hello:plain-text    2          2           30s
```

`AVAILABLE` reaching `2` confirms the full round trip: `reconcileDeployment`
created the Deployment, the Deployment's own controller brought up 2 Pods,
`updateStatus` read `status.availableReplicas` back off it and wrote it onto
the `WebApp`.

```bash
kubectl get deploy,svc -l app.kubernetes.io/instance=hello-webapp
kubectl get pods -l app.kubernetes.io/instance=hello-webapp
```

## Reach the managed app

```bash
kubectl port-forward svc/hello-webapp 8080:80
curl localhost:8080
```

## Prove self-healing

```bash
kubectl scale deploy hello-webapp --replicas=5
kubectl get deploy hello-webapp -w
```

Watch `REPLICAS` on the Deployment drop back to `2` on its own within a few
seconds — that's `Owns(&appsv1.Deployment{})` from step 5 firing `Reconcile`
again the moment the Deployment's spec diverged from what the `WebApp` asks
for, with no manual intervention. Same experiment with `kubectl delete svc
hello-webapp` — the Service reappears.

## Edit the spec

```bash
kubectl patch webapp hello-webapp --type=merge -p '{"spec":{"replicas":3}}'
kubectl get deploy hello-webapp
```

`REPLICAS` should move to `3` — this time the change came from the `WebApp`
spec itself (`.For(&WebApp{})`'s watch), not the `Owns()` self-healing path.

## Delete it

```bash
kubectl delete webapp hello-webapp
kubectl get deploy,svc -l app.kubernetes.io/instance=hello-webapp
```

The second command should return nothing — the owner references set in
`reconcileDeployment`/`reconcileService` (step 5) let Kubernetes garbage
collection remove the Deployment and Service automatically; the operator
itself has no delete-handling code at all.

## If a `WebApp` never gets a Deployment

```bash
kubectl describe webapp hello-webapp
kubectl logs -n webapp-operator-system deploy/webapp-operator-controller-manager
```

Check for an RBAC `Forbidden` error first (step 5's RBAC-markers section) —
the most common cause at this stage.
