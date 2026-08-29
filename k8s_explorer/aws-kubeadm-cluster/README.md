# kubeadm on EC2 — a self-managed Kubernetes cluster, without EKS

**Goal:** understand what EKS's control plane actually does for you, by doing it
yourself on 3 small EC2 instances.
**Cost while running:** ≈ $0.08/hour for all 3 nodes combined (no NAT Gateway — see
`terraform/network.tf`). Fully zeroed out by `terraform destroy` when you're done for
the day.
**Read first:** [`docs/CONCEPTS.md`](docs/CONCEPTS.md) — this SOP assumes you already
know what a control-plane component, kubelet, and CNI plugin are *for*. Don't start
here if you haven't read that yet.

This is a manual, hands-typed bootstrap on purpose — every step below is something a
managed control plane (EKS) would have done invisibly. Automating it with `user_data`/
Ansible is a reasonable follow-up exercise *after* you've done it by hand at least once,
not before.

---

## 0. Prerequisites

- AWS credentials configured (`aws sts get-caller-identity` should return your account).
- Terraform >= 1.5.
- Your own public IP: `curl -s ifconfig.me` — you'll need this as a `/32` CIDR.

## 1. Provision the infrastructure

```bash
cd terraform
terraform init
terraform apply -var="allowed_ssh_cidr=<YOUR_IP>/32"
```

Review the plan before typing `yes` — it should show **15 resources to add**: a VPC,
subnet, route table, internet gateway, security group (+ 3 rules), an SSH key pair (+
the local private key file), and 3 EC2 instances (1 control-plane, 2 workers).

✅ On success, note the outputs — `ssh_control_plane` and `ssh_workers` are ready-to-paste
SSH commands. Keep this terminal's outputs visible; you'll be copying from them for the
next several steps.

> **This step bills your AWS account from this point on.** Nothing here is destructive
> or hard to undo — `terraform destroy` at the end reverses all of it — but it isn't
> free while it's up, per the cost breakdown above.

## 2. On EVERY node (control-plane AND both workers) — repeat this whole section 3 times

SSH in using the command from the `terraform output`, then run all of the following on
each node before moving on to step 3.

### 2a. Disable swap

```bash
sudo swapoff -a
sudo sed -i '/ swap / s/^/#/' /etc/fstab
```

kubelet refuses to start with swap enabled — Kubernetes' resource accounting assumes
memory limits are real limits, which swap would undermine. The `sed` edit makes this
survive a reboot; without it, swap silently comes back on next boot and kubelet stops.

### 2b. Load required kernel modules and sysctls

```bash
cat <<EOF | sudo tee /etc/modules-load.d/k8s.conf
overlay
br_netfilter
EOF
sudo modprobe overlay
sudo modprobe br_netfilter

cat <<EOF | sudo tee /etc/sysctl.d/k8s.conf
net.bridge.bridge-nf-call-iptables  = 1
net.bridge.bridge-nf-call-ip6tables = 1
net.ipv4.ip_forward                 = 1
EOF
sudo sysctl --system
```

`br_netfilter` lets iptables see traffic crossing a Linux bridge — without it, kube-proxy's
iptables rules silently don't apply to Pod traffic. `ip_forward=1` is what lets this node
route traffic between Pods and out to the rest of the cluster at all.

✅ `sudo sysctl net.ipv4.ip_forward` should print `net.ipv4.ip_forward = 1`.

### 2c. Install and configure containerd

```bash
sudo apt-get update
sudo apt-get install -y containerd

sudo mkdir -p /etc/containerd
containerd config default | sudo tee /etc/containerd/config.toml
sudo sed -i 's/SystemdCgroup = false/SystemdCgroup = true/' /etc/containerd/config.toml
sudo systemctl restart containerd
sudo systemctl enable containerd
```

The `SystemdCgroup` edit matters more than it looks: kubelet and containerd both need to
agree on which cgroup driver manages resource limits (`systemd` vs `cgroupfs`). A
mismatch here is a classic kubeadm-init failure that gives a confusing error far removed
from "check your cgroup driver" — fixing it *before* installing kubeadm avoids ever
hitting that.

### 2d. Install kubeadm, kubelet, kubectl

```bash
sudo apt-get install -y apt-transport-https ca-certificates curl gpg
sudo mkdir -p /etc/apt/keyrings

curl -fsSL https://pkgs.k8s.io/core:/stable:/v1.31/deb/Release.key \
  | sudo gpg --dearmor -o /etc/apt/keyrings/kubernetes-apt-keyring.gpg

echo 'deb [signed-by=/etc/apt/keyrings/kubernetes-apt-keyring.gpg] https://pkgs.k8s.io/core:/stable:/v1.31/deb/ /' \
  | sudo tee /etc/apt/sources.list.d/kubernetes.list

sudo apt-get update
sudo apt-get install -y kubelet kubeadm kubectl
sudo apt-mark hold kubelet kubeadm kubectl
```

`apt-mark hold` stops an unattended `apt upgrade` from silently jumping Kubernetes
versions on you — version skew between kubeadm/kubelet/kubectl and the cluster is a real
compatibility surface, not a formality.

