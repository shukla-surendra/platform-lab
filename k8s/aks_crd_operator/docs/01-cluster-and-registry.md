# 1. Cluster and registry

`infra/main.tf` provisions everything the rest of the tutorial needs: an AKS
cluster (`aks-crd-lab`) and an ACR (`akscrdlabacr01`) in their own resource
group (`rg-aks-crd-lab`), with the AKS kubelet identity already granted
`AcrPull` on the registry — so no `imagePullSecret` is needed later when the
operator image comes from ACR.

## Apply

```bash
cd k8s/aks_crd_operator/infra
terraform init
terraform apply
```

`azurerm_container_registry.acr` names must be globally unique across all of
Azure. If `akscrdlabacr01` is taken, change the `name` in `main.tf` before
applying — it's referenced nowhere else by hardcoded string, `terraform
output acr_login_server` is how later steps read it back.

## Get credentials

```bash
az aks get-credentials \
  --resource-group "$(terraform output -raw resource_group)" \
  --name "$(terraform output -raw aks_cluster_name)"

kubectl get nodes
```

One `Ready` node is enough — the operator's controller-manager Pod and a
couple of `WebApp`-managed Deployments are lightweight.

## Confirm ACR

```bash
az acr login --name "$(terraform output -raw acr_login_server | cut -d. -f1)"
```

This is just proving your own `az` session can push; the *cluster's* pull
permission comes from the Terraform role assignment, not from this login.

## What's deliberately not here

No ingress, no public IP, no DNS — this tutorial only needs `kubectl
port-forward` to see a `WebApp`-managed Pod respond (step 7). If you want the
managed app reachable from outside the cluster, `k8s/aks_setup/minimul_aks_002`
has the static-IP + `LoadBalancer` pattern to add on top.
