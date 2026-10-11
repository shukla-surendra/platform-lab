# EKS services + egress lab: a 2-hour, low-cost session

A lean EKS cluster (Terraform) plus manifests to practice **Services** (ClusterIP, NodePort, LoadBalancer, ExternalName)
and **egress** (what IP the internet sees, and blocking outbound traffic with NetworkPolicy), with **Spot** nodes and
**no NAT gateway**. Built from your `010_eks_cluster`, which is untouched. The AKS lab in
`cloud-practice/azure/terraform/aks-egress-lab` is also untouched.

## Status: what was and was not checked

| | |
|---|---|
| `terraform validate` | **Passed** |
| `terraform plan` | **Ran cleanly: 18 resources to add.** No NAT gateway, no Elastic IP, no load balancer. **Nothing was applied** |
| AWS state before this lab (`us-east-1`) | **Checked, read-only:** no EKS clusters, no NAT gateways, no load balancers (classic or v2), no Elastic IPs, no running instances. Other regions were **not** checked |
| Kubernetes version `1.36` | **Checked:** the current EKS default, in standard support (support ends 2027-08-02), so no extended-support surcharge |
| VPC CNI network-policy setting | **Checked against AWS's own add-on schema:** `enableNetworkPolicy` (a string-typed boolean) exists in the default vpc-cni version for 1.36 (`v1.22.4-eksbuild.3`) |
| Manifests in `labs/` | YAML-checked only (client-side, local minikube). **Not run on EKS** |
| Expected results below | Written from how these features normally behave. **Not observed on this cluster.** Guesses are marked |
| Costs | From memory. **Check the AWS pricing pages** |

## What gets created (18 resources)

```
VPC 10.30.0.0/16, internet gateway, 2 public subnets (2 AZs), route table
IAM role for the cluster + IAM role for the nodes (4 policy attachments)
EKS cluster "eks-egress-lab"  (Kubernetes 1.36, public + private API endpoint)
managed node group: 2 SPOT nodes (t3.medium / t3a.medium / t2.medium), 20 GB disks, public IPs
add-ons: vpc-cni (with network policy ON), kube-proxy, coredns
```

Differences from your 010 project:

| | 010 | 011 |
|---|---|---|
| Cluster name / VPC range | `eks-lab`, `10.20.0.0/16` | `eks-egress-lab`, `10.30.0.0/16` (no collision) |
| Nodes | On-demand `t3.small` | **Spot**, three similar 2 vCPU / 4 GiB types, 20 GB disks |
| Network policy | Not enabled | **Enabled** on the VPC CNI add-on (egress NetworkPolicy works) |
| NodePort from the internet | n/a | Optional, off by default: one security-group rule for **your IP only** |
| Tags | `Project=eks-lab` | `Project=eks-egress-lab`, `ttl=destroy-after-session`, so leftovers are easy to find |
| Outputs | kubeconfig command | + region, and the **verify-clean** commands |

## Cost: where the money goes

All figures are **approximate and from memory**: verify on the AWS pricing pages before relying on them.

| Item | Cost shape | Keep it low |
|---|---|---|
| **EKS control plane** | Per hour while the cluster exists (the biggest fixed cost, on the order of $0.10/hour) | Create late, destroy promptly |
| 2 Spot nodes | Cents per hour each (Spot is usually much cheaper than on-demand; the price varies) | 1 node if you prefer (`-var node_desired_size=1`) |
| **Public IPv4 addresses** | AWS charges per public IPv4 address per hour: each node has one, plus the load balancer | Fewer nodes, destroy promptly |
| Root disks (2 × 20 GB) | Small | Destroyed with the nodes |
| **LoadBalancer Service** | Per hour while it exists (+ data) | Create, test, **delete**, wait until it's gone |
| NAT gateway | **None** (public subnets) | n/a |

