# Accessing the deployed app (`k8s/hello-app.yaml`)

The app is in namespace `demo`: Deployment `hello` (2 nginx pods) + Service `hello` (type `ClusterIP`).
Tested: **port-forward works** (option 1).

Make sure kubectl points at the right cluster first:
```
kubectl config current-context        # must be the eks-lab context
# or use the separate file:  export KUBECONFIG=~/.kube/eks-lab.config
```

## Why it isn't public by default

A `ClusterIP` Service gets a virtual IP that exists **only inside the cluster**. Pods and nodes have IPs, but there is no route from the internet to the app: no load balancer, no NodePort, no Ingress, and no security-group rule. So you pick how to reach it.

## Options at a glance

| # | Method | Who can reach it | Cost | Status |
|---|---|---|---|---|
| 1 | `kubectl port-forward` | Only you, while the command runs | Free | **Tested, works** |
| 2 | In-cluster DNS (`hello.demo`) | Other pods | Free | Works (untested) |
| 3 | `type: LoadBalancer` Service | Internet | ~$0.025/hr + data | Not applied |
| 4 | Ingress + AWS Load Balancer Controller (ALB) | Internet, host/path routing, TLS | ALB cost + controller setup | Not part of this lab |

## 1. Port-forward (free, for testing)

```
kubectl -n demo port-forward svc/hello 8080:80
# open http://localhost:8080   or:   curl localhost:8080
```
- Forwards local port 8080 to Service port 80 through the Kubernetes API server.
- Keep the terminal open; Ctrl+C stops it.
- You can target a single pod instead: `kubectl -n demo port-forward pod/<pod-name> 8080:80`.
- Via `svc/` it picks **one** backing pod when it starts; it does not load-balance across pods.
- For debugging only, not for real users.

## 2. From inside the cluster

Services get DNS names: `<service>.<namespace>.svc.cluster.local` (short: `hello.demo`, or just `hello` from the same namespace). CoreDNS resolves them.
```
kubectl -n demo run tmp --rm -it --image=busybox --restart=Never -- wget -qO- hello
```
Other apps in the cluster call each other this way.

## 3. Public via `type: LoadBalancer`

```
kubectl -n demo patch svc hello -p '{"spec":{"type":"LoadBalancer"}}'
kubectl -n demo get svc hello -w          # wait for EXTERNAL-IP (xxxx.elb.amazonaws.com)
curl http://<that-hostname>
```
- Takes a few minutes; the DNS name may need a minute after appearing.
- Creates an AWS **Classic Load Balancer** (default for a plain Service) in your public subnets (they carry the `kubernetes.io/role/elb` tag). Open to the internet on port 80.
- ~$0.025/hr plus data transfer.
- **Delete the Service before `terraform destroy`**, or the load balancer and its security group are orphaned and block VPC deletion:
  `kubectl -n demo delete svc hello` (or patch back to `ClusterIP`).
- To make it permanent, edit `type: ClusterIP` -> `type: LoadBalancer` in `k8s/hello-app.yaml` and re-apply.

## 4. Ingress with an ALB (the production-style way)

Needs the **AWS Load Balancer Controller** installed in the cluster (Helm chart + an IAM role for it, via IRSA or Pod Identity). Then an `Ingress` resource makes AWS create an Application Load Balancer, with host/path routing, TLS (ACM certificates) and one ALB shared by many services. Not set up in this lab; a good follow-up lesson.

## Things that do NOT work (and why)

- **Node public IPs**: nodes have public IPs here, but no `NodePort` Service and no security-group rule allowing it, so the app isn't reachable that way.
- **Pod IPs / Service ClusterIP from your laptop**: private VPC addresses (`10.20.x.x`, `172.20.x.x`), not routable from the internet.

## Troubleshooting

| Symptom | Check |
|---|---|
| `port-forward` "unable to listen on port 8080" | Port in use locally; use another, e.g. `9090:80` |
| `port-forward` connection refused / error | `kubectl -n demo get pods` (Running/Ready?), `kubectl -n demo describe pod ...` |
| Service has `<pending>` EXTERNAL-IP for long | `kubectl -n demo describe svc hello` (events: subnet tags, quota, permissions) |
| LB hostname doesn't respond | Wait a few minutes; check `kubectl -n demo get endpoints hello` has pod IPs |
| Wrong cluster | `kubectl config current-context` (see `USING_THE_CLUSTER.md`) |

## Cleanup

```
kubectl delete namespace demo      # removes app; do this BEFORE terraform destroy
```
