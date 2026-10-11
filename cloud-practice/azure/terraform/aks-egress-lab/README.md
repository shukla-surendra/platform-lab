# AKS egress lab: a 2-hour, low-cost session on Services and egress

A lean AKS cluster (Terraform) plus manifests to practice **Services** (ClusterIP, NodePort, LoadBalancer public and
internal, ExternalName) and **egress** (what IP the internet sees, and blocking outbound traffic with NetworkPolicy).

> **I assumed AKS (Azure).** Your last message said "aks" after we'd been discussing EKS. AKS is also the cheaper
> choice for this: its control plane is free, and outbound traffic uses the cluster's own load balancer, so there is
> no NAT gateway bill. If you meant EKS, this is not that.

## Status: what was and was not checked

| | |
|---|---|
| `terraform validate` | **Passed** (azurerm 5.7.0) |
| `terraform plan` | **Ran cleanly**, creates: resource group, cluster, random suffix. **Nothing was applied** |
| Azure state before this lab | **Checked:** no AKS clusters, no container registries, no public IPs (only the free default `NetworkWatcherRG`). The earlier `aks-services` lab is gone |
| Manifests in `labs/` | YAML-checked only (client-side, against a local minikube). **Not run on AKS** |
| Expected outputs below | Written from how these features normally behave. **Not observed on this cluster.** Where one is a guess, it says so |
| Costs | From memory. **Check the Azure pricing pages** |

## What gets created

```
rg-aks-egress-xxxxx                      your resource group
  └─ aks-egress-xxxxx                    the cluster: Free tier, 1 node (Standard_B2s_v2), Azure CNI overlay + Cilium
MC_rg-aks-egress-xxxxx_..._centralindia  created BY AKS: the VM, disk, the standard load balancer, the outbound public IP
```

Compared with your earlier `aks-services` project, this one:
- **drops the container registry** and its role assignment (nothing here pulls from a private registry)
- **uses variables** for region, VM size, node count, network policy and the number of outbound IPs
- **runs lab Pods on the single node** (no `only_critical_addons`)
- **enables Cilium** (`network_data_plane` and `network_policy`) so NetworkPolicy **egress** rules are enforced
- **makes the egress path explicit** (`outbound_type = "loadBalancer"`, `managed_outbound_ip_count`) and outputs it
- **outputs the `az aks get-credentials` command** and the outbound public IP IDs

## Cost: where the money goes, and how to keep it minimal

All figures are **approximate and from memory**: verify on the Azure pricing pages before relying on them.

| Item | Cost shape | What to do |
|---|---|---|
| AKS control plane | **Free tier: no hourly charge** | Nothing |
| 1 × `Standard_B2s_v2` node | Per hour while it exists (cents per hour) | Keep 1 node. Destroy at the end |
| Node OS disk | Small, per day | Goes away on destroy |
| The cluster's standard load balancer + 1 **outbound public IP** | Hourly charge, plus data processing | Created automatically. Goes away on destroy |
| Each **public** `LoadBalancer` Service | **An extra public IP per Service, per hour** | Create one at a time, test, **delete it** |
| **Internal** `LoadBalancer` Service | No public IP | Cheap. Prefer it for practice |
| Outbound data | Per GB (small for this lab) | Don't download large files |
| Container registry | **None in this lab** | |

Rough expectation for a 2-hour session: **on the order of a dollar or less, if you destroy at the end.** The big risk is
**forgetting to destroy**: a running cluster, its load balancer and public IPs keep billing every day. Last time a lab was left running
for two weeks (it was cleaned up since, which I verified).

**Cost guards**
1. Set a **budget alert** in Azure (Cost Management → Budgets), for example at a few dollars, before you start.
2. Put the **destroy step in your calendar** now, at minute 105 of the session.
3. If you only need a break: `az aks stop -g <rg> -n <cluster>` stops the nodes (the control plane is free). Disks and public IPs still bill. Destroy is cheaper.
4. After destroying, **verify** (checklist at the end).

## 2-hour plan

| Minutes | What |
|---|---|
| 0-15 | `terraform apply`, connect `kubectl`, deploy the app |
| 15-50 | **Services:** ClusterIP → NodePort → internal LB → public LB |
| 50-95 | **Egress:** what IP the internet sees → ExternalName → NetworkPolicy (4 steps) |
| 95-105 | Optional Terraform exercises (**plan only**) |
| 105-120 | **Destroy and verify clean** |

## 0. Create the cluster

```bash
cd cloud-practice/azure/terraform/aks-egress-lab
az account show -o table                 # confirm you're on the right subscription
terraform init
terraform plan                           # read it: 3 resources
terraform apply                          # about 5-10 minutes (AKS creation time varies); type yes
```

