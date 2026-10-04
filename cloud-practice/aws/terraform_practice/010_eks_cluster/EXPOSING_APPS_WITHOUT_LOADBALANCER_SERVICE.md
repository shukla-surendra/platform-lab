# Exposing an app without `type: LoadBalancer`

Nothing in this file was run (the lab cluster was destroyed). Only the `LoadBalancer` Service and `port-forward` were tested; see `LOADBALANCER_SERVICE_BEHAVIOR.md` and `ACCESSING_THE_APP.md`. Details below are from general knowledge, so verify against current docs before relying on them.

## 1. The real question

A ClusterIP is reachable only inside the cluster. To let someone outside (a user, a browser) reach a pod, **something must sit on the boundary and accept their traffic**. `type: LoadBalancer` is one way to create that door. The question is which other doors exist.

```
outside world  ->  [ A DOOR ]  ->  ClusterIP Service  ->  pods
```

Every option below is a different kind of door. They differ in cost, stability and who they are meant for.

## 2. Pick by goal

| Goal | Use |
|---|---|
| Just test it myself, free | `kubectl port-forward` (not public) |
| Public, cheapest, learning only | **NodePort** |
| Public, production, many apps | **Ingress** (ALB) or **Gateway API** |
| Private/admin access, no public port | Tunnel / VPN / SSM port forwarding |
| Extra edge features (cache, WAF, auth) | CloudFront / API Gateway in front |

## 3. Option A: NodePort (no cloud load balancer)

The Service opens the **same port on every node** (range 30000-32767) and forwards to the pods.

```yaml
apiVersion: v1
kind: Service
metadata: { name: hello-np, namespace: demo }
spec:
  type: NodePort
  selector: { app: hello }
  ports:
    - port: 80
      targetPort: 80
      nodePort: 30080        # optional; omit and Kubernetes picks one
```

```
client -> http://<node-public-ip>:30080 -> node (kube-proxy) -> any ready pod
```

To make it reachable from the internet in this lab:
1. Nodes must have public IPs (they do: public subnets).
2. Add an inbound rule for TCP 30080 on the node/cluster security group (Terraform: `aws_vpc_security_group_ingress_rule`, ideally limited to your IP, not `0.0.0.0/0`).
3. Open `http://<a node's public IP>:30080`.

Downsides:
- **Node IPs change** when nodes are replaced (upgrades, scaling, failures), so the URL breaks.
- **No balancing across nodes**: the client picks a node; a dead node means a dead URL.
- You open ports directly on the nodes; **no TLS, no host/path routing**.
- Only works with public nodes. Production nodes are normally private.

Use it to understand the mechanism, not for real traffic.

## 4. Option B: Ingress (the standard production answer)

An **Ingress** is not a Service type. It is a set of HTTP routing **rules** (host/path -> Service). An **ingress controller** reads those rules and does the work.

On AWS, install the **AWS Load Balancer Controller**; it creates an **ALB** and keeps it in sync with your Ingress objects.

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: hello
  namespace: demo
  annotations:
    alb.ingress.kubernetes.io/scheme: internet-facing
    alb.ingress.kubernetes.io/target-type: ip      # send straight to pod IPs
spec:
  ingressClassName: alb
  rules:
    - http:
        paths:
          - path: /
            pathType: Prefix
            backend:
              service: { name: hello, port: { number: 80 } }   # the ClusterIP Service
