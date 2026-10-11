# 3. Ingress on AWS (EKS)

> **Read this first.** Nothing in this file was run on AWS: no cluster, no load balancer, no IAM role was created.
> Facts are marked: **[searched]** = found in the sources listed at the end (some third-party, so double-check),
> **[general]** = from my general knowledge of EKS and the AWS Load Balancer Controller, **not verified here**.
> Before building anything, read the current official docs, because annotation names, IAM policies and
> chart versions change between releases. **Load balancers cost money and keep running until deleted.**

## The big picture: two common designs

On minikube, the controller is reached through a node's `hostPort`. On AWS, the entrance is an **AWS load balancer**.
There are two main ways to get one.

### Design A: AWS Load Balancer Controller (AWS LBC): an ALB per Ingress

```
client ──> Route 53 (DNS) ──> ALB (Application Load Balancer, public subnets)
                                  │  listener rules built from your Ingress (host/path)
                                  v
                            target group ──> Pods   (target-type: ip)      or
                                         └─> node ports  (target-type: instance)
```

The AWS LBC is a controller you install in the cluster. It watches Ingress objects and **creates and configures an
actual ALB** for them: listeners, rules, target groups, security groups. There is no nginx in the data path: the ALB
does the routing. IngressClass: `alb`. **[general]**

### Design B: ingress-nginx (or another in-cluster controller) behind an NLB

```
client ──> Route 53 ──> NLB (created by a Service type LoadBalancer) ──> ingress controller Pods (nginx) ──> your Pods
```

The same controller as in this lab runs in the cluster, and **one `Service` of type `LoadBalancer`** in front of it makes
AWS create a load balancer (typically a Network Load Balancer). nginx does the host/path routing **inside** the
cluster. This is closest to what you practiced locally. **[general]** Remember the retirement note in
`01-concepts.md` before choosing ingress-nginx for anything new.

### Comparison

| | A: AWS LBC (ALB) | B: in-cluster controller + NLB |
|---|---|---|
| Who routes host/path | The **ALB** (AWS-managed) | **nginx** Pods you run |
| What you operate | The LBC controller (small) | The controller Pods, scaling, upgrades |
| AWS integrations | WAF, ACM certificates on the ALB, Cognito/OIDC authentication **[general]** | TLS with cert-manager or at the NLB |
| Cost shape | ALB hourly + usage. Several Ingresses can **share one ALB** with `group.name` **[general]** | NLB hourly + usage, plus the controller Pods' compute |
| Portability | AWS-specific annotations | Closer to any other cluster |
| Rule limits | ALB limits apply (check current quotas) | nginx limits, effectively config size |

## Target type: `ip` vs `instance` (connects to the NodePort lesson)

How does the ALB send traffic into the cluster? **[searched]**

| `alb.ingress.kubernetes.io/target-type` | How traffic reaches Pods |
|---|---|
| `instance` (**the default**) | ALB → **node port** of your Service on a node → proxied to a Pod. Your Service must be reachable via a node port (`NodePort` or `LoadBalancer`) |
| `ip` | ALB registers the **Pod IPs** directly as targets. Required when Pods run on Fargate or EKS Hybrid Nodes. Pod readiness gates only work in this mode, because in `instance` mode the ALB cannot see individual Pod health |

In `instance` mode, the NodePort you learned in lesson 2 is literally the hop between the ALB and your Pods. In `ip`
mode (which works because the EKS VPC CNI gives Pods VPC-routable IPs **[general]**), the ALB skips the node port and
the extra hop.

## What you need before it works

### 1. An EKS cluster with a way to give the controller AWS permissions
The controller calls AWS APIs (to create the ALB, target groups, rules, security-group rules), so it needs an IAM role.
Two mechanisms **[general]**:
- **IRSA** (IAM Roles for Service Accounts): needs the cluster's **OIDC provider**, an IAM role trusting it, and a
  Kubernetes ServiceAccount annotated with the role ARN.
- **EKS Pod Identity**: the newer mechanism, via the Pod Identity agent add-on.

The IAM **policy** for the controller is published by the controller's project in its repository. **Use the version
that matches the controller version you install**, because new releases add permissions.