Rough expectation for 2 hours: **on the order of a dollar or less if you destroy at the end.** The risk is **forgetting to destroy**:
the control plane, nodes and any load balancer bill every day. A load balancer left behind can also **block deletion of the VPC**.

### Measured on 2026-10-11 (default settings, us-east-1)

Read-only checks while the lab was running (`aws eks`, `aws ec2 describe-*`, `describe-spot-price-history`):
2 Spot nodes (`t3a.medium`, `t2.medium`), no NAT gateway, no load balancer, no Elastic IP.

| Item | Per hour |
|---|---|
| EKS control plane (standard support; rate from memory) | ~$0.100 |
| 2 Spot nodes at ~$0.015 each (read from Spot price history) | ~$0.030 |
| 2 public IPv4 addresses at $0.005 (rate from memory) | ~$0.010 |
| 2 × 20 GB gp3 root disks (rate from memory) | ~$0.005 |
| **Total** | **~$0.15/hour, ~$3.60/day** |

2 hours is about $0.30. Left on overnight (8 h) about $1.20; a forgotten week about $25. The control plane keeps billing
even if every node is gone: only `terraform destroy` stops it. Each `type: LoadBalancer` Service adds about $0.025/hour
(rate from memory) while it exists.

**Cost guards**
1. Set an **AWS Budget alert** (Billing → Budgets) before you start.
2. Put the **destroy step in your calendar** at minute 105.
3. Always follow the **destroy order** in section 5, and run the verify commands.

## Spot nodes: what happens if one is reclaimed

The managed node group is an Auto Scaling group. If AWS reclaims a Spot node, the group launches a replacement (EKS uses EC2 Capacity
Rebalancing for Spot node groups): **no Karpenter needed**. It only works while Spot capacity exists; that is why three similar
instance types are listed. If none has capacity in any AZ, the node group becomes degraded and the replacement doesn't appear. You can
simulate a reclaim yourself (exercise 1c).

## 2-hour plan

| Minutes | What |
|---|---|
| 0-15 | `terraform apply`, connect `kubectl`, deploy the app |
| 15-50 | **Services:** ClusterIP → NodePort (and the security group) → ExternalName → LoadBalancer |
| 50-70 | **Spot:** kill a node, watch Services and Pods recover |
| 70-100 | **Egress:** per-node egress IPs → NetworkPolicy (4 steps) |
| 100-120 | **Destroy and verify clean** (start at minute 100) |

## 0. Create the cluster

```bash
cd cloud-practice/aws/terraform_practice/011_eks_services_egress
aws sts get-caller-identity --query Arn --output text     # confirm the right AWS identity
terraform init
terraform plan                                            # read it: 18 to add
terraform apply                                           # the EKS control plane takes roughly 10-15 minutes
```

Connect (**the region matters**: your AWS CLI default is not `us-east-1`):
```bash
./connect.sh        # adds the context, switches kubectl to it, shows the nodes (same as: aws eks update-kubeconfig --name eks-egress-lab --region us-east-1)
kubectl config current-context                            # should name eks-egress-lab
kubectl get nodes -o wide                                 # 2 nodes Ready; note INTERNAL-IP and EXTERNAL-IP
kubectl -n kube-system get pods                           # aws-node (vpc-cni), kube-proxy, coredns Running
```
Deploy the app: `kubectl apply -f labs/00-app.yaml` then `kubectl -n lab get pods -o wide` (2 Pods, probably one per node).

A test shell: `kubectl -n lab run t --image=curlimages/curl:8.10.1 --rm -it --restart=Never -- sh`

## 1. Services

### 1a. ClusterIP and NodePort
```bash
kubectl apply -f labs/01-services-clusterip-nodeport.yaml
kubectl -n lab get svc
kubectl -n lab get endpointslice
```
Test from inside the cluster:
```bash
NODE_IP=$(kubectl get nodes -o jsonpath='{.items[0].status.addresses[?(@.type=="InternalIP")].address}')
kubectl -n lab run t --image=curlimages/curl:8.10.1 --rm -i --restart=Never -- curl -s http://web-clusterip
kubectl -n lab run t --image=curlimages/curl:8.10.1 --rm -i --restart=Never -- curl -s http://$NODE_IP:30080
```
**Expect:** `web, answered by pod ...` both times.