```bash
eval "$(terraform output -raw get_credentials)"       # runs: az aks get-credentials ... --overwrite-existing
kubectl config current-context                        # should be the new cluster
kubectl get nodes -o wide                             # 1 node Ready
kubectl -n kube-system get pods -l k8s-app=cilium     # the Cilium agent Pod(s) running (needed for NetworkPolicy)
```

Deploy the app: `kubectl apply -f labs/00-app.yaml` then `kubectl -n lab get pods` (2 Pods Running).

A quick test shell for later: `kubectl -n lab run t --image=curlimages/curl:8.10.1 --rm -it --restart=Never -- sh`

## 1. Services

### 1a. ClusterIP and NodePort (free)
```bash
kubectl apply -f labs/01-services-clusterip-nodeport.yaml
kubectl -n lab get svc
kubectl -n lab get endpointslice               # the Pod IPs behind the Services
```
Test **from inside the cluster**:
```bash
kubectl -n lab run t --image=curlimages/curl:8.10.1 --rm -i --restart=Never -- curl -s http://web-clusterip
NODE_IP=$(kubectl get nodes -o jsonpath='{.items[0].status.addresses[?(@.type=="InternalIP")].address}')
kubectl -n lab run t --image=curlimages/curl:8.10.1 --rm -i --restart=Never -- curl -s http://$NODE_IP:30080
```
**Expect:** both answer `web, answered by pod ...`. AKS nodes normally have **private IPs only**, so a NodePort is reachable from
inside the VNet (here: from a Pod), **not** from your laptop. That is different from what you may expect from a cloud NodePort. (From general
knowledge of AKS defaults: confirm with `kubectl get nodes -o wide`: `EXTERNAL-IP` should be `<none>`.)

### 1b. Internal LoadBalancer (cheap)
```bash
kubectl apply -f labs/03-service-loadbalancer-internal.yaml
kubectl -n lab get svc web-lb-internal -w        # wait for EXTERNAL-IP: a PRIVATE address from your network
```
**Expect:** an address like `10.x.x.x`. Test from a Pod: `curl http://<that ip>`. No public IP was created for this one.

### 1c. Public LoadBalancer (costs while it exists)
```bash
kubectl apply -f labs/02-service-loadbalancer-public.yaml
kubectl -n lab get svc web-lb-public -w          # EXTERNAL-IP goes <pending> then a public address (1-3 minutes)
curl http://<EXTERNAL-IP>                        # from your laptop this time
```
**Expect:** works from your laptop. Look in Azure: `az network public-ip list -g <node_resource_group> -o table` now shows **one more
public IP**. **Delete it when done:** `kubectl delete -f labs/02-service-loadbalancer-public.yaml`, and confirm the IP disappears.

Questions to answer for yourself: why does the NodePort test need a Pod while the public LB test does not? Which of the three Services
cost money? What did `kubectl get svc` show in `PORT(S)` for the NodePort Service?

## 2. Egress

### 2a. What IP does the internet see?
```bash
kubectl apply -f labs/10-egress-ip-check.yaml
kubectl -n lab wait --for=condition=complete job/egress-ip-check --timeout=90s
kubectl -n lab logs job/egress-ip-check
```
Now find Azure's outbound IP and compare:
```bash
terraform output egress_public_ip_ids
az network public-ip show --ids <the id above> --query ipAddress -o tsv
```
**Expect:** the two addresses are **identical**: every Pod's outbound traffic leaves through the cluster's load balancer's outbound IP. (This is the
standard behavior of `outbound_type = loadBalancer`. I did not observe it on this cluster.)

