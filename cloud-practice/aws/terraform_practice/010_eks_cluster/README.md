# 010 – EKS cluster, step by step

Goal: understand every piece needed to get a working Kubernetes cluster on AWS.
Nothing here is applied automatically; read, then run it yourself.

## The flow (file order = dependency order)

```
00_versions_and_provider.tf   which provider/version; default tags
variables.tf                  all the knobs
01_network.tf                 VPC → internet gateway → 2 public subnets → route table
02_iam.tf                     cluster role (control plane) + node role (workers)
03_cluster.tf                 aws_eks_cluster = the CONTROL PLANE
04_nodes.tf                   managed node group (workers) + add-ons (vpc-cni, kube-proxy, coredns)
outputs.tf                    endpoint + the kubeconfig command
```

Why this order:
1. **Network first**: the cluster and nodes need subnets (>= 2 AZs).
2. **IAM next**: the control plane and the nodes each need a role they can assume.
3. **Control plane**: the Kubernetes brain; no place to run pods yet.
4. **Nodes**: EC2 workers that join the cluster; this is where pods run.
5. **Add-ons**: networking + DNS components; CoreDNS needs nodes, so it comes last.

Terraform works this out itself from references (`aws_iam_role.cluster.arn`, `aws_subnet.public[*].id`), plus explicit `depends_on` where AWS needs ordering that references can't express.

## Who is who

| Piece | Runs where | Managed by | You pay for |
|---|---|---|---|
| Control plane (API server, etcd, scheduler) | AWS's account, multi-AZ | AWS | ~$0.10/hr per cluster |
| Worker nodes | EC2 in your VPC | AWS patches/replaces (managed node group); you size them | EC2 per hour |
| Pods | On your nodes | Kubernetes | nothing extra |
| Add-ons | Pods on your nodes | EKS (versions via Terraform) | nothing extra |

## Run it

```
terraform init
terraform plan      # read it: ~20 resources
terraform apply     # control plane ~10 min, nodes ~3-5 min
$(terraform output -raw kubeconfig_command)
kubectl get nodes
kubectl get pods -A
```

Try a workload:
```
kubectl create deployment hello --image=nginx --replicas=2
kubectl get pods -o wide
kubectl expose deployment hello --port=80 --type=LoadBalancer   # creates an AWS load balancer (costs money)
kubectl delete svc hello && kubectl delete deployment hello      # delete the Service FIRST before destroy
```

## How access works

- `bootstrap_cluster_creator_admin_permissions = true` makes the IAM identity that ran `terraform apply` a cluster admin.
- `aws eks update-kubeconfig` writes a kubeconfig that calls `aws eks get-token`; Kubernetes sees your IAM identity, EKS maps it via an **access entry** to Kubernetes permissions.
- To add a teammate: create an `aws_eks_access_entry` + `aws_eks_access_policy_association` (e.g. `AmazonEKSClusterAdminPolicy` or `AmazonEKSViewPolicy`).

## Cost (approx., us-east-1; verify)

| Item | ~Cost |
|---|---|
| EKS control plane | $0.10/hr ≈ $73/month |
| 2 × t3.small nodes | ≈ $30/month |
| Public IPv4 addresses (nodes) | ≈ $0.005/hr each |
| Load balancer (if you create a LoadBalancer Service) | ≈ $18+/month each |
| NAT gateway | not used here (would be ≈ $33/month each) |

A day of practice costs a few dollars. **Destroy when done.**
Staying on an old Kubernetes version (extended support) costs much more per hour, so keep `kubernetes_version` in STANDARD support.

## Destroy (important order)

1. Delete anything Kubernetes created in AWS first: `kubectl delete svc <name>` for LoadBalancer Services (and Ingresses). Otherwise load balancers and security groups stay behind, and `terraform destroy` hangs on the VPC.
2. `terraform destroy`
3. Check the console for leftovers (load balancers, ENIs, EBS volumes from PVCs).

Data note: pods are ephemeral. Anything not on a PersistentVolume is lost when pods/nodes go; PVCs create EBS volumes that Terraform does NOT track.

## Production differences (what this lab deliberately skips)

- **Private subnets for nodes + NAT gateways** (or VPC endpoints); public subnets only for load balancers.
- **Restrict `public_access_cidrs`** or make the API private-only (reach via VPN/SSM).
- **IRSA / Pod Identity** so pods get AWS permissions without node-wide credentials.
- **Cluster logging** (`enabled_cluster_log_types`), **secrets encryption** with KMS.
- **Autoscaling** (Cluster Autoscaler or Karpenter), multiple node groups, spot for cheap workloads.
- **Remote encrypted Terraform state** (see `terraform_practice/000_bootstrap_state_bucket`).
- Ingress controller / AWS Load Balancer Controller, monitoring, GitOps.

## Common errors

- `Unsupported Kubernetes version`: check `aws eks describe-cluster-versions`.
- Nodes `NotReady` / node group `CREATE_FAILED`: node role missing a policy, or subnets have no route to the internet (nodes can't reach the EKS API/ECR).
- `kubectl` Unauthorized: you're using a different IAM identity than the one that created the cluster; add an access entry for it.
- Destroy hangs on the VPC/subnet: leftover load balancers or ENIs from Kubernetes.
