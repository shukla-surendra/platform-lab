This builds on `minimul_aks_001/main.tf` by adding one new resource (plus a
supporting data source and output): a static Public IP reserved ahead of
time for whatever `LoadBalancer`-type Service ends up exposing the app
publicly — see `helm/gridwork/PUBLIC_EXPOSURE_PLAN.md` for the three-level
plan this feeds into.

## Static Public IP

```
data "azurerm_resource_group" "aks_node_rg" {
  name = azurerm_kubernetes_cluster.aks.node_resource_group
}

resource "azurerm_public_ip" "ingress" {
  name                = "pip-aks-dev-ingress"
  resource_group_name = data.azurerm_resource_group.aks_node_rg.name
  location            = data.azurerm_resource_group.aks_node_rg.location
  allocation_method   = "Static"
  sku                 = "Standard"
}

output "ingress_public_ip" {
  value = azurerm_public_ip.ingress.ip_address
}
```

Without this, a `LoadBalancer` Service (or the ingress-nginx controller's own
Service) gets Azure to hand it *whatever* public IP happens to be free at
creation time — fine for a quick test, but that IP changes if the Service is
ever deleted and recreated (a `helm uninstall`/reinstall, moving to a
different ingress controller, etc.), which silently breaks any DNS record
already pointed at the old one.

**Why a `data` source instead of just creating it in `rg-aks-dev` directly:**
Kubernetes' cloud-controller-manager creates `LoadBalancer` IPs inside AKS's
own auto-managed node resource group
(`MC_rg-aks-dev_aks-dev_centralindia` — the one `minimul_aks_managed_rg.md`
already documents), not the resource group Terraform itself defined. Terraform
doesn't manage that resource group as one of its own resources — it's owned
and named by AKS — so `data "azurerm_resource_group" "aks_node_rg"` reads its
name off the cluster (`node_resource_group` is an attribute AKS exposes)
rather than hardcoding the generated `MC_...` string. Creating the IP inside
that same resource group means the eventual Kubernetes Service only needs a
`loadBalancerIP: <ip>` annotation — no need for the extra
`service.beta.kubernetes.io/azure-load-balancer-resource-group` annotation
that cross-resource-group pinning would otherwise require.

**Why `sku = "Standard"`, not `"Basic"`:** AKS provisions a Standard SKU Load
Balancer by default for `LoadBalancer` Services on any reasonably current
cluster, and Azure does not allow mixing Basic and Standard SKU IPs/LBs in
the same setup — a Basic IP here would simply fail to attach.

**Missing piece / what still has to happen for this IP to actually get
used:** creating it here doesn't wire anything up by itself — the Kubernetes
side (whichever Service ends up being `type: LoadBalancer`, either
`gridwork-frontend` directly at Level 0, or the ingress-nginx controller's
Service at Level 1) still needs:

```yaml
metadata:
  annotations:
    service.beta.kubernetes.io/azure-load-balancer-ipv4: <the reserved IP>
spec:
  type: LoadBalancer
  loadBalancerIP: <the reserved IP>   # deprecated but still widely used; the
                                       # annotation above is the newer form
```

Run `terraform apply` first, read the IP back with `terraform output
ingress_public_ip`, then paste it into whichever Service manifest needs it.

## What else you could add here

- **DNS as Terraform** (`azurerm_dns_zone` / `azurerm_dns_a_record`) pointing
  a real subdomain at `ingress_public_ip` — currently this file only reserves
  the IP, DNS itself is still a manual step (registrar UI, or a `nip.io`
  placeholder per the exposure plan).
- **A firewall/NSG rule restricting inbound to 80/443 only** — right now
  nothing in this Terraform config defines NSG rules at all (AKS's
  auto-managed one currently allows whatever the Kubernetes Service layer
  opens); tightening that explicitly is a defense-in-depth step, not a
  functional requirement.
