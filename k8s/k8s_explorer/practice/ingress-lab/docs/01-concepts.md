# 1. Ingress concepts

## The problem Ingress solves

A Service gets traffic **to** your Pods. To get traffic from **outside**, the Service types give you:

| Option | One entrance per... | Pain |
|---|---|---|
| `NodePort` | app (one high port each, 30000-32767) | Port sprawl, node IPs, no names or paths |
| `LoadBalancer` | app (one cloud load balancer each) | Cost and sprawl: 10 apps = 10 load balancers |
| **Ingress** | **cluster** (one entrance for many apps) | Needs a controller; HTTP/HTTPS only |

An Ingress lets **one** external entrance serve **many** apps by looking at the HTTP **host name** and **path**.

```
                       one entrance (a load balancer or a node port)
client ──> shop.example.com ──┐         │
client ──> blog.example.com ──┼──> Ingress controller ──reads──> Ingress rules
client ──> shop.example.com/api ┘         │
                              ┌───────────┼───────────┐
                              v           v           v
                          shop-svc    blog-svc     api-svc     (ordinary Services)
                              │           │           │
                            Pods        Pods        Pods
```

## The two parts: Ingress and controller

| Part | What it is |
|---|---|
| **Ingress** (`kind: Ingress`) | A Kubernetes object holding **routing rules**. It does nothing by itself |
| **Ingress controller** | A program (often nginx, or a cloud load balancer integration) that **watches** Ingress objects and makes the rules real |

**An Ingress with no controller does nothing.** This is the most common beginner confusion. Kubernetes ships the
Ingress *API*, but not a controller. You install one (minikube: `minikube addons enable ingress`; EKS: the AWS Load
Balancer Controller or ingress-nginx; see the other docs).

> **Important: `ingress-nginx` is being retired.** The Kubernetes project announced the retirement of the
> `ingress-nginx` controller in November 2025, with best-effort maintenance until **March 2026**, and no further
> releases, bug fixes or security patches after that. Existing installs keep running, but they get no security fixes.
> minikube's `ingress` addon installs this controller (v1.13.2 on this lab's cluster), and it is what this lab uses
> because it is the easiest to run locally. The **Ingress API and everything you learn about rules, hosts, paths and
> TLS stays the same** with other controllers. For anything that matters, plan on a maintained controller and look
> at **Gateway API** (section below). I confirmed the announcement by search but did not check what happened after
> March 2026: check the project's repository for its current status. Sources are at the end of this file.

## What an Ingress looks like

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: site
  namespace: ingress-s1
spec:
  ingressClassName: nginx            # which controller should handle this (see IngressClass)
  rules:
  - host: shop.local                 # match the HTTP Host header
    http:
      paths:
      - path: /api                   # match the URL path
        pathType: Prefix
        backend:
          service: {name: api-svc, port: {number: 80}}
      - path: /
        pathType: Prefix
        backend:
          service: {name: shop-svc, port: {number: 80}}
