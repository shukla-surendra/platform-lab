# Service `type: LoadBalancer` on EKS: what happens and how it behaves

Hands-on run against this lab cluster (us-east-1), using `k8s/hello-lb.yaml`
(a second Service, `hello-lb`, selecting the same `app=hello` pods).
Everything below was observed, except where marked "general knowledge".

## 1. Create it

```
kubectl apply -f k8s/hello-lb.yaml
kubectl -n demo get svc            # EXTERNAL-IP <pending>
kubectl -n demo get svc hello-lb -w
```

Timeline observed:

| Time | What you see |
|---|---|
| 0 s | `EXTERNAL-IP <pending>`; event `EnsuringLoadBalancer`; a **NodePort was auto-allocated** (here `80:30238/TCP`) |
| ~8 s | event `EnsuredLoadBalancer`; EXTERNAL-IP is a hostname `xxxx-NNN.us-east-1.elb.amazonaws.com` |
| ~1 min | AWS reports instances `OutOfService` -> `InService` after health checks pass (needs 2 passes, 10 s apart) |
| ~1-2 min | Hostname resolves and `curl` returns `200` (first tries fail with `000` while DNS/health settle) |

Lesson: EXTERNAL-IP appearing does **not** mean it is serving yet. Wait for health checks and DNS.

## 2. What Kubernetes + AWS actually built

The in-tree cloud controller (`service-controller`) watched the Service and called the AWS API. Result:

- A **Classic Load Balancer** (default for a plain `type: LoadBalancer` Service with no controller), `internet-facing`, spread over the two AZs of the subnets (`us-east-1a`, `us-east-1b`).
- Listener: TCP **80** on the LB -> TCP **30238** (the NodePort) on the **worker instances**.
- Health check: `TCP:30238`, every 10 s, 5 s timeout, healthy after 2 passes, unhealthy after 6 failures.
- A **security group** for the LB (open to the internet on 80) and rules letting it reach the nodes.
- Registered targets: the **EC2 worker nodes** (not the pods).

## 3. The traffic path

```
client -> AWS Classic LB :80
       -> a worker node :30238 (NodePort, via kube-proxy)
       -> a pod  :80   (kube-proxy picks ANY ready pod, on any node)
```

So there are two load-balancing hops: AWS picks a **node**, then kube-proxy picks a **pod** (possibly on another node).

## 4. How it behaved

- **Distribution**: 20 requests landed on both pods (14 and 9 in the logs; the pods saw a few extra from earlier tests). Roughly even but not exact; this is connection-level balancing, not strict round robin.
- **Client IP is lost**: nginx logged the **node IPs** (`10.20.1.212`, `10.20.2.232`), not the real client IP. Because `External Traffic Policy: Cluster` (the default) means a request may be forwarded to a pod on another node, and the traffic is source-NATed.
  - Keep the client IP: `externalTrafficPolicy: Local` (only nodes with a local pod pass health checks; can skew load; with Classic LB the real IP is still not visible unless you use proxy protocol / an NLB or ALB, which is general knowledge, not tested here).
- **Same pods, two Services**: the old `hello` (ClusterIP) kept working in parallel; Services are just different front doors to the same pods.
- **Session affinity**: `None` (each request may hit a different pod).

## 5. Delete it

```
kubectl -n demo delete svc hello-lb
```

Observed: the Classic load balancer was gone within seconds; count of LBs in the region back to 0. Kubernetes deleted what it created. No leftover LB security group (only the EKS cluster security group remains, which belongs to the cluster).

**This is why you must delete the Service before `terraform destroy`**: Terraform doesn't know about this load balancer or its security group. If the cluster/VPC is destroyed first, they are orphaned, keep billing, and block VPC/subnet deletion.

## 6. Cost during this test

Classic LB ~ $0.025/hr plus data processed. The whole experiment (a few minutes) cost a fraction of a cent. Left running it is ~$18-20/month. (Approximate; verify.)

