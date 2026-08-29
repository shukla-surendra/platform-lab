# Concepts: What EKS Actually Does For You (and What You're About to Do By Hand)

Read this before touching AWS. The whole point of this exercise is understanding what a
managed control plane like EKS hides — that only lands if you know what each piece is
*for* before you type the command that creates it.

## The two halves of a Kubernetes cluster

Every Kubernetes cluster, managed or not, is made of the same two kinds of node:

**Control-plane components** (the "brain" — decides *what should happen*):
- **`kube-apiserver`** — the only component anything else talks to. Every `kubectl`
  command, every kubelet check-in, every internal component's read/write goes through
  this one HTTP(S) API. Nothing in Kubernetes talks to etcd directly except the API
  server.
- **`etcd`** — a distributed key-value store. This is the *entire* cluster state —
  every Pod, Deployment, Service, Secret, all of it, as key-value pairs. If etcd is gone,
  the cluster's state is gone (which is why real deployments run etcd on 3 or 5 nodes,
  never 1 — it uses the Raft consensus protocol, which needs a majority quorum to keep
  operating and to survive losing a node).
- **`kube-scheduler`** — watches the API server for Pods with no node assigned yet,
  decides which node they should run on (based on resource requests, affinity rules,
  taints/tolerations), and writes that decision back through the API server. It does
  *not* actually start the Pod — it only assigns it.
- **`kube-controller-manager`** — runs the reconciliation loops that make Kubernetes
  "declarative": watches the actual state, compares it to the desired state (e.g. "a
  Deployment says 3 replicas, only 2 Pods exist"), and takes action to close the gap.

**Worker-node components** (the "hands" — actually run things):
- **`kubelet`** — runs on every node (control-plane nodes usually run one too). Watches
  the API server for Pods assigned to *its* node, and tells the container runtime to
  actually start/stop containers to match. Reports node and Pod status back.
- **`kube-proxy`** — implements Kubernetes Services: maintains network rules (iptables
  or IPVS) on each node so traffic to a Service's stable virtual IP gets routed to one
  of the actual Pod IPs behind it, even as Pods come and go.
- **A container runtime** (`containerd` here) — actually pulls images and runs
  containers. Kubernetes talks to it via the CRI (Container Runtime Interface), not
  directly — this is why containerd, CRI-O, and (historically) Docker were all
  interchangeable underneath kubelet.

## What kubeadm actually does

`kubeadm init` on the control-plane node does, roughly, in order:
1. Runs preflight checks (CPU/memory minimums, swap disabled, required kernel modules
   and sysctls present, ports free) — **fails loudly rather than starting a
   half-working control plane.**
2. Generates a self-signed CA and every certificate the control-plane components need
   to talk to each other over TLS.
3. Writes **static Pod manifests** for `kube-apiserver`, `kube-scheduler`, and
   `kube-controller-manager` into `/etc/kubernetes/manifests/` — the kubelet on that
   node watches this directory directly (not via the API server, which doesn't exist
   yet at this point) and starts them as ordinary Pods. This is *how the control plane
   bootstraps itself*: kubelet starting Pods from local files is the one thing that
   doesn't require an already-running API server.
4. Bootstraps a single-node `etcd` as another static Pod (this lab's setup — a real HA
   control plane runs etcd as its own multi-node cluster instead).
5. Prints a `kubeadm join` command containing a **bootstrap token** and a CA cert hash —
   this is the entire credential a worker needs to securely join.

`kubeadm join` on each worker does the reverse: uses the bootstrap token to authenticate
to the API server just long enough to request its own signed kubelet certificate, then
starts kubelet, which registers the node and starts reporting in.

**What kubeadm deliberately does NOT do**: install a CNI plugin, provide HA etcd out of
the box, handle cloud-provider integration (load balancers, EBS volumes as PVs), or
manage OS-level upgrades. Every one of those is a separate, explicit step — which is
exactly why this lab has separate steps for them instead of one command that does
everything.

## Why Pod networking needs a separate plugin at all

Kubernetes's networking model requires that every Pod gets its own IP, and every Pod can
reach every other Pod's IP directly, on any node, without NAT. Kubernetes itself
implements *none* of this — it delegates entirely to whatever **CNI (Container Network
Interface)** plugin you install. Without one, Pods stay in `Pending` / `ContainerCreating`
forever; kubelet can start the container but has no way to give it a routable IP.

This lab uses **Flannel**, one of the simplest CNI plugins: it gives each node a slice
of a larger Pod CIDR (e.g. node A gets `10.244.0.0/24`, node B gets `10.244.1.0/24`), and
wraps pod-to-pod traffic between different nodes in a **VXLAN** tunnel (UDP port 8472) so
it can cross the underlying AWS network transparently. It's not the fastest or most
feature-rich CNI (Calico/Cilium offer network policies, BGP routing, eBPF dataplanes),
but it's the easiest to understand for a first pass, which matches this lab's goal.

## What EKS actually replaces, concretely

Now the payoff — mapping every step above to what "just use EKS" would have done for you
instead:

| This lab, by hand | What EKS does instead |
| --- | --- |
| `kubeadm init` — bootstrap one control plane, one etcd | AWS runs and fully manages the control plane + etcd across multiple AZs for you — you never see a control-plane EC2 instance at all |
| Manually keeping etcd/API server alive, no built-in HA | AWS handles control-plane HA and upgrades; you never patch it |
| Install Flannel yourself, understand VXLAN overlay | The Amazon VPC CNI is pre-integrated — Pods get real VPC IPs, no overlay network at all |
| `kubeadm join` with a manually-copied token | Managed node groups join automatically via IAM roles (`aws-auth` ConfigMap / access entries) |
| You manage kernel/containerd/kubelet versions on every node yourself | EKS-optimized AMIs and managed node group upgrades handle this |
| No cloud integration — a `LoadBalancer` Service does nothing without extra setup | The AWS Load Balancer Controller and EBS CSI driver are one Helm install away, pre-integrated with IAM |

None of this makes EKS "better" or "worse" in the abstract — it's a real cost/control
tradeoff. The point of this lab is that you now know exactly *what* you're trading away
by choosing one over the other, instead of "EKS is expensive" being the only fact you
have about it.

## Key terms, for quick reference

- **Static Pod**: a Pod defined by a file kubelet reads directly from local disk, not
  via the API server — how the control plane bootstraps before an API server exists.
- **Bootstrap token**: a short-lived, narrow-purpose credential (`kubeadm init` prints
  it) that lets a new node authenticate just long enough to request its own real
  certificate — not a long-term credential itself.
- **CNI (Container Network Interface)**: the plugin interface Kubernetes delegates all
  Pod networking to; Kubernetes has no built-in networking implementation of its own.
- **VXLAN overlay**: how Flannel gets Pod-to-Pod traffic across nodes that don't
  otherwise share a routable network — wraps it inside UDP packets between the real
  node IPs.
- **Reconciliation loop**: the core Kubernetes control pattern — continuously compare
  desired state (what you declared) to actual state (what's really running), and act to
  close the gap. Almost everything in `kube-controller-manager` is one of these.