### 2. Subnet tags
The controller finds subnets by **tags**. **[searched]** (the first two from a third-party guide, the selection logic
from the controller's behavior as described in the search results: verify in the official docs)

| Tag | Value | Meaning |
|---|---|---|
| `kubernetes.io/role/elb` | `1` | Public subnets, for internet-facing load balancers |
| `kubernetes.io/role/internal-elb` | `1` | Private subnets, for internal load balancers |
| `kubernetes.io/cluster/<cluster-name>` | `shared` or `owned` | Associates the subnet with the cluster |

- The controller does **not** inspect route tables to decide public vs private: it relies on the tags.
- Subnets with fewer than ~8 free IP addresses are filtered out, and it picks **one subnet per Availability Zone**.
- **Missing subnet tags is the most common reason a load balancer is not created.** It leaves your Ingress with an empty ADDRESS.

### 3. Install the controller
Typically with Helm **[general]**:

```bash
helm repo add eks https://aws.github.io/eks-charts
helm repo update
helm install aws-load-balancer-controller eks/aws-load-balancer-controller \
  -n kube-system \
  --set clusterName=<your-cluster> \
  --set serviceAccount.create=false \
  --set serviceAccount.name=aws-load-balancer-controller    # the ServiceAccount carrying the IAM role
```
(Check the chart's current README for required values such as `region` and `vpcId`, which can be needed when the
controller can't read them from instance metadata.) Then verify:

```bash
kubectl -n kube-system get deploy aws-load-balancer-controller
kubectl get ingressclass          # an IngressClass for the controller should exist
```

### 4. A certificate for HTTPS
Request or import a certificate in **AWS Certificate Manager (ACM)** in the same region as the ALB, and reference its
ARN in the Ingress annotation. **[general]**

### 5. DNS
Create DNS records pointing your names at the ALB's DNS name (Route 53 alias records). **ExternalDNS** can create them
automatically from the Ingress host names. **[general]**

## An example Ingress for the AWS LBC

Annotations below follow the ones named in the search results and the controller's usual conventions. **Confirm each
name against the controller's current "Ingress annotations" reference before using it.**

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: site
  namespace: prod
  annotations:
    alb.ingress.kubernetes.io/scheme: internet-facing          # [searched] or "internal"
    alb.ingress.kubernetes.io/target-type: ip                  # [searched] default is "instance"
    alb.ingress.kubernetes.io/listen-ports: '[{"HTTP":80},{"HTTPS":443}]'          # [general]
    alb.ingress.kubernetes.io/certificate-arn: arn:aws:acm:<region>:<account-id>:certificate/<id>   # [general]
    alb.ingress.kubernetes.io/ssl-redirect: "443"              # [general]
    alb.ingress.kubernetes.io/healthcheck-path: /healthz       # [general]
    alb.ingress.kubernetes.io/group.name: shared-public        # [general] share one ALB between Ingresses
spec:
  ingressClassName: alb
  rules:
  - host: shop.example.com
    http:
      paths:
      - path: /api
        pathType: Prefix
        backend: {service: {name: api-svc, port: {number: 80}}}
      - path: /
        pathType: Prefix
        backend: {service: {name: shop-svc, port: {number: 80}}}
```

Compared with the minikube Ingress in this lab:
- `ingressClassName: alb` instead of `nginx`. (The older annotation `kubernetes.io/ingress.class: alb` appears in the
  EKS docs found by the search; the field is the current form.)
- The rules (host, path, backend) are **identical**. Only the class and the annotations change.
- With `target-type: instance`, the backend Services must be `NodePort` (or `LoadBalancer`). With `ip`, `ClusterIP` is enough.

## Minikube vs EKS at a glance

| | minikube (this lab) | EKS with AWS LBC |
|---|---|---|
| Controller | ingress-nginx addon, one Pod, `hostPort 80/443` | AWS LBC (a small controller) that creates an **ALB** |
| IngressClass | `nginx` (default) | `alb` |
| Entrance | A node's port 80 (reached via port-forward/tunnel/docker network) | An ALB with a DNS name |
| `ADDRESS` of the Ingress | Empty or the node IP | The ALB's DNS name |
| Names | `Host:` header, `/etc/hosts` | Route 53 records |
| HTTPS | Secret in the cluster (or none) | ACM certificate on the ALB |
| Permissions | None | IAM role for the controller (IRSA / Pod Identity) |
| Cost | Free | ALB/NLB, data processing, plus node compute |

## Terraform angle

If you manage EKS with Terraform, the pieces map onto resources **[general]**: the cluster and VPC (public/private
subnets with the tags above), the OIDC provider or Pod Identity association, an IAM policy and role for the
controller, and a `helm_release` for the controller chart. Destroying is the dangerous direction: see below.

## Pitfalls and cleanup

| Pitfall | Why it matters |
|---|---|
| Deleting the cluster or Terraform stack **before** deleting Ingresses and `LoadBalancer` Services | The load balancers (and their security groups / ENIs) can be left behind, still billing, and can **block VPC deletion**. Delete the Ingress objects first and wait for the load balancers to disappear |
| Missing subnet tags | The ALB is never created; the Ingress `ADDRESS` stays empty |
| Controller IAM policy older than the controller version | Permission-denied errors in the controller logs |
| `target-type: instance` with a `ClusterIP` Service | Targets cannot be registered through a node port. Use `ip`, or make the Service `NodePort` |
| Health checks failing | `502/503` from the ALB. Check the health-check path and port, and the security groups between the ALB and Pods/nodes |
| Public ALB by accident | `scheme: internet-facing` exposes it. Use `internal` for private apps |

## Troubleshooting on AWS

| Symptom | First checks |
|---|---|
| `ADDRESS` empty | Is the controller running? `kubectl -n kube-system logs deploy/aws-load-balancer-controller`. Look for subnet-discovery or permission errors |
| ALB exists but `503` / unhealthy targets | Target group health in the AWS console. Health-check path/port, security groups, Pod readiness |
| `404` from the ALB | No listener rule matched the host/path (typo in `host`, wrong path, or the Ingress belongs to a different class) |
| Certificate not applied | Wrong region, ARN typo, or the certificate not issued in ACM |
| Works in the browser by IP, not by name | DNS record missing or not propagated |

## Sources
- [Route application and HTTP traffic with Application Load Balancers - Amazon EKS](https://docs.aws.eu/eks/latest/userguide/alb-ingress.html) (EKS documentation mirror)
- [Troubleshoot load balancer creation, AWS re:Post](https://repost.aws/de/knowledge-center/load-balancer-troubleshoot-creating)
- [AWS Load Balancer Integration on EKS (ReportPortal guide, third-party)](https://www.reportportal.io/docs/installation-steps-advanced/AWSLoadBalancerIntegrationOnEKS/)
- The controller's own documentation (kubernetes-sigs/aws-load-balancer-controller): the authoritative reference for annotations, IAM policy and versions. I did not read it directly: check it.