## 7. Things to remember

- Plain `type: LoadBalancer` gives a **Classic LB**. Classic is legacy; for NLB/ALB install the **AWS Load Balancer Controller** (NLB via Service annotations, ALB via Ingress). Not part of this lab.
- It needs subnets tagged `kubernetes.io/role/elb=1` (public) so AWS knows where to place the LB: done in `01_network.tf`.
- One LB per Service gets expensive; an Ingress/ALB lets many services share one.
- Port 80 over plain HTTP, open to the internet: fine for a test, not for production (use TLS, restrict with `loadBalancerSourceRanges`).
- The LB hostname changes if you delete and recreate the Service.

See also: `ACCESSING_THE_APP.md`, `AKS_VS_EKS_LOAD_BALANCER.md`.

---

# Console observation: the Classic Load Balancer (second run)

Recreated `hello-lb` and inspected the result (console: EC2 -> Load Balancing -> Load Balancers, us-east-1; same data via `aws elb ...`). Confirmed: **the load balancer type is "Classic"**.

## What the console/API shows

| Field | Observed |
|---|---|
| Type | **Classic** (legacy ELB; not ALB/NLB, which live under the "Application/Network" types) |
| Name | `a<32 hex chars>` (auto-generated from the Service UID, not a friendly name) |
| Scheme | internet-facing |
| VPC / subnets | the lab VPC; the two public subnets (one per AZ: `us-east-1a`, `us-east-1b`) |
| Listener | TCP 80 -> instance TCP 30238 (the Service's NodePort) |
| Health check | `TCP:30238`, interval 10 s, timeout 5 s, healthy 2, unhealthy 6 |
| Target instances | both worker EC2 nodes, `InService` (after about 1.5-2 min) |
| Cross-zone load balancing | **off** (`CrossZone: false`) |
| Idle timeout | 60 s |
| Connection draining | off |
| Access logs | off |
| Tags | `kubernetes.io/service-name = demo/hello-lb`, `kubernetes.io/cluster/eks-lab = owned` |

The two tags are how Kubernetes finds and cleans up the load balancer later. They are the proof the cluster, not Terraform, owns it.

## Security groups it created

- **LB security group** named `k8s-elb-<lb-name>`, description "Security group for Kubernetes ELB ... (demo/hello-lb)", tagged `kubernetes.io/cluster/eks-lab = owned`.
  - Inbound: **TCP 80 from 0.0.0.0/0** (the world), plus a second rule from 0.0.0.0/0 that shows as port `3` (appears to be ICMP type 3, "destination unreachable", needed for path-MTU discovery: general knowledge, not verified).
- **Node side**: the EKS cluster security group (`eks-cluster-sg-...`) got a rule allowing traffic **from the LB security group** (all ports/protocols), so the load balancer can reach the NodePort on the nodes.

Neither of these security-group changes is in Terraform. The node-side rule is added to a group Terraform does manage indirectly (the cluster's own SG), and Kubernetes removes it when the Service is deleted.

## Notes from watching it

- **Classic is the default** for a plain `type: LoadBalancer` Service when only the built-in cloud controller is present. To get NLB/ALB you install the AWS Load Balancer Controller.
- **Cross-zone off**: each AZ's load balancer node sends traffic to instances in its own AZ only. With uneven node counts per AZ this skews load (here 1 node per AZ, so fine).
- **Slow to become healthy**: EXTERNAL-IP shows in ~8 s, but traffic works only after 2 health-check passes and DNS settle (~1.5-2 min). Early `curl` returns `000`.
- **Targets are nodes, not pods**: that's why the NodePort exists and why the client IP is lost.
- **Created at**: the console "Creation time" matches the time `kubectl apply` ran.

## Cleanup (still required)

```
kubectl -n demo delete svc hello-lb
```
Confirms in console: the load balancer disappears, and the `k8s-elb-...` security group is deleted a few seconds later. Do this before `terraform destroy`.