**The real-AWS NodePort lesson.** Your nodes have **public** IPs, so can you reach the NodePort from your laptop?
```bash
PUBLIC_IP=$(kubectl get nodes -o jsonpath='{.items[0].status.addresses[?(@.type=="ExternalIP")].address}')
curl -m 5 http://$PUBLIC_IP:30080          # expect: times out, the node's security group does not allow it
```
Now open the range **for your address only** and try again:
```bash
MYIP=$(curl -s https://checkip.amazonaws.com)
terraform apply -var "allow_nodeport_from_cidr=${MYIP}/32"      # adds ONE security-group rule (free)
curl -m 5 http://$PUBLIC_IP:30080          # expect: web, answered by pod ...
curl -m 5 http://<the OTHER node's public IP>:30080     # also works: the port is open on every node
```
This depends on the rule landing on the security group your nodes actually use (the cluster's primary one, which managed node groups use by default).
If it still times out, check with the command in `05_nodeport_access.tf`.
**Remove it afterwards:** `terraform apply` (without the variable) or just destroy at the end. Never use `0.0.0.0/0`.

Compare with minikube: there the problem was Docker Desktop hiding the node IP. Here the node IP is reachable, and it's the **security group** that decides.

### 1b. ExternalName
```bash
kubectl apply -f labs/03-service-externalname.yaml -f labs/11-egress-client.yaml
kubectl -n lab wait --for=condition=Ready pod/egress-client --timeout=120s
kubectl -n lab exec egress-client -- nslookup external-checkip.lab.svc.cluster.local
```
**Expect:** a CNAME to `checkip.amazonaws.com`: only the **name** changes.

### 1c. LoadBalancer (costs while it exists)
```bash
kubectl apply -f labs/02-service-loadbalancer-public.yaml
kubectl -n lab get svc web-lb-public -w                  # EXTERNAL-IP becomes a DNS NAME (an AWS load balancer hostname)
```
```bash
aws elb   describe-load-balancers --region us-east-1 --query 'LoadBalancerDescriptions[].[LoadBalancerName,Scheme]' --output text
aws elbv2 describe-load-balancers --region us-east-1 --query 'LoadBalancers[].[LoadBalancerName,Type]' --output text
curl http://<EXTERNAL-IP hostname>                        # may need a minute for DNS and health checks
```
**Expect:** a hostname (not an IP), and one load balancer appears in the CLI output. Which kind (classic or v2) is worth finding out: it tells you what creates it.
**Delete it when done, and wait until it's gone:**
```bash
kubectl delete -f labs/02-service-loadbalancer-public.yaml
aws elb describe-load-balancers --region us-east-1 --query 'LoadBalancerDescriptions[].LoadBalancerName'     # must become empty
```

## 2. Spot: kill a node on purpose

```bash
kubectl -n lab get pods -o wide                           # which Pods are on which node
aws ec2 describe-instances --region us-east-1 --filters "Name=tag:eks:cluster-name,Values=eks-egress-lab" "Name=instance-state-name,Values=running" \
  --query 'Reservations[].Instances[].[InstanceId,PrivateIpAddress,InstanceLifecycle]' --output text    # InstanceLifecycle should say "spot"
aws ec2 terminate-instances --region us-east-1 --instance-ids <one instance id>                          # simulates losing a node
kubectl get nodes -w                                      # watch: NotReady, then a new node joins (a few minutes)
kubectl -n lab get pods -o wide -w                        # Pods rescheduled; Service endpoints update
```
**Expect:** the node group launches a replacement. While one node is gone, calls to the ClusterIP Service keep working through the other node's Pod (if replicas ran on both).
**Observe:** how long until the new node is Ready? Did the egress IP of that node change (it's a new instance, so a new public IP)? Terminating counts toward
nothing extra: you pay for the replacement while it runs.

## 3. Egress

### 3a. Which IP does the internet see: per node
```bash
kubectl apply -f labs/10-egress-ip-daemonset.yaml
kubectl -n lab logs -l app=egress-ip --prefix --tail=2
kubectl get nodes -o wide                                 # compare with EXTERNAL-IP
```
**Expect (not observed):** one line per node, each showing **that node's public IP**, **different per node**, and matching `EXTERNAL-IP` in `kubectl get nodes -o wide`.
This is the cost of the no-NAT layout: there is **no single stable egress IP**, and a replaced node (exercise 2) gets a new one. A NAT gateway would give one stable IP
(for allow-listing) at the price of an hourly + per-GB charge. That is the trade-off this lab chooses not to pay for.

### 3b. Block egress with NetworkPolicy (4 steps)
`egress-client` (from 1b) is the Pod under test. After each step run:

```bash
kubectl -n lab exec egress-client -- sh -c '
  echo "1) DNS:                 $(nslookup checkip.amazonaws.com 2>&1 | grep -c "Address.*[0-9]") address lines";
  echo -n "2) web (in-cluster):    "; curl -s -m 5 http://web-clusterip || echo BLOCKED;
  echo -n "3) internet (https):    "; curl -s -m 5 https://checkip.amazonaws.com || echo BLOCKED'
```

| Step | Apply | Expected |
|---|---|---|
| 0. Before | (nothing) | DNS, web and internet all work |
| 1. Default deny | `kubectl apply -f labs/20-netpol-default-deny-egress.yaml` | **All three blocked**, even DNS |
| 2. Allow DNS | `kubectl apply -f labs/21-netpol-allow-dns.yaml` | DNS works. Web and internet still blocked |
| 3. Allow the web app | `kubectl apply -f labs/22-netpol-allow-web.yaml` | DNS + **web works**. Internet still blocked |
| 4. Allow HTTPS out | `kubectl apply -f labs/23-netpol-allow-internet-https.yaml` | All three work again |

Notes: policies are **additive** (only "allow" rules); they select Pods by **label** (`app=egress-client`); a policy does nothing without an engine that enforces it.
If step 1 blocks nothing, the VPC CNI policy enforcement isn't active: check `kubectl -n kube-system get pods -l k8s-app=aws-node` and the add-on configuration
(`aws eks describe-addon --cluster-name eks-egress-lab --addon-name vpc-cni --region us-east-1 --query addon.configurationValues`).
The ipBlock `except` list in step 4 is standard NetworkPolicy; whether this engine honors it exactly is something to confirm by testing.
Remove: `kubectl delete -f labs/2*.yaml`.

## 4. Terraform sharpening (plan only, free)

1. `terraform plan -var capacity_type=ON_DEMAND` : which attribute changes? Is the node group replaced?
2. `terraform plan -var node_desired_size=1` : in place or replacement?
3. `terraform plan -var 'node_instance_types=["t3.medium"]'` : what is the downside for Spot (see the variable description)?
4. `terraform plan -var 'allow_nodeport_from_cidr=203.0.113.7/32'` : how many resources get added?
5. `terraform state list` and `terraform output` : find the security group and the verify-clean commands.
6. Add a variable of your own (e.g. extra tags) and run `terraform fmt && terraform validate`.

## 5. Destroy and verify clean (start at minute 100)

**Order matters.** Remove anything that created a load balancer **before** destroying the cluster, otherwise it can be left behind, keep billing, and block VPC deletion.

```bash
kubectl delete namespace lab --wait=true                  # removes the LoadBalancer Service; waits for it
aws elb   describe-load-balancers --region us-east-1 --query 'LoadBalancerDescriptions[].LoadBalancerName'     # must be empty
aws elbv2 describe-load-balancers --region us-east-1 --query 'LoadBalancers[].LoadBalancerName'               # must be empty
terraform destroy                                         # about 10 minutes; type yes
```

Then verify. Each command should return nothing (they are also saved in the `verify_clean_commands` output: run
`terraform output -raw verify_clean_commands` **before** you destroy if you want a copy, because outputs disappear with the state):
```bash
aws eks list-clusters --region us-east-1
aws elb describe-load-balancers --region us-east-1 --query 'LoadBalancerDescriptions[].LoadBalancerName'
aws elbv2 describe-load-balancers --region us-east-1 --query 'LoadBalancers[].LoadBalancerName'
aws ec2 describe-instances --region us-east-1 --filters Name=instance-state-name,Values=running,pending --query 'Reservations[].Instances[].InstanceId'
aws ec2 describe-addresses --region us-east-1 --query 'Addresses[].PublicIp'
aws ec2 describe-vpcs --region us-east-1 --filters Name=tag:Project,Values=eks-egress-lab --query 'Vpcs[].VpcId'
```
Also remove the stale kubeconfig entry: `kubectl config delete-context <the eks-egress-lab context>`.

If `terraform destroy` stalls on the VPC or a subnet, a load balancer or its security group (`k8s-elb-...`) is probably still there: find and delete it, then destroy again.

## Troubleshooting

| Symptom | Likely cause |
|---|---|
| Node group page in the console shows no instances, but EC2 shows 2 | Normal. A managed node group has no list of instances of its own: it owns an Auto Scaling group, which launches plain EC2 instances. Find them in EC2 (filter tag `eks:nodegroup-name = default`), in the Auto Scaling group `eks-default-...`, or with `kubectl get nodes`. (Not verified in the console: if the EKS page still looks empty, check the region selector first.) |
| `kubectl` can't connect / wrong cluster | Wrong context, or you ran an `aws` command in the wrong region (default is not `us-east-1`) |
| Nodes never become Ready | Wait a few minutes. `aws eks describe-nodegroup ... --query nodegroup.health` shows Spot capacity or launch problems |
| Node group `DEGRADED` / no Spot capacity | None of the instance types had Spot capacity in your AZs. Retry later, add types, or `-var capacity_type=ON_DEMAND` |
| `EXTERNAL-IP` stays `<pending>` | Wait 2-3 minutes. Then `kubectl -n lab describe svc web-lb-public` (Events). Check the subnet tags in `01_network.tf` |
| NodePort from laptop times out | The security group rule is missing, or it's not the group on the nodes (1a). Check your `MYIP` |
| NetworkPolicy has no effect | Policy enforcement not active (3b), or the Pod lacks the label `app=egress-client` |
| `terraform apply` fails on add-on config | The `enableNetworkPolicy` value or add-on version: re-check with `aws eks describe-addon-configuration` |
| DaemonSet logs say `FAILED` | A NetworkPolicy from 3b is still applied, or the node has no outbound path |

## Files

| File | Purpose |
|---|---|
| `00_versions_and_provider.tf` ... `05_nodeport_access.tf` | Provider, network, IAM, cluster, nodes + add-ons, optional NodePort rule |
| `variables.tf`, `outputs.tf` | Settings and outputs (incl. verify-clean commands) |
| `connect.sh` | Adds the cluster to `~/.kube/config`, switches kubectl to it, runs `kubectl get nodes`. Switch back: `kubectl config use-context minikube` |
| `.terraform.lock.hcl` | Provider versions, copied from 010 |
| `labs/00-app.yaml` | Namespace `lab` and the `web` Deployment |
| `labs/01-03-*` | Service types |
| `labs/10-11-*` | Egress IP DaemonSet and a client Pod |
| `labs/20-23-*` | The four NetworkPolicy steps |
| `egress-app/` | A separate Deployment-based egress test: see its README |