✅ At this point `kubelet` will be installed but **crash-looping** — that's expected and
correct. It has no cluster to join yet; `kubeadm init`/`join` in the next steps are what
give it something to do. Confirm with `systemctl status kubelet` — you should see
repeated restart attempts, not a clean "inactive."

**Checkpoint before continuing: all 3 nodes must have completed 2a-2d.**

## 3. On the CONTROL-PLANE node only

### 3a. Initialize the cluster

```bash
PRIVATE_IP=$(hostname -I | awk '{print $1}')
sudo kubeadm init \
  --pod-network-cidr=10.244.0.0/16 \
  --apiserver-advertise-address="$PRIVATE_IP"
```

`--pod-network-cidr` must match what your CNI plugin expects — `10.244.0.0/16` is
Flannel's hardcoded default (step 3c installs Flannel; if you ever swap in Calico or
another CNI, this value and that plugin's manifest need to agree with each other, or
Pods get IPs the CNI doesn't recognize as its own).

This takes a minute or two. **Save the full `kubeadm join ...` command it prints at the
end** — you need it verbatim on both workers in step 4. If you lose it, regenerate it any
time with `kubeadm token create --print-join-command` (run on the control-plane).

✅ Success output ends with "Your Kubernetes control-plane has initialized successfully!"

### 3b. Set up your kubeconfig

```bash
mkdir -p "$HOME"/.kube
sudo cp -i /etc/kubernetes/admin.conf "$HOME"/.kube/config
sudo chown "$(id -u)":"$(id -g)" "$HOME"/.kube/config
```

This is the credential `kubectl` uses — copying the admin one here is fine for a lab;
production practice hands out narrower-scoped kubeconfigs per user/service instead.

✅ `kubectl get nodes` should now work and show one node — `NotReady` is expected right
now, because there's no CNI yet (next step).

### 3c. Install the Flannel CNI

```bash
kubectl apply -f https://github.com/flannel-io/flannel/releases/latest/download/kube-flannel.yml
```

✅ Give it 30-60 seconds, then `kubectl get nodes` should flip to `Ready`, and
`kubectl get pods -n kube-flannel` should show a Flannel Pod `Running`.

## 4. On EACH WORKER node

Paste the exact `kubeadm join` command you saved from step 3a, with `sudo`:

```bash
sudo kubeadm join <control-plane-ip>:6443 \
  --token <token> \
  --discovery-token-ca-cert-hash sha256:<hash>
```

✅ Ends with "This node has joined the cluster." Repeat on the second worker.

## 5. Verify the cluster, from the control-plane

```bash
kubectl get nodes -o wide
kubectl get pods -A
```

✅ **All 3 nodes `Ready`.** In `kube-system`, `coredns` (2 replicas), `kube-proxy` (one
per node), and in `kube-flannel`, one Flannel Pod per node — all `Running`. If a node
stays `NotReady` for more than ~a minute after joining, SSH into it and check
`sudo journalctl -u kubelet -f` for the actual error rather than guessing.

## 6. Smoke test — prove cross-node Pod networking actually works

```bash
kubectl create deployment web --image=nginx --replicas=2
kubectl expose deployment web --port=80 --type=NodePort
kubectl get pods -o wide          # confirm the 2 Pods landed on DIFFERENT nodes
kubectl get svc web               # note the NodePort, e.g. 3xxxx
```

Then, from your **local machine** (not SSH'd in):

```bash
curl http://<either-worker-public-ip>:<nodeport>/
```

✅ Returns nginx's welcome page — **from either worker's IP, regardless of which node
the Pod you hit is actually running on.** That's kube-proxy's Service routing and
Flannel's cross-node Pod networking both working together, the exact mechanism
`docs/CONCEPTS.md` describes rather than just asserts.

## 7. Tear it down

```bash
cd terraform
terraform destroy
```

✅ Confirm with `aws ec2 describe-instances --filters "Name=tag:Project,Values=kubeadm-poc"`
— should return no running instances. This is what actually stops billing; stopping
(not terminating) instances instead would still accrue EBS charges indefinitely.

---

## Troubleshooting quick-reference

| Symptom | Likely cause |
| --- | --- |
| `kubeadm init` fails preflight on memory | Instance is smaller than t3.small — check `terraform.tfvars`/`-var instance_type=...` |
| Node stuck `NotReady` after joining | CNI not installed yet, or `--pod-network-cidr` doesn't match the CNI's expected range |
| `kubeadm join` fails with a certificate error | Token expired (default TTL 24h) — regenerate with `kubeadm token create --print-join-command` on the control-plane |
| `curl` to NodePort hangs from your machine | Security group only allows SSH (22) — check `terraform/security_group.tf`'s ingress rules cover the NodePort range, or that you're hitting the right node's public IP |
| kubelet crash-looping and never recovers even after join | Check `SystemdCgroup = true` actually landed in `/etc/containerd/config.toml` (step 2c) — a cgroup driver mismatch is the most common silent cause |
