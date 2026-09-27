# Terraform: AKS for Services Practice

RG + a bare single-node AKS cluster (Free tier, `Standard_B2s_v2`), made to
answer one question:

> **If I create two Services of `type: LoadBalancer`, do I get two Azure Load Balancers?**

**No.** You get **one** Azure Load Balancer (named `kubernetes`) with **two
public IPs / frontends** on it, not two Load Balancer resources. The
experiment below shows this on a real cluster.

> ⚠️ **Billable**: 1 VM node, plus one Standard public IP per LoadBalancer
> Service. Delete the Services, then run `terraform destroy` when done.

## Usage

```bash
cd cloud-practice/azure/terraform/aks-services
terraform init
terraform apply   # ~4-5 minutes

az aks get-credentials -g "$(terraform output -raw resource_group_name)" \
  -n "$(terraform output -raw cluster_name)" --overwrite-existing
NRG=$(terraform output -raw node_resource_group)   # MC_... group, where the LB lives
```

## The experiment

### 0. Baseline: before any Service

```bash
az network lb list -g $NRG --query "[].{name:name, frontends:length(frontendIPConfigurations), rules:length(loadBalancingRules||\`[]\`)}" -o table
```

```
Name        Frontends    Rules
kubernetes  1            0
```

A `kubernetes` LB **already exists** before you create any Service. AKS creates
it with the cluster because `outbound_type = "loadBalancer"`. Its single
frontend + public IP handles the nodes' **outbound** (SNAT) internet traffic.

### 1. Two public LoadBalancer Services

```bash
kubectl apply -f manifests/app.yaml -f manifests/two-lb-services.yaml
kubectl get svc
```

```
web-lb-a   LoadBalancer   10.0.205.251   4.213.207.68   80:31747/TCP
web-lb-b   LoadBalancer   10.0.121.100   4.187.194.33   8080:30566/TCP
```

On the Azure side:

```
== LBs
Name        Frontends    Rules    Probes
kubernetes  3            2        2          <- still ONE LB

== Public IPs
Name                                         Ip             Service (tag)
5f799ddc-...                                 4.224.100.179  (outbound)
kubernetes-a0c51e8893067460282cf2dcd2d9555c  4.213.207.68   default/web-lb-a
kubernetes-a28085c21f799490a92eefe716315e69  4.187.194.33   default/web-lb-b
```

What each Service actually created:

| Per Service | Azure object |
|---|---|
| 1 public IP | `kubernetes-a<service-uid>` (tagged `k8s-azure-service=<ns>/<name>`) |
| 1 frontend IP config | on the shared `kubernetes` LB |
| 1 LB rule + 1 health probe | per Service port |
| **0** new Load Balancers | reuses `kubernetes` |

Both public IPs return nginx (`curl http://<ip>:<port>` → 200).

### 2. Bonus: an internal LoadBalancer Service

```bash
kubectl apply -f manifests/internal-lb-service.yaml
```

```
Name                 Frontends    Rules
kubernetes           3            2
kubernetes-internal  1            1          <- a second LB appears
```

With the `service.beta.kubernetes.io/azure-load-balancer-internal: "true"`
annotation, the Service gets a **private** IP from the VNet (`10.224.0.5`)
and goes onto a **separate** `kubernetes-internal` LB. An Azure LB can't
mix public and private frontends here, so AKS keeps one LB for each kind.
More internal Services would share `kubernetes-internal` in the same way.

## Why it works this way

- The **cloud-controller-manager** (the Azure cloud provider in AKS) watches
  Services of type LoadBalancer and reconciles the Azure LB to match.
  It uses **one LB per cluster (per public/internal)**, adding frontends, not LBs.
- The Standard LB's backend pool is **all the nodes** (the VMSS). The rules
  use **floating IP** (`enableFloatingIP: true`), so traffic reaches the node
  still addressed to the public IP:port. That's why the rule's backend port
  shows `8080` rather than a NodePort. kube-proxy on the node then forwards
  it to a `web` pod.
- One Azure LB has limits on frontends/rules, so AKS can spread Services
  across several LBs if you turn on the multiple-standard-LB feature
  (`load_balancer_profile` / `--load-balancer-backend-pool-type`, multi-SLB).
  That's opt-in. The default is the single shared LB shown above.
- **AWS contrast:** on EKS with the legacy in-tree provider, each
  LoadBalancer Service gets its own ELB/NLB, so two Services means two
  cloud load balancers (and two bills). On AKS, two Services means one LB
  with two IPs. You pay per public IP and per rule, not per LB.

For a full inventory of every Azure resource this creates, see [`AZURE_RESOURCES.md`](AZURE_RESOURCES.md). For connecting, auth and kubeconfig cleanup, see [`CONNECT_KUBECTL.md`](CONNECT_KUBECTL.md). For the `kubernetes` Service that exists before you deploy anything, see [`DEFAULT_KUBERNETES_SERVICE.md`](DEFAULT_KUBERNETES_SERVICE.md). For every AKS system pod in `kube-system`, and `get all` vs `get all -A`, see [`KUBE_SYSTEM_COMPONENTS.md`](KUBE_SYSTEM_COMPONENTS.md). For deploying a real app (gridwork) with ACR + Helm, see [`DEPLOY_GRIDWORK.md`](DEPLOY_GRIDWORK.md). For how ClusterIPs work (and why one node can serve many), see [`SERVICES_AND_CLUSTER_IPS.md`](SERVICES_AND_CLUSTER_IPS.md). Questions and plain-language answers are collected in [`doubt.md`](doubt.md). A step-by-step Service types lab (problem first, then ClusterIP → NodePort → LoadBalancer) is in [`service-types-lab/`](service-types-lab/SERVICE_TYPES_LAB.md).

## Things to try next

- `kubectl delete svc web-lb-b` → its frontend, rule, probe and public IP disappear; the LB stays.
- Delete **all** Services → `kubernetes` goes back to `Frontends 1, Rules 0` and stays, because outbound traffic needs it. `kubernetes-internal` is deleted entirely, since nothing else uses it (verified).
- Pin a static IP: create a public IP in `$NRG` and set `spec.loadBalancerIP`
  (or the `service.beta.kubernetes.io/azure-pip-name` annotation).
- Two Services sharing **one** IP (different ports):
  `service.beta.kubernetes.io/azure-load-balancer-ipv4` with the same IP on both.
- Compare `type: NodePort` and `ClusterIP`: neither touches the Azure LB at all.

## Clean up

```bash
kubectl delete -f manifests/     # lets cloud-controller-manager remove the IPs/frontends cleanly
terraform destroy
```