```

Read it as: *"for requests to host `shop.local`: paths starting with `/api` go to `api-svc`, everything else to `shop-svc`."*

## Parts of the spec

### `rules`: host and path
- **`host`**: matched against the HTTP `Host` header. Leave it out and the rule applies to any host. Wildcards like `*.example.com` are allowed in the host field (one label only).
- **`path`** + **`pathType`**:

| pathType | Meaning |
|---|---|
| `Prefix` | Matches the path and everything under it, element by element: `/api` matches `/api` and `/api/x`, **not** `/apix` |
| `Exact` | Matches only that exact path |
| `ImplementationSpecific` | Up to the controller (often regex-like). Avoid unless you need controller-specific behavior |

- When several paths match, the **longest/most specific** match wins (per the Ingress API semantics). On this lab's
  controller, `/api` produced both `location /api/` and `location = /api` in the generated nginx config.
- The backend is a **Service name and port**. The Service must be in the **same namespace as the Ingress**.
  A `ClusterIP` Service is enough: it does not need to be NodePort or LoadBalancer.

### `ingressClassName` and `IngressClass`
Several controllers can run in one cluster. An **IngressClass** names one (`controller: k8s.io/ingress-nginx`),
and `spec.ingressClassName` picks it. Minikube's addon creates an IngressClass called `nginx` and marks it as the
**default** (annotation `ingressclass.kubernetes.io/is-default-class: "true"`), so an Ingress with no class also
goes to it. Older manifests use the annotation `kubernetes.io/ingress.class` instead; that annotation is deprecated
for Ingress, though some controllers still honor it.

```bash
kubectl get ingressclass
```

### Default backend and unmatched requests
Requests that match **no** rule go to a **default backend**. In this lab, nginx answers `404 Not Found` for unknown
hosts. You can set `spec.defaultBackend` to send them to a Service of your choice.

### TLS (HTTPS)
```yaml
spec:
  tls:
  - hosts: [shop.example.com]
    secretName: shop-tls            # a Secret of type kubernetes.io/tls holding the certificate and key
```
The controller terminates TLS: clients speak HTTPS to the controller, and the controller forwards plain HTTP to the
Pods (unless you configure otherwise). Certificates are commonly issued automatically with **cert-manager**
(Let's Encrypt). On AWS you can instead use an **ACM certificate** on the load balancer (see the AWS doc).

### Annotations
Controller-specific features live in **annotations**, which differ per controller. Examples for ingress-nginx:
`nginx.ingress.kubernetes.io/rewrite-target`, `.../ssl-redirect`, `.../proxy-body-size`. AWS LBC uses
`alb.ingress.kubernetes.io/...`. Annotations are **not portable** between controllers, which is one of the
reasons Gateway API exists.

## What happens, step by step

1. You apply an Ingress. (With ingress-nginx, a validating admission webhook checks it first.)
2. The controller sees it (it **watches** Ingress, Service and EndpointSlice objects).
3. It regenerates its configuration: for ingress-nginx, a new nginx config plus a list of backends.
4. A client sends `GET /api` with `Host: shop.local` to the controller's address.
5. The controller matches host and path, picks a Pod from the **Service's live Pod list**, and proxies the request
   **straight to the Pod IP** (observed in this lab: the controller's backend list contained Pod IPs, not the
   Service's ClusterIP).

## Ingress vs the Service types (summary)

| | Layer | Routes by | One entrance for many apps? | TLS in one place? |
|---|---|---|---|---|
| NodePort / LoadBalancer Service | L4 (TCP/UDP) | Port / address | No | No |
| **Ingress** | **L7 (HTTP/HTTPS)** | **Host and path** | **Yes** | **Yes** |

- Ingress is **HTTP/HTTPS only**. For plain TCP/UDP (a database, a game server), use a LoadBalancer Service (or a
  controller-specific TCP feature).
- The controller **itself** still needs an entrance. On a cloud, that is **one** LoadBalancer Service in front of it
  (or, with the AWS Load Balancer Controller, an ALB it creates for you).

## Limits of the Ingress API, and Gateway API

Ingress is simple and widely used, but:
- It only describes HTTP routing. Anything else (header matching, traffic splitting, retries, TCP) is
  controller-specific **annotations**, so configs are not portable.
- One object mixes the infrastructure concern (the entrance) with the app concern (the routes).

**Gateway API** is the newer Kubernetes API designed to replace it: it separates `GatewayClass` / `Gateway`
(infrastructure) from `HTTPRoute` and friends (app teams), and supports more than HTTP. The Kubernetes project
recommends it for new work. This lab teaches Ingress because it is still everywhere and the concepts carry over.
I have not built Gateway API labs here.

## Sources
- Kubernetes blog, [Ingress NGINX Retirement: What You Need to Know](https://kubernetes.io/blog/2025/11/11/ingress-nginx-retirement/) (Nov 2025)
- Kubernetes docs: Ingress, IngressClass, Gateway API (search kubernetes.io for the current pages)
