# Plan: expose this on a public IP — three levels, follow in order

Working directory for all of this: `minimul_aks_002/helm/gridwork`. Each level
builds on the last — don't skip to Level 2 without doing Level 1 first, the
Ingress from Level 1 is what Level 2's TLS actually attaches to.

Current state: `frontend.yaml`'s Service is `type: NodePort` — reachable only
via `kubectl port-forward`, nothing else.

---

## Level 0 — `LoadBalancer` Service: a real public IP, no domain, no TLS

**What happens mechanically:** changing the Service's `type` to `LoadBalancer`
is read by Azure's cloud-controller-manager (already running in every AKS
cluster), which calls the Azure API on your behalf and provisions a Standard
Load Balancer + a Public IP resource inside the `MC_rg-aks-dev_aks-dev_...`
managed resource group — the same resource group `minimul_aks_managed_rg.md`
already documents. No new pods, no new Helm chart pieces.

**Step 1** — edit `templates/frontend.yaml`, the Service block only:
```yaml
apiVersion: v1
kind: Service
metadata:
  name: {{ include "pa.fullname" . }}-frontend
  labels:
    {{- include "pa.labels" . | nindent 4 }}
    app: {{ include "pa.fullname" . }}-frontend
spec:
  selector:
    app: {{ include "pa.fullname" . }}-frontend
  ports:
    - port: 80
      targetPort: 80
  type: LoadBalancer   # was: NodePort
```

**Step 2** — apply it:
```bash
helm upgrade gridwork ./gridwork
```

**Step 3** — watch for the public IP to be assigned (takes 30-90s):
```bash
kubectl get svc gridwork-frontend --watch
```
`EXTERNAL-IP` starts as `<pending>`, then becomes a real IP. Ctrl+C once it does.

**Step 4** — verify from anywhere (not just your machine):
```bash
curl -I http://<EXTERNAL-IP>/
```

**Stop here if:** you just need "reachable from the internet" for now — demoing
to yourself, testing from a phone on a different network, etc. Move to Level 1
only when you actually need a second exposed service or a real domain.

---

## Level 1 — Ingress controller: one IP, host-based routing, TLS-ready

**What happens mechanically:** instead of `gridwork-frontend`'s own Service
being `LoadBalancer`, you install **one shared entry point** — the
`ingress-nginx` controller — whose Service is `LoadBalancer`. It gets the
public IP once. An `Ingress` resource (just a routing-rules manifest, no pods
of its own) tells that controller "requests for host X, path Y go to Service
Z." Every future service you expose reuses this same IP instead of costing a
new Load Balancer.

**Step 1** — revert Level 0's change: `gridwork-frontend`'s Service goes back
to a plain `ClusterIP` (no `type:` line needed) — it's now internal-only,
reached through the Ingress controller instead of directly.

**Step 2** — install the ingress-nginx controller (separate Helm release,
not part of this chart — it's cluster-wide infrastructure, shared by anything
you deploy later):
```bash
helm repo add ingress-nginx https://kubernetes.github.io/ingress-nginx
helm repo update
helm install ingress-nginx ingress-nginx/ingress-nginx \
  --namespace ingress-nginx --create-namespace
```