Experiments:
- Delete and re-run the Job (`kubectl -n lab delete job egress-ip-check` then apply again). **Same IP?** Expected: yes: it's the load balancer's, not the Pod's or node's.
- Create the **public LoadBalancer Service** (1c) and re-run the Job. **Does the egress IP change?** My expectation: no (the Service's public IP is for **inbound** traffic; outbound uses the outbound IP configuration). Observe it rather than trust me.
- Why this matters: an external system that allow-lists your cluster needs **one stable IP**. Here it is the outbound IP. It lasts as long as the cluster does.

### 2b. ExternalName: a name for something outside
```bash
kubectl apply -f labs/04-service-externalname.yaml
kubectl apply -f labs/11-egress-client.yaml
kubectl -n lab wait --for=condition=Ready pod/egress-client --timeout=90s
kubectl -n lab exec egress-client -- nslookup external-checkip.lab.svc.cluster.local
```
**Expect:** a CNAME to `checkip.amazonaws.com`. Note that the call still leaves via the same outbound IP: ExternalName only changes the **name**.

### 2c. Block egress with NetworkPolicy (4 steps)
`egress-client` is the Pod under test. Run each step, then test.

```bash
# test helper: run this after each step
kubectl -n lab exec egress-client -- sh -c '
  echo "1) DNS:                 $(nslookup checkip.amazonaws.com 2>&1 | grep -c "Address.*[0-9]") address lines";
  echo -n "2) web (in-cluster):    "; curl -s -m 5 http://web-clusterip || echo BLOCKED;
  echo -n "3) internet (https):    "; curl -s -m 5 https://checkip.amazonaws.com || echo BLOCKED'
```

| Step | Apply | Expected result of the test |
|---|---|---|
| 0. Before any policy | (nothing) | DNS works, web works, internet works |
| 1. Default deny | `kubectl apply -f labs/20-netpol-default-deny-egress.yaml` | **All three blocked**, even DNS (names don't resolve) |
| 2. Allow DNS | `kubectl apply -f labs/21-netpol-allow-dns.yaml` | DNS works again. Web and internet **still blocked** |
| 3. Allow the web app | `kubectl apply -f labs/22-netpol-allow-web.yaml` | DNS works, **web works**, internet still blocked |
| 4. Allow HTTPS to the internet | `kubectl apply -f labs/23-netpol-allow-internet-https.yaml` | All three work again |

Things to notice:
- Policies are **additive**: each `allow` adds to the (empty) default-deny. There are no "deny" rules, only "allow".
- A policy selects Pods by **label** (`app=egress-client`). Pods without that label are not affected.
- Policies need an **engine** that enforces them. On a cluster without one, the objects apply but nothing is blocked. That's why this cluster enables Cilium.
- Remove them: `kubectl delete -f labs/2*.yaml`.
- If `step 1` does not block anything, the policy engine is not working: check `kubectl -n kube-system get pods -l k8s-app=cilium`.

## 3. Terraform sharpening (optional, plan only, costs nothing)

Do these with `terraform plan`. **Don't apply** them during the cost-sensitive session.

1. `terraform plan -var outbound_ip_count=2` : read the diff. Is it an update in place, or a replacement? What would it do to the egress IP you recorded?
2. `terraform plan -var enable_network_policy=false` : what changes in `network_profile`? Is a cluster **replacement** needed? (Look for "forces replacement".)
3. `terraform plan -var vm_size=Standard_B2ms` : what happens to the node pool?
4. `terraform state list` and `terraform show | head -60` : find where the load balancer is. (Hint: it is not in your state: AKS creates it in the `MC_` group.)
5. `terraform output` : read the outputs. Which ones help `kubectl`, which help you check the bill?
6. Add a `variable "tags"` or an extra output yourself and run `terraform fmt && terraform validate`.

## 4. Destroy and verify clean (do this at minute 105)

```bash
kubectl delete namespace lab --wait=false           # releases any LoadBalancer Services first
terraform destroy                                   # a few minutes; type yes
```

Verify **nothing is left** (all should be empty, apart from the free default `NetworkWatcherRG`):

```bash
az group list -o table
az aks list -o table
az network public-ip list -o table
az network lb list -o table
```

Clean your local kubeconfig (the cluster is gone but its entry stays):
```bash
kubectl config get-contexts
kubectl config delete-context <the aks-egress context>
```

## Troubleshooting

| Symptom | Likely cause |
|---|---|
| `terraform apply` rejects the network settings | The Cilium combination may not be accepted for your Kubernetes version or region. Re-run with `-var enable_network_policy=false` (you lose egress NetworkPolicy), or check the Azure CNI Powered by Cilium docs |
| Quota / `SkuNotAvailable` for the VM size | Pick another size with `-var vm_size=...` or another region. `az vm list-skus --location centralindia --size Standard_B2s_v2` shows restrictions (it had none when I checked) |
| `EXTERNAL-IP` stays `<pending>` | Wait a few minutes. If it persists: `kubectl -n lab describe svc <name>` (look at Events) |
| NodePort test times out | Use the node's **InternalIP** from a **Pod**, not your laptop |
| NetworkPolicy does nothing | No enforcing engine: check the Cilium Pods. Or the Pod doesn't carry the label `app=egress-client` |
| Egress Job `FAILED to reach the internet` | A policy from 2c is still applied, or the node has no outbound path |

## Files

| File | Purpose |
|---|---|
| `variables.tf`, `main.tf`, `outputs.tf` | The cluster |
| `.terraform.lock.hcl` | Provider versions (azurerm 5.7.0), copied from `aks-services` |
| `labs/00-app.yaml` | Namespace `lab` and the `web` Deployment |
| `labs/01-04-*` | The Service types |
| `labs/10-11-*` | Egress IP check and a client Pod |
| `labs/20-23-*` | The four NetworkPolicy steps |