```

```
client -> ALB (one) -> rules by host/path -> ClusterIP Services -> pods
```

Key difference from a LoadBalancer Service:

| | `type: LoadBalancer` Service | Ingress + ALB |
|---|---|---|
| Load balancers created | **One per Service** | **One shared** by many Services |
| Routing | Port only (TCP) | Host and path rules (HTTP/HTTPS) |
| TLS | Not built in | ACM certificates on the ALB |
| Extras | Basic | Redirects, auth, WAF integration (via ALB) |
| LB type (AWS) | Classic LB (default) | Application LB |

Important: Ingress **still uses a load balancer** (the ALB). You haven't avoided the load balancer, you've shared one across many apps.

Setup needed (not in this lab yet):
- IAM role + policy for the controller (IRSA or EKS Pod Identity).
- Install the controller (Helm chart `aws-load-balancer-controller`).
- Subnets tagged `kubernetes.io/role/elb=1` (already done in `01_network.tf`).
- Backend Services stay **ClusterIP**.

## 5. Option C: Gateway API

The newer, more expressive replacement for Ingress (roles split between platform and app teams, richer routing). Same idea: rules + a controller. The AWS Load Balancer Controller has been adding support; check current status.

## 6. Option D: your own ingress controller (e.g. ingress-nginx)

nginx pods inside the cluster do the routing. You still need **one** way in front of them: a `LoadBalancer` Service (one LB) or a NodePort. So you reduce to one load balancer, but still have one.

## 7. Option E: hostPort / hostNetwork

A pod binds a port directly on its node. No load balancer, no Service. Ties the pod to a specific node and port; used for special cases (DaemonSets, node agents), rarely for apps.

## 8. Option F: services in front (CloudFront, API Gateway)

An AWS edge service forwards requests to the cluster (via a public entry or a private link). Adds caching, auth, WAF, custom domains. There is still some entry point behind it.

## 9. Option G: private access (no public door)

For admins or internal users, avoid exposing anything:
- `kubectl port-forward` (tested, personal use).
- SSM port forwarding to a node or bastion, VPN, Tailscale, Cloudflare Tunnel.

## 10. Summary

| Option | Public? | Load balancers | Stable URL | Status here |
|---|---|---|---|---|
| port-forward | No (you only) | 0 | n/a | Tested |
| **LoadBalancer Service** | Yes | 1 per Service | Yes (hostname) | **Tested** |
| NodePort | Yes (if SG open + public nodes) | 0 | No (node IPs change) | Not run |
| **Ingress + ALB** | Yes | 1 for many apps | Yes | Not set up |
| Gateway API | Yes | Usually 1 | Yes | Not set up |
| ingress-nginx | Yes | 1 (in front of nginx) | Yes | Not set up |
| Tunnel / VPN / SSM | Private | 0 | n/a | Not run |

## 11. Possible follow-up lessons

1. NodePort + a security-group rule in Terraform, then see why the URL is fragile when a node is replaced.
2. AWS Load Balancer Controller via Terraform + Helm, one Ingress routing two Services (e.g. `/a` and `/b`), to see one ALB serve many apps.

---

# Is the minimal Ingress + ALB the best solution?

Short answer: it is the **standard pattern for HTTP apps on AWS**, but the snippet in section 4 is a **minimal lab version**, and "best" depends on what you expose. Not run; from general knowledge, verify against current docs.

## What is good about it

- **HTTP/HTTPS apps**: the ALB understands hosts, paths and TLS.
- **Shared load balancer**: many apps can share one ALB instead of one load balancer per Service.
- **`target-type: ip`**: the ALB sends traffic straight to pod IPs, skipping the NodePort hop and kube-proxy's second balancing step. This works because the VPC CNI gives pods real VPC IPs. Backends stay plain **ClusterIP** Services.

## What the minimal snippet is missing for production

```yaml
metadata:
  annotations:
    alb.ingress.kubernetes.io/scheme: internet-facing
    alb.ingress.kubernetes.io/target-type: ip
    alb.ingress.kubernetes.io/listen-ports: '[{"HTTP":80},{"HTTPS":443}]'
    alb.ingress.kubernetes.io/certificate-arn: <ACM cert ARN>     # TLS
    alb.ingress.kubernetes.io/ssl-redirect: '443'                 # HTTP -> HTTPS
    alb.ingress.kubernetes.io/healthcheck-path: /healthz          # real health endpoint
    alb.ingress.kubernetes.io/group.name: shared                  # many Ingresses share ONE ALB
    alb.ingress.kubernetes.io/inbound-cidrs: <your CIDR>          # limit who can reach it
spec:
  rules:
    - host: app.example.com                                       # host-based routing
```

| Gap | Why it matters |
|---|---|
| No TLS | The snippet serves plain HTTP on port 80 only |
| No `group.name` | Each Ingress gets its **own** ALB, losing the main cost advantage |
| Default health check path `/` | May not reflect real app health |
| No access restriction / WAF | Open to the whole internet |
| No hostname / DNS | Needs a Route 53 record (ideally ExternalDNS) pointing at the ALB |

## What it requires that this lab does not have yet

- The **AWS Load Balancer Controller** installed (Helm chart), with an **IAM role** for it (IRSA or EKS Pod Identity).
- Without the controller, an Ingress with `ingressClassName: alb` does nothing.
- Public subnets tagged `kubernetes.io/role/elb=1` (already done in `01_network.tf`).

## When something else is a better fit

| Situation | Better choice |
|---|---|
| TCP/UDP or non-HTTP traffic (database, raw TCP gRPC, game servers) | `LoadBalancer` Service backed by an **NLB**, not an ALB |
| One simple app, no routing needed | A single NLB Service can be simpler |
| New projects | Evaluate **Gateway API** (where the ecosystem is heading); check the AWS controller's current support |
| ingress-nginx | I recall its retirement being announced for 2026; verify before building on it |

## Cost

ALB is about $0.0225/hr plus usage (LCU) charges, roughly $16-20/month, similar to a Classic LB. The saving comes from **sharing one ALB across apps** via `group.name`. Approximate; verify current pricing.

## Verdict

- Good default for **web apps on EKS**.
- Treat the snippet as a starting point: add TLS, `group.name`, a real health check, access limits and DNS.
- Use an NLB for non-HTTP traffic.

## Follow-up lesson idea (real work: the controller needs IAM)

Terraform + Helm for the AWS Load Balancer Controller (IAM policy/role, Pod Identity or IRSA, Helm release), then one hardened Ingress routing two Services (`/a`, `/b`) through a single shared ALB.