**Step 3** — get its public IP (same `LoadBalancer` mechanism as Level 0, just
on the controller's Service instead of yours):
```bash
kubectl get svc -n ingress-nginx ingress-nginx-controller --watch
```

**Step 4** — point DNS at it. If you own a domain, add an `A` record:
```
gridwork.<your-domain>   A   <EXTERNAL-IP from step 3>
```
No domain yet? Use a free wildcard DNS-to-IP service for now (e.g.
`<ip-with-dashes>.nip.io` resolves to that literal IP with zero setup) —
good enough to test Level 1 and Level 2 before buying a real domain.

**Step 5** — add `templates/ingress.yaml` to this chart:
```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: {{ include "pa.fullname" . }}-ingress
  labels:
    {{- include "pa.labels" . | nindent 4 }}
  annotations:
    nginx.ingress.kubernetes.io/proxy-body-size: "10m"
spec:
  ingressClassName: nginx
  rules:
    - host: {{ .Values.ingress.host | quote }}
      http:
        paths:
          - path: /
            pathType: Prefix
            backend:
              service:
                name: {{ include "pa.fullname" . }}-frontend
                port:
                  number: 80
```

**Step 6** — add to `values.yaml`:
```yaml
ingress:
  host: gridwork.<your-domain-or-nip.io-value>
```

**Step 7** — apply and verify:
```bash
helm upgrade gridwork ./gridwork
curl -I -H "Host: <the host from values.yaml>" http://<ingress public IP>/
```

---

## Level 2 — TLS via cert-manager: the browser-trusted `https://` version

**What happens mechanically:** `cert-manager` (another cluster-wide
controller, its own Helm release) watches for `Certificate` resources. When
it sees one, it requests a free certificate from Let's Encrypt via the
ACME **HTTP-01 challenge** — Let's Encrypt makes an HTTP request to
`http://<your-host>/.well-known/acme-challenge/...` to prove you actually
control that domain, then issues the cert. cert-manager stores it as a
Kubernetes Secret and auto-renews before the 90-day expiry.

**Hard requirement this level adds:** a real DNS `A` record pointing at your
Ingress controller's IP (Level 1, Step 4) — Let's Encrypt cannot validate a
bare IP address, only a resolvable hostname. If you're still on a
`nip.io`-style placeholder, that's fine — it resolves, so it works for
testing — but treat it as temporary.

**Step 1** — install cert-manager:
```bash
helm repo add jetstack https://charts.jetstack.io
helm repo update
helm install cert-manager jetstack/cert-manager \
  --namespace cert-manager --create-namespace \
  --set installCRDs=true
```

**Step 2** — create a `ClusterIssuer` (cluster-wide, apply once with
`kubectl`, not part of this chart — it's not tied to one release):
```yaml
apiVersion: cert-manager.io/v1
kind: ClusterIssuer
metadata:
  name: letsencrypt-prod
spec:
  acme:
    server: https://acme-v02.api.letsencrypt.org/directory
    email: <your-email>
    privateKeySecretRef:
      name: letsencrypt-prod-key
    solvers:
      - http01:
          ingress:
            ingressClassName: nginx
```
```bash
kubectl apply -f cluster-issuer.yaml
```

**Step 3** — update `templates/ingress.yaml` to request a cert and add the
TLS block:
```yaml
metadata:
  name: {{ include "pa.fullname" . }}-ingress
  labels:
    {{- include "pa.labels" . | nindent 4 }}
  annotations:
    nginx.ingress.kubernetes.io/proxy-body-size: "10m"
    cert-manager.io/cluster-issuer: letsencrypt-prod
spec:
  ingressClassName: nginx
  tls:
    - hosts:
        - {{ .Values.ingress.host | quote }}
      secretName: {{ include "pa.fullname" . }}-tls
  rules:
    - host: {{ .Values.ingress.host | quote }}
      http:
        paths:
          - path: /
            pathType: Prefix
            backend:
              service:
                name: {{ include "pa.fullname" . }}-frontend
                port:
                  number: 80
```

**Step 4** — apply and watch the cert get issued:
```bash
helm upgrade gridwork ./gridwork
kubectl get certificate    # READY should flip to True within ~1-2 min
```

**Step 5** — verify:
```bash
curl -I https://<your host>/
```
Browser-trusted padlock, no warnings.

---

## What's still not covered even after Level 2

- **`allowedOrigins: "*"`** in `values.yaml`'s backend env — fine while nginx
  is the only thing calling the backend, but worth tightening to the real
  host once one exists.
- **Rate limiting / WAF** at the edge — ingress-nginx has annotations for
  basic rate limiting; a real WAF is Azure Application Gateway territory, a
  different (and paid) path from everything above.
- **A stable IP across ingress-nginx reinstalls** — deleting and recreating
  the `ingress-nginx-controller` Service can hand you a *new* public IP.
  Azure has a way to pre-allocate a static Public IP and pin the Service to
  it (`service.beta.kubernetes.io/azure-load-balancer-resource-group` +
  `loadBalancerIP` annotations) — worth doing once you're on a real domain,
  so the DNS record doesn't go stale after routine maintenance.
