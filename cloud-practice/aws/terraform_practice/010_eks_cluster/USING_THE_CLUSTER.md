# Using the EKS cluster: connect, switch context, deploy, update, clean up

Commands assume cluster `eks-lab` in `us-east-1` (the defaults in `variables.tf`).
Account IDs are shown as `<ACCOUNT_ID>`.

## 1. Prerequisites

```
aws --version                   # AWS CLI v2
kubectl version --client        # kubectl (keep within +-1 minor of the cluster version)
aws sts get-caller-identity     # confirm WHICH IAM identity you are
```

The IAM identity that ran `terraform apply` is already cluster admin
(`bootstrap_cluster_creator_admin_permissions = true`). Any other identity gets **no access** until you add an access entry (section 7).

## 2. Check the cluster from AWS

```
aws eks describe-cluster --name eks-lab --region us-east-1 \
  --query 'cluster.{status:status,version:version,endpoint:endpoint}'
aws eks list-nodegroups --cluster-name eks-lab --region us-east-1
```

`status` should be `ACTIVE`.

## 3. Connect: write a kubeconfig entry

```
aws eks update-kubeconfig --name eks-lab --region us-east-1
# or: $(terraform output -raw kubeconfig_command)
```

What it does:
- Adds a **cluster**, a **user** and a **context** named
  `arn:aws:eks:us-east-1:<ACCOUNT_ID>:cluster/eks-lab` to `~/.kube/config`.
- **Switches your current context to it.**
- The user entry runs `aws eks get-token` on every call, so kubectl authenticates with your current AWS credentials (no password stored). If your AWS profile/credentials change, kubectl's identity changes too.

Use a short alias and a separate file if you like:
```
aws eks update-kubeconfig --name eks-lab --region us-east-1 --alias eks-lab
aws eks update-kubeconfig --name eks-lab --region us-east-1 --alias eks-lab --kubeconfig ~/.kube/eks-lab.config
KUBECONFIG=~/.kube/eks-lab.config kubectl get nodes     # use only this file in this shell
```

## 4. Contexts: avoid running commands on the wrong cluster

A kubeconfig can hold many clusters (AKS, minikube, EKS...). **Every kubectl command goes to the *current* context**, so check before anything destructive.

```
kubectl config get-contexts            # list; * marks current
kubectl config current-context
kubectl config use-context eks-lab     # switch (name from get-contexts)
kubectl config use-context <other>     # switch back

# one-off without switching:
kubectl --context eks-lab get nodes

# set a default namespace for a context:
kubectl config set-context --current --namespace=demo

# remove the entry when the cluster is destroyed:
kubectl config delete-context eks-lab
kubectl config delete-cluster arn:aws:eks:us-east-1:<ACCOUNT_ID>:cluster/eks-lab
kubectl config delete-user    arn:aws:eks:us-east-1:<ACCOUNT_ID>:cluster/eks-lab
```

Habit: run `kubectl config current-context` before every `delete`/`apply`. Also check `aws sts get-caller-identity` if you use several AWS profiles (`AWS_PROFILE=...`).

## 5. Verify it works

```
kubectl get nodes -o wide                    # 2 nodes, STATUS Ready
kubectl get pods -A                          # coredns, kube-proxy, aws-node (vpc-cni) Running
kubectl get ns
kubectl cluster-info
kubectl auth whoami                          # shows the identity Kubernetes sees (newer kubectl)
kubectl auth can-i '*' '*'                   # yes = cluster admin
```

## 6. Deploy something

```
kubectl create namespace demo
kubectl -n demo create deployment hello --image=nginx --replicas=2
kubectl -n demo get pods -o wide             # see which nodes they landed on
kubectl -n demo logs deploy/hello
kubectl -n demo exec -it deploy/hello -- sh

# reach it without a load balancer (free):
kubectl -n demo port-forward deploy/hello 8080:80    # then open http://localhost:8080

# or expose publicly (creates an AWS load balancer: costs money, ~$0.025/hr+):
kubectl -n demo expose deployment hello --port=80 --type=LoadBalancer
kubectl -n demo get svc hello -w             # wait for EXTERNAL-IP / hostname

# scale and update:
kubectl -n demo scale deployment hello --replicas=3
kubectl -n demo set image deployment/hello nginx=nginx:1.27
kubectl -n demo rollout status deployment/hello
kubectl -n demo rollout undo deployment/hello

# clean up YOUR resources (do this BEFORE terraform destroy):
kubectl -n demo delete svc hello
kubectl delete namespace demo
```

Notes:
- Nodes use public subnets in this lab, so internet-facing load balancers work. The subnets carry the `kubernetes.io/role/elb` tag. Provisioning a load balancer **from a Service** needs the AWS Load Balancer Controller (or the legacy in-tree provider that a plain `type=LoadBalancer` uses, which creates a Classic LB); for Ingress you must install the controller yourself (not part of this lab).
- PersistentVolumeClaims create EBS volumes that Terraform does **not** track; delete PVCs before destroying.

## 7. Give another IAM user/role access

Authentication mode is `API`, so use EKS **access entries**, not the old `aws-auth` ConfigMap.

CLI:
```
aws eks create-access-entry --cluster-name eks-lab --region us-east-1 \
  --principal-arn arn:aws:iam::<ACCOUNT_ID>:user/<name>

aws eks associate-access-policy --cluster-name eks-lab --region us-east-1 \
  --principal-arn arn:aws:iam::<ACCOUNT_ID>:user/<name> \
  --policy-arn arn:aws:eks::aws:cluster-access-policy/AmazonEKSViewPolicy \
  --access-scope type=cluster
```
Common policies: `AmazonEKSClusterAdminPolicy`, `AmazonEKSAdminPolicy`, `AmazonEKSEditPolicy`, `AmazonEKSViewPolicy`. Scope can be `cluster` or limited to namespaces (`type=namespace,namespaces=demo`).

Terraform equivalent: `aws_eks_access_entry` + `aws_eks_access_policy_association`.

List/remove: `aws eks list-access-entries ...`, `aws eks delete-access-entry ...`.

## 8. Updating things

| Want to change | How | Notes |
|---|---|---|
| Node count/size | edit `variables.tf` / tfvars, `terraform apply` | Instance type change = rolling replacement of nodes (`max_unavailable = 1`) |
| Kubernetes version | bump `kubernetes_version`, `terraform apply` | Upgrade **control plane first**, then node group (re-apply) then add-ons. **One minor version at a time**; no downgrade. Check deprecated APIs first |
| Add-on versions | `aws eks describe-addon-versions --addon-name coredns --kubernetes-version 1.36`, set `addon_version` | |
| API access CIDRs | edit `public_access_cidrs` in `03_cluster.tf` (restrict to your IP) | Do it carefully: wrong CIDR locks you out of the public endpoint |
| Add a node group | new `aws_eks_node_group` | See `NODE_GROUPS_NOTES.md` |

Always `terraform plan` first. Look for `-/+` (replace) on cluster or node group.

If your public IP changes and you restricted `public_access_cidrs`, kubectl times out; update the CIDR.

## 9. Troubleshooting

| Symptom | Likely cause / fix |
|---|---|
| `error: You must be logged in to the server (Unauthorized)` | Different IAM identity than the creator; check `aws sts get-caller-identity`; add an access entry |
| kubectl hangs / timeout | `public_access_cidrs` excludes your IP, or no network; check `aws eks describe-cluster ... resourcesVpcConfig` |
| `no context exists` / wrong cluster | `kubectl config get-contexts`, `use-context` (section 4) |
| `exec plugin: ... aws: executable not found` | AWS CLI not on PATH for kubectl |
| Nodes `NotReady` or none | Node role missing a policy, or subnets with no internet route; `aws eks describe-nodegroup ... --query nodegroup.health` |
| Pods `Pending` | No nodes, or not enough CPU/memory/IPs; `kubectl describe pod <name>` (look at Events). `t3.small` has a low pod limit (~11 pods per node) |
| `ImagePullBackOff` | Image name wrong, or no outbound internet from node |
| Service stuck `<pending>` EXTERNAL-IP | Subnet tags missing, or load balancer quota/permissions; `kubectl describe svc` |

Useful debug commands:
```
kubectl describe node <node>
kubectl get events -A --sort-by=.lastTimestamp | tail -20
kubectl -n kube-system logs deploy/coredns
aws eks describe-cluster --name eks-lab --region us-east-1 --query cluster.health
```

## 10. Tear down (order matters)

```
# 1. delete what Kubernetes created in AWS (load balancers, PVC volumes)
kubectl get svc -A | grep LoadBalancer      # delete each: kubectl delete svc ...
kubectl get pvc -A                          # delete PVCs
kubectl get ingress -A                      # delete ingresses

# 2. destroy infra
terraform destroy

# 3. remove local kubeconfig entries (section 4)

# 4. console check: load balancers, ENIs, EBS volumes, security groups tagged eks-lab
```

If `terraform destroy` hangs on the VPC/subnets, a leftover load balancer or ENI from Kubernetes is almost always the reason.

## 11. Cost reminder (~$0.16/hour while it exists)

Control plane ~$0.10/hr + 2 x t3.small ~$0.04/hr + public IPs and EBS ~$0.015/hr. Destroy when finished. Figures are approximate (us-east-1); verify current prices.
