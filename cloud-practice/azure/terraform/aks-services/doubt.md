# Doubts: Questions and Plain-Language Answers

A running list of questions that came up while practising on this AKS
cluster. Each answer is written as simply as possible and checked against the
real cluster (`aks-svc-lf508l`, 1 node, gridwork deployed). Newest questions
go at the bottom.

Quick glossary used throughout:

| Word | Plain meaning |
|---|---|
| **Node** | A virtual machine (VM) that runs your pods. Here: 1 VM, `aks-system-31524237-vmss000000` |
| **Control plane** | The "brain" of Kubernetes (API server, scheduler, etc.). On AKS, **Azure runs it for you, outside your VMs** |
| **Pod** | One running copy of your app (one or more containers) |
| **Service** | A fixed name + address in front of a group of pods |
| **ClusterIP** | The internal address a Service gets. Works **only inside the cluster** |

---

## 1. Does a node get a public IP? Does the control plane use the node's IP to talk to it? And is that the same IP as a ClusterIP that outside services use?

**Short answer: No, no, and no.** These are three different things:

1. The node (VM) gets only a **private** IP, not a public one.
2. The control plane doesn't call the node's IP. **The node calls the control plane.**
3. A ClusterIP is **not** the node's IP, and **nothing outside the cluster can use it.**

### Part 1: The node has only a private IP

When AKS creates a node (a VM), it gets one IP address from the VNet subnet,
and it's private:

```
$ kubectl get node -o jsonpath='{range .items[0].status.addresses[*]}{.type}={.address}{"\n"}{end}'
InternalIP=10.224.0.4          <- private IP, from the VNet subnet 10.224.0.0/16
Hostname=aks-system-31524237-vmss000000
                               <- no ExternalIP line at all

$ az aks nodepool show ... --query enableNodePublicIp
false                          <- AKS default: nodes get NO public IP

$ az vmss nic list ... --query "[].ipConfigurations[].{private:privateIPAddress, public:publicIPAddress.id}"
Private     Public
10.224.0.4  (empty)
```

Think of the node as a computer in an office network: it has an internal
address (`10.224.0.4`) that only machines inside the same network can reach.
From your laptop it's unreachable:

```
$ curl http://10.224.0.4:30757/
(timeout)
```

> Public IPs **do** exist in this setup, but they belong to the **Azure Load
> Balancer**, not the node:
> - `4.224.100.179`: used when the node goes **out** to the internet (e.g. pulling images)
> - `98.70.243.116`: the gridwork website (from the `LoadBalancer` Service)
>
> (You *can* turn on public IPs per node with `enableNodePublicIp`, but it's
> off by default and rarely used.)

### Part 2: The node calls the control plane, not the other way around

On AKS, the control plane runs in **Azure's own network**, not in your VNet.
It can't reach into your private `10.224.x.x` network. So the direction is
reversed: **the node dials out to the control plane.**

```
                 Azure-managed (not your subscription)
            ┌─────────────────────────────────────────┐
            │  Control plane (API server, scheduler)  │
            │  akssvclf508l-...azmk8s.io  :443        │
            └───────────────▲─────────────────────────┘
                            │  HTTPS, started BY THE NODE (outbound)
                            │  via the Load Balancer's outbound IP 4.224.100.179
            ┌───────────────┴─────────────────────────┐
            │  Your VNet (private)                    │
            │  Node VM 10.224.0.4                     │
            │   ├─ kubelet ─────────► "any work for me?" / "here's my status"
            │   └─ konnectivity-agent ► keeps a tunnel open for logs/exec
            └─────────────────────────────────────────┘
```

Two things on the node do the dialling:

| Who (on the node) | What it does |
|---|---|
| **kubelet** | Connects to the API server, asks "which pods should I run?", and reports back "node is healthy, pod X is running" |
| **konnectivity-agent** | Opens a long-lived tunnel **to** `akssvclf508l-...azmk8s.io:443`. When you run `kubectl logs` or `kubectl exec`, the control plane sends that request **back down this tunnel** to the node |

Proof, from the agent's settings:

```
--proxy-server-host=akssvclf508l-s161qh2r.hcp.centralindia.azmk8s.io
--proxy-server-port=443
```

That's why the node doesn't need a public IP. It never has to accept an
incoming connection from the control plane.

### Part 3: A ClusterIP is not the node's IP, and is internal only

This is the key point to get right:

| | Node IP | ClusterIP |
|---|---|---|
| Example | `10.224.0.4` | `10.0.162.81` (gridwork-backend) |
| What it is | A real network card on the VM | A **virtual** address, just a forwarding rule |
| How many | One per node | One per Service (you have many on 1 node) |
| Who can reach it | Things inside the VNet | **Only pods inside the cluster** |
| From the internet / your laptop | ❌ | ❌ |

```
$ curl http://10.0.162.81:8000/health      # from the laptop
(timeout)                                  # ClusterIP is not reachable from outside
```

A ClusterIP is for **pods talking to other pods**, like the gridwork frontend
calling the backend, or the backend calling Redis. (Details and proof are in
[`SERVICES_AND_CLUSTER_IPS.md`](SERVICES_AND_CLUSTER_IPS.md).)

### So how DO outside users reach the app?

You need a Service of type **LoadBalancer**. It gets a **public IP on the
Azure Load Balancer**, which then forwards traffic into the private node:

```
Your browser
   │  http://98.70.243.116          <- public IP (on the Azure Load Balancer)
   ▼
Azure Load Balancer "kubernetes"
   │  forwards to the node's private IP 10.224.0.4
   ▼
Node VM (kube-proxy rules)
   │  rewrites the address to the pod's IP
   ▼
gridwork-frontend pod 10.244.0.135:80
   │  calls http://gridwork-backend:8000   <- ClusterIP, internal only
   ▼
gridwork-backend pod 10.244.0.88:8000
```

### One-line summary

**The node has a private IP. The node reaches out to the control plane
(never the reverse). ClusterIPs are internal addresses for pod-to-pod
traffic. Only a `LoadBalancer` Service's public IP is reachable from outside.**

---

## 2. Where is the control plane actually running? On a hidden node, or on my system node?

**Short answer: neither. It's not on any VM in your subscription.** Azure runs
it on **its own infrastructure**, completely outside your cluster. Your one
"system" node is an ordinary worker VM, and it runs none of the control
plane.

### What "system node" really means

The name `system` is confusing. On AKS, a **system node pool** is still a
**worker** pool. It's just the one AKS prefers for its own *add-ons* (CoreDNS,
metrics-server, konnectivity-agent, and so on; see
[`KUBE_SYSTEM_COMPONENTS.md`](KUBE_SYSTEM_COMPONENTS.md)). It's **not** a
control-plane node.

```
$ kubectl get node -o jsonpath='{.items[0].metadata.labels}'
"kubernetes.azure.com/mode":"system"     <- system POOL (for add-ons)
"kubernetes.azure.com/role":"agent"      <- but its role is AGENT = worker
                                          (no node-role.kubernetes.io/control-plane label,
                                           no control-plane taint)
```

### Evidence 1: there is only one node, and it's the worker

```
$ kubectl get nodes
aks-system-31524237-vmss000000   Ready   <none>   ...   10.224.0.4

$ az vmss list -g MC_rg-aks-services-demo_aks-svc-lf508l_centralindia
aks-system-31524237-vmss   1      <- the only VM set, capacity 1

$ az vm list --query "length(@)"
0                                  <- no other VMs anywhere in the subscription
```

No hidden node exists in your subscription. You'd see it (and pay for it).

### Evidence 2: no control-plane pods run in your cluster

```
$ kubectl get pods -A | grep -Ei 'apiserver|etcd|scheduler|controller-manager'
(nothing)
```

On a self-built cluster (kubeadm, minikube) you'd see `kube-apiserver-…`,
`etcd-…`, `kube-scheduler-…` and `kube-controller-manager-…` pods in
`kube-system` on a control-plane node. On AKS: none.

### Evidence 3: the control plane leaves "footprints" (leases), and they point elsewhere

Control-plane parts write a **lease** (like a "I'm the leader, I'm alive"
note) into your cluster. Reading who holds them shows they're real and
running, but not in your cluster:

```
$ kubectl get lease -n kube-system -o custom-columns=NAME:.metadata.name,HOLDER:.spec.holderIdentity
kube-scheduler            kube-scheduler-v2-5c944d8696-7v94d_...
kube-controller-manager   kube-controller-manager-v2-7b57b9f55d-srgkl_...
cloud-controller-manager  cloud-controller-manager-c5857c49d-kwr6z_...
apiserver-fweqj3nsilwv... apiserver-fweqj3nsilwv..._...     <- 2 API server copies
apiserver-il2ya3yfylqm... apiserver-il2ya3yfylqm..._...

$ kubectl get pods -A | grep -cE 'kube-controller-manager-v2|cloud-controller-manager|kube-scheduler-v2'
0                                   <- those holder pods don't exist in YOUR cluster
```

So the scheduler, controller-manager and cloud-controller-manager are running
somewhere (they hold the leases), and there are **two API server copies** for
reliability. The holder names look like normal Deployment pod names
(`...-7b57b9f55d-srgkl`), which suggests Azure itself runs them as pods on
**its own, separate cluster** that manages many customers' control planes.
**etcd** (the database holding all cluster state) isn't visible at all.

### Evidence 4: the API server's IP isn't yours

```
$ kubectl get endpointslices -l kubernetes.io/service-name=kubernetes
ENDPOINTS: 4.188.113.64              <- where the API server lives

$ az network public-ip list --query "[?ipAddress=='4.188.113.64']"
(not found in subscription)           <- Azure owns this IP, not you
```

### The picture

```
 ┌──────────────── Azure's side (hidden, you don't pay for VMs) ────────────────┐
 │  API server ×2   scheduler   controller-manager   cloud-controller-manager   │
 │  etcd (cluster database)                                                     │
 │  reachable at akssvclf508l-s161qh2r.hcp.centralindia.azmk8s.io (4.188.113.64)│
 └───────────────────────────────▲──────────────────────────────────────────────┘
                                 │ node dials OUT (kubelet + konnectivity tunnel)
 ┌──────────────── Your subscription (MC_... resource group) ───────────────────┐
 │  VNet 10.224.0.0/16                                                          │
 │   └─ Node VM "aks-system-...-vmss000000" 10.224.0.4   (role: agent/worker)   │
 │        ├─ kube-system add-ons: CoreDNS, kube-proxy, metrics-server, ...      │
 │        └─ your apps: gridwork frontend, backend, postgres, redis             │
 └──────────────────────────────────────────────────────────────────────────────┘
```

### Why AKS does it this way

- **You don't manage or patch it.** Azure upgrades, backs up and heals the control plane.
- **Free tier = no charge for it.** You only pay for your worker VMs. (The paid
  "Standard" tier adds an uptime SLA and more API server capacity, but the control plane is
  still hidden.)
- **Your node's CPU and memory go entirely to your workloads and add-ons**, not to etcd or the API server.
- **The trade-off:** you can't SSH into it, see its logs directly, or change its flags.
  You can only see its logs through Azure Monitor diagnostic settings.

### One-line summary

**The control plane runs on Azure's own hidden infrastructure, not on any VM
you own. Your "system" node is just a worker that hosts add-ons and your apps.
It reaches the control plane over the internet at the `...azmk8s.io` address.**

---

## 3. Where is kubeadm installed?

**Short answer: nowhere. AKS doesn't use kubeadm.** It's not on your node,
and you never see it on the control plane (which is hidden anyway, see
question 2). AKS has its **own** tooling to build nodes.

### What kubeadm is (for context)

`kubeadm` is the standard tool for building a Kubernetes cluster **yourself**
on plain Linux machines:

- `kubeadm init` on the first machine creates the control plane (API server,
  etcd, scheduler, controller-manager) as **static pods**, from files in
  `/etc/kubernetes/manifests/`.
- `kubeadm join` on other machines turns them into worker nodes.

Managed services (AKS, EKS, GKE) replace all of that with their own automation.

### Evidence: checked on your node

From a node shell (`kubectl debug node/... --profile=sysadmin`, then `chroot /host`):

```
$ command -v kubeadm
kubeadm: not found in PATH

$ find / -xdev -name "kubeadm*" -type f
(nothing)                          <- not installed anywhere on the disk

$ ls -la /etc/kubernetes/manifests
(empty)                            <- a kubeadm control plane would put
                                      kube-apiserver.yaml, etcd.yaml, etc. here
```

### So how does AKS set up the node instead?

```
1. Azure creates the VM from a ready-made AKS image
   (AKSUbuntu-2404gen2containerd-..., already has containerd + kubelet on it)
          │
          ▼
2. A VM extension runs AKS's setup script   (the "vmssCSE" extension, see AZURE_RESOURCES.md)
   files in /opt/azure/containers/  (init-aks-cloud.sh, kubelet.sh, aks-node-controller, ...)
   log:     /var/log/azure/cluster-provision.log   ("... endcustomscript")
          │
          ▼
3. kubelet starts as a normal Linux service
   /etc/systemd/system/kubelet.service → /opt/bin/kubelet ... $KUBELET_TLS_BOOTSTRAP_FLAGS
          │
          ▼
4. kubelet "joins" the cluster by itself (TLS bootstrap)
   uses /var/lib/kubelet/bootstrap-kubeconfig (a one-time join ticket)
   → asks the API server for its own certificate
   → saves it as /var/lib/kubelet/kubeconfig and pki/
          │
          ▼
5. Node shows up as Ready in `kubectl get nodes`
```

Step 4 is the same idea that `kubeadm join` uses under the hood (TLS
bootstrapping). AKS just does it with its own scripts instead of the
kubeadm command.

### kubeadm cluster vs. AKS side by side

| | Self-built with kubeadm | AKS (this cluster) |
|---|---|---|
| Create control plane | `kubeadm init` on your machine | Azure does it, hidden (question 2) |
| Control-plane files | `/etc/kubernetes/manifests/*.yaml` (static pods) | empty folder on your node |
| Add a worker node | `kubeadm join <token>` | Azure creates a VM, and the AKS script + kubelet join by themselves |
| Upgrade | `kubeadm upgrade` node by node | `az aks upgrade` / Terraform `kubernetes_version` |
| Where kubelet lives | usually `/usr/bin/kubelet` (from apt packages) | `/opt/bin/kubelet` (baked into the AKS image) |

### Where kubeadm *would* show up

If you want to try kubeadm itself, you'd need plain VMs (e.g. the sibling
`../vm/` module) and install it yourself (`apt install kubeadm kubelet
kubectl`). Tools like **kind** and **minikube** also use kubeadm internally.
On AKS, you never touch it.

### One-line summary

**kubeadm isn't installed on AKS. Azure builds your node from a pre-made
image and joins it to the cluster with its own script (vmssCSE) plus
kubelet's built-in TLS bootstrap. The control plane is created by Azure,
not by `kubeadm init`.**

---

## 4. I see pods, Deployments and ReplicaSets. Do I always need a ReplicaSet?

**Short answer: you need one, but you never create or manage it yourself.**
When you create a **Deployment**, Kubernetes creates the ReplicaSet for you,
and the ReplicaSet creates the pods. You only ever write/edit the
Deployment. Other kinds (StatefulSet, Job) don't use ReplicaSets at all.

### Who creates whom (checked in the `gridwork` namespace)

Every Kubernetes object records its "parent" in `ownerReferences`:

```
$ kubectl get pods,rs -n gridwork -o custom-columns='KIND:.kind,NAME:.metadata.name,OWNER-KIND:.metadata.ownerReferences[0].kind,OWNER:.metadata.ownerReferences[0].name'
KIND         NAME                                 OWNER-KIND    OWNER
Pod          gridwork-backend-569bb56978-pwzjk    ReplicaSet    gridwork-backend-569bb56978
Pod          gridwork-frontend-74655fc657-wjwh2   ReplicaSet    gridwork-frontend-74655fc657
Pod          gridwork-redis-575846c79d-9fc4w      ReplicaSet    gridwork-redis-575846c79d
Pod          gridwork-postgres-0                  StatefulSet   gridwork-postgres     <- no ReplicaSet
Pod          gridwork-migrate-2-58swh             Job           gridwork-migrate-2    <- no ReplicaSet
ReplicaSet   gridwork-backend-569bb56978          Deployment    gridwork-backend
ReplicaSet   gridwork-backend-56d48474d4          Deployment    gridwork-backend
ReplicaSet   gridwork-frontend-74655fc657         Deployment    gridwork-frontend
ReplicaSet   gridwork-redis-575846c79d            Deployment    gridwork-redis
```

As a family tree:

```
Deployment  gridwork-backend             <- YOU manage this (via Helm)
  ├─ ReplicaSet gridwork-backend-56d48474d4   revision 1, image :166f8cf        → 0 pods
  └─ ReplicaSet gridwork-backend-569bb56978   revision 2, image :166f8cf-sqla20 → 1 pod
        └─ Pod gridwork-backend-569bb56978-pwzjk

StatefulSet gridwork-postgres            <- manages its pod DIRECTLY
  └─ Pod gridwork-postgres-0

Job gridwork-migrate-2                   <- manages its pod DIRECTLY
  └─ Pod gridwork-migrate-2-58swh   (Completed)
```

Notice the names: the pod name is the ReplicaSet name plus a random suffix, and
the ReplicaSet name is the Deployment name plus a **hash of the pod template**
(`569bb56978`).

### What each one does, in simple words

| Object | Its one job | Do you write it? |
|---|---|---|
| **Pod** | Runs your container(s) | No. If a lone pod dies, nothing brings it back |
| **ReplicaSet** | "Keep exactly **N** copies of **this exact** pod running." Replaces pods that die | No. Created by the Deployment |
| **Deployment** | Manages **versions**: rolling updates, rollbacks, history. Does this by creating a new ReplicaSet per version | **Yes**, this is what you (or Helm) write |

The key point: **a ReplicaSet can't change its pods**. It only knows one
fixed pod template. So when you change the image, the Deployment makes a
**new** ReplicaSet for the new version and slowly moves pods over:

```
old RS (v1):  1 pod  →  1 pod  →  0 pods
new RS (v2):  0 pods →  1 pod  →  1 pod       (rolling update)
```

### Why is there an "empty" ReplicaSet (`0 0 0`)?

```
replicaset.apps/gridwork-backend-56d48474d4    0   0   0     <- revision 1
replicaset.apps/gridwork-backend-569bb56978    1   1   1     <- revision 2
```

That's the **first backend version** (image `:166f8cf`, the one that
crashed with the `psycopg` error, see [`DEPLOY_GRIDWORK.md`](DEPLOY_GRIDWORK.md)).
When the fixed image rolled out, the Deployment scaled it to 0 but **kept it**
as history:

```
$ kubectl rollout history deploy/gridwork-backend -n gridwork
REVISION
1          <- ReplicaSet ...56d48474d4 (:166f8cf)
2          <- ReplicaSet ...569bb56978 (:166f8cf-sqla20), current
```

That's what makes **instant rollback** possible:

```bash
kubectl rollout undo deploy/gridwork-backend -n gridwork   # would scale RS rev 1 back up
```

(Don't run it here, since revision 1 is the broken image.) Kubernetes keeps
the last **10** old ReplicaSets (`revisionHistoryLimit: 10`) and deletes older ones
automatically. Empty ReplicaSets use no CPU or memory. They're just saved records.

### What about StatefulSet and Job?

They don't use ReplicaSets:

- **StatefulSet** (Postgres) owns its pods **directly**, because each pod
  has a fixed identity (`postgres-0`, `-1`, …) and its own disk. It keeps version
  history in a different object:
  ```
  $ kubectl get controllerrevisions -n gridwork
  gridwork-postgres-78b956cf8b   statefulset.apps/gridwork-postgres   1
  ```
- **Job** (the migration) runs pods **until they finish once** and then stops.
  No "keep N running" is needed, so there's no ReplicaSet.
- **DaemonSet** (e.g. kube-proxy in `kube-system`) is the same: it owns pods
  directly, one per node.

### Should I ever create a ReplicaSet myself?

**Practically never.** Always use a Deployment. It does everything a
ReplicaSet does, plus updates and rollbacks. If you delete a ReplicaSet that a
Deployment owns, the Deployment just recreates it. Writing a bare ReplicaSet
means losing rolling updates for no gain.

### One-line summary

**Deployment → ReplicaSet → Pod. You manage only the Deployment; it creates
one ReplicaSet per version (old ones kept at 0 for rollback). StatefulSets,
Jobs and DaemonSets manage their pods directly with no ReplicaSet.**

---

## 5. So the flow is Deployment → ReplicaSet → Pod?

**Yes.** You write the Deployment, and everything after that happens
automatically. Each arrow is done by a different part of Kubernetes. Here is
the full chain, all the way to a running container:

```
You: kubectl apply / helm install
   │
   ▼
Deployment            ← your wish: "1 backend pod, image X"
   │  Deployment controller (hidden control plane, question 2) creates…
   ▼
ReplicaSet            ← "keep 1 copy of THIS exact pod"
   │  ReplicaSet controller (control plane) creates…
   ▼
Pod                   ← at first just a record in the database, not running anywhere yet
   │  Scheduler (control plane) picks a node → aks-system-31524237-vmss000000
   ▼
kubelet on that node  ← dials out to the API server and sees "a pod is assigned to me" (question 1)
   │  tells containerd: pull image from ACR, start the container
   ▼
Running container
```

Who does which step:

| Step | Done by | Where it runs |
|---|---|---|
| Deployment → ReplicaSet | Deployment controller (part of kube-controller-manager) | Azure's hidden control plane |
| ReplicaSet → Pod | ReplicaSet controller (part of kube-controller-manager) | Azure's hidden control plane |
| Pod → node | kube-scheduler | Azure's hidden control plane |
| Node → running container | kubelet + containerd | **your** node VM |

Other workload kinds skip the ReplicaSet (question 4):

```
StatefulSet → Pod     (e.g. gridwork-postgres-0)
Job         → Pod     (e.g. gridwork-migrate-2-...)
DaemonSet   → Pod     (e.g. kube-proxy, one per node)
```

**Try it yourself.** Watch each layer react when you scale:

```bash
kubectl scale deploy/gridwork-frontend -n gridwork --replicas=2
kubectl get deploy,rs,pods -n gridwork -l app=gridwork-frontend
kubectl get events -n gridwork --sort-by=.lastTimestamp \
  -o custom-columns=REASON:.reason,OBJECT:.involvedObject.kind,SOURCE:.source.component,MSG:.message | tail -6
kubectl scale deploy/gridwork-frontend -n gridwork --replicas=1   # back to 1
```

Real output from this cluster. The **SOURCE** column shows who did each step:

```
REASON              OBJECT       SOURCE                  MSG
ScalingReplicaSet   Deployment   deployment-controller   Scaled up replica set gridwork-frontend-74655fc657 from 1 to 2
SuccessfulCreate    ReplicaSet   replicaset-controller   Created pod: gridwork-frontend-74655fc657-gr5jz
Scheduled           Pod          default-scheduler       Successfully assigned gridwork/gridwork-frontend-74655fc657-gr5jz to aks-system-31524237-vmss000000
Pulled              Pod          kubelet                 Container image ".../gridwork-frontend:166f8cf" already present on machine
Created             Pod          kubelet                 Container created
Started             Pod          kubelet                 Container started
```

Each arrow in the diagram above appears as one event from a different component.

### One-line summary

**Deployment → ReplicaSet → Pod → (scheduler picks node) → kubelet starts the
container. You touch only the first box.**

---

## 6. So a StatefulSet is an alternative to a Deployment?

**Yes, both are ways to run pods, but you pick based on the app, not
preference.**

- **Deployment**: for apps where **every copy is identical and replaceable**
  (stateless). Example: gridwork backend, frontend.
- **StatefulSet**: for apps where **each copy needs its own identity and
  its own disk** that survive restarts (stateful). Example: gridwork Postgres.

Analogy: Deployment pods are like **taxis**. Any one will do, and if one
breaks you get another. StatefulSet pods are like **numbered bank lockers**.
Locker #0 always has the same number and the same contents, even if the
door is replaced.

### The differences, checked on gridwork

| | Deployment (`gridwork-backend`) | StatefulSet (`gridwork-postgres`) |
|---|---|---|
| **Pod names** | random: `gridwork-backend-569bb56978-pwzjk` | fixed, numbered: `gridwork-postgres-0` (then `-1`, `-2`…) |
| **After a restart** | new name, new IP | **same name** (`-0` comes back as `-0`); the IP may change, but DNS follows it |
| **Storage** | shared or none (Redis here has no volume at all, so its data is lost on restart) | **one disk per pod** from `volumeClaimTemplates`: pod `-0` always gets PVC `data-gridwork-postgres-0` → the same Azure Managed Disk |
| **Network name** | only the Service name (load-balanced) | **per-pod DNS**: `gridwork-postgres-0.gridwork-postgres` via a **headless** Service (question 1 and [`SERVICES_AND_CLUSTER_IPS.md`](SERVICES_AND_CLUSTER_IPS.md)) |
| **Start/stop order** | all at once, any order | **in order**: `-0` must be Ready before `-1` starts; scale down removes the highest number first (`podManagementPolicy: OrderedReady`) |
| **Uses a ReplicaSet?** | yes (question 4) | no, owns pods directly |
| **Delete the workload** | pods gone | pods gone, **disks kept** (`persistentVolumeClaimRetentionPolicy: Retain`), so data isn't lost by accident |

From the cluster:

```
$ kubectl get sts gridwork-postgres -n gridwork -o jsonpath=...
serviceName=gridwork-postgres            <- the headless Service giving per-pod DNS
podManagementPolicy=OrderedReady         <- start/stop one at a time, in order
volumeClaimTemplates=data                <- "give every pod its own disk named data-<pod>"
pvcRetention={"whenDeleted":"Retain","whenScaled":"Retain"}   <- keep disks

$ kubectl get pod gridwork-postgres-0 -n gridwork -o jsonpath=...
hostname=gridwork-postgres-0 subdomain=gridwork-postgres claim=data-gridwork-postgres-0
```

That `Retain` is why [`DEPLOY_GRIDWORK.md`](DEPLOY_GRIDWORK.md)'s teardown
needs an explicit `kubectl delete pvc`. Otherwise the Azure disk keeps
existing (and costing money) after `helm uninstall`.

### Why a database needs this

If Postgres ran as a Deployment and its pod restarted, the new pod could
start with a **fresh empty disk** or, with several replicas, **fight over the
same disk**. With a StatefulSet:

1. `gridwork-postgres-0` restarts → comes back with the **same name**
2. → reattaches **its own** PVC `data-gridwork-postgres-0` → same Azure disk
3. → all the data (e.g. the `labtest@example.com` user) is still there

With replication (e.g. `-0` primary, `-1` replica), apps can also address a
**specific** member by its stable DNS name. Load-balancing across a primary
and replicas would send writes to the wrong one.

### Which one should I use?

```
Does each copy need its OWN data that must survive restarts,
or a stable name other members must find?
     │
     ├─ No  → Deployment      (web apps, APIs, workers: most things)
     │
     └─ Yes → StatefulSet     (databases, Kafka, Zookeeper, Elasticsearch, Redis with persistence)
```

The other two workload types (question 4) are different tools, not
alternatives:

| Kind | Use when |
|---|---|
| **DaemonSet** | exactly one pod on **every node** (log agents, kube-proxy) |
| **Job / CronJob** | run to **completion** once / on a schedule (gridwork's migration Job) |

> Real-world note: on Azure, many teams don't run Postgres in the cluster at
> all. They use a managed database (Azure Database for PostgreSQL) and keep
> the cluster stateless, with only Deployments. A StatefulSet is fine for learning and
> labs like this one.

### One-line summary

**Both run pods. A Deployment is for identical, throwaway copies (stateless apps).
A StatefulSet is for copies that each keep a fixed name, a fixed disk and a start
order (databases). Pick by whether the app has state to keep.**

---

## 7. Are there other ways to run pods, besides Deployment and StatefulSet?

**Yes.** Kubernetes has a handful of built-in "workload" types, each for a
different kind of job. On top of that, you can add more types by installing
extensions (operators). But for everyday apps you'll mostly use
Deployment, StatefulSet, DaemonSet, Job and CronJob.

### The built-in ones on this cluster

```
$ kubectl api-resources --api-group=apps -o name
daemonsets.apps  deployments.apps  replicasets.apps  statefulsets.apps  (controllerrevisions.apps = history, not a workload)
$ kubectl api-resources --api-group=batch -o name
cronjobs.batch  jobs.batch
```

| Type | What it's for (plain words) | Keeps running? | Example on this cluster |
|---|---|---|---|
| **Deployment** | N identical, replaceable copies of an app | yes | gridwork backend, frontend, redis; CoreDNS |
| **StatefulSet** | copies that each keep a fixed name + own disk | yes | gridwork Postgres |
| **DaemonSet** | exactly **one pod on every node** (add a node → it gets one automatically) | yes | kube-proxy, azure-cns, CSI drivers (see [`KUBE_SYSTEM_COMPONENTS.md`](KUBE_SYSTEM_COMPONENTS.md)) |
| **Job** | run a task **until it finishes successfully**, then stop | no, it completes | `gridwork-migrate-2` (database migration) |
| **CronJob** | create a Job **on a schedule** (like Linux cron) | no, runs per schedule | none yet (e.g. nightly backup, cleanup) |
| **ReplicaSet** | keep N copies of one fixed pod. Normally created *by* a Deployment | yes | the `gridwork-*-<hash>` ones (question 4) |
| **Pod** (on its own) | a single pod with **no manager**. If it dies or its node goes away, nothing recreates it | until it dies | the `apitest` / debug pods used for testing |

Quick way to choose:

```
Does it run forever, or finish?
 ├─ Finishes ───────── once ──────────────► Job
 │                  └─ on a schedule ─────► CronJob
 └─ Runs forever
      ├─ one per node (agent/infra) ──────► DaemonSet
      ├─ needs own identity + disk ───────► StatefulSet
      └─ everything else ─────────────────► Deployment     (the default choice)
```

### Less common ones

| Way | What it is | Should you use it? |
|---|---|---|
| **Bare Pod** | `kubectl run` / `kind: Pod` with no controller | Only for quick tests and debugging |
| **Bare ReplicaSet** | writing a ReplicaSet yourself | No, use a Deployment (question 4) |
| **ReplicationController** | the old, pre-ReplicaSet version | No. It still exists (core `v1`, you saw it in the `get all` list) only for backward compatibility |
| **Static Pod** | a YAML file placed in `/etc/kubernetes/manifests/` on a node, which the kubelet runs directly without the API server | That's how **kubeadm** runs the control plane. On AKS this folder is empty (question 3) |

### Adding new types: operators and CRDs

Kubernetes lets tools add **new object types** (CustomResourceDefinitions, or CRDs)
plus a controller (an "operator") that knows how to run them. They usually
create Deployments/StatefulSets/Pods underneath. Popular examples:

| Tool | New type you'd write | What it adds |
|---|---|---|
| **CloudNativePG** | `kind: Cluster` | a whole Postgres cluster with failover and backups (a smarter replacement for gridwork's hand-written StatefulSet) |
| **Argo Rollouts** | `kind: Rollout` | a Deployment with canary / blue-green releases |
| **KEDA** | `ScaledObject`, `ScaledJob` | scale on queue length, events, down to zero (gridwork's chart supports it, but it's off here) |
| **Knative** | `kind: Service` (Knative's own) | serverless-style apps that scale to zero on no traffic |

This cluster currently has only Azure's networking/storage CRDs
(`nodenetworkconfigs.acn.azure.com`, `volumesnapshots...`). No extra workload
types are installed.

### Not a new type, but a different place to run pods

**AKS virtual nodes** run pods on **Azure Container Instances** instead of on
your VMs (the `aks-virtualkubelet` subnet you saw in
[`AZURE_RESOURCES.md`](AZURE_RESOURCES.md) is reserved for this). You still
use a normal Deployment; only *where* the pods land changes. It's off in this
cluster.

### One-line summary

**Built-in choices: Deployment (default), StatefulSet (stateful), DaemonSet
(one per node), Job/CronJob (run to completion). Bare Pods/ReplicaSets are
for testing only, and operators like CloudNativePG, Argo Rollouts or KEDA add
smarter types on top of these.**

---

## 8. What problem does a ClusterIP solve? How can one node have many ClusterIPs, and why?

**Short answer:**
- **Problem:** pods are temporary, and **their IP changes every time they are
  replaced**. A ClusterIP gives a group of pods **one fixed address + name**
  that never changes, so other apps always know where to call.
- **Many on one node:** a ClusterIP is **not attached to the node**. It's just
  a **forwarding rule** ("traffic for X → send to pod Y"). A node can hold
  thousands of rules, so there's no limit tied to node count.

### Part 1: The problem, shown live on this cluster

The gridwork frontend (nginx) must call the backend. What address should it use?

**Option A: the backend pod's IP.** Watch what happens when the pod is
replaced (a crash, an upgrade, or here, a manual delete):

```
BEFORE: pod IP = 10.244.0.88    ClusterIP = 10.0.162.81
$ kubectl delete pod -n gridwork -l app=gridwork-backend      # Deployment makes a new one
AFTER:  pod IP = 10.244.0.157   ClusterIP = 10.0.162.81
                  ^^^^^^^^^^^^ changed         ^^^^^^^^^^^ same
```

If nginx had `10.244.0.88` written in its config, **the site would now be
broken**. And pods get replaced *all the time*: every deploy, every crash,
every node restart.

**Option B: the Service (ClusterIP).** nginx calls
`http://gridwork-backend:8000`, which resolves to `10.0.162.81`. After the pod was
replaced:

```
$ kubectl exec -n gridwork deploy/gridwork-frontend -- wget -qO- http://gridwork-backend:8000/health
{"status":"healthy",...,"database":"healthy"}
$ curl http://98.70.243.116/     → 200            # public site never noticed
```

**The ClusterIP is a permanent "front desk" for a group of pods.** Pods
behind it come and go, but callers always use the same desk.

Analogy: a company **reception phone number**. Employees (pods) join,
leave and change desks (IPs), but customers always dial the same reception
number (ClusterIP), and reception connects them to whoever is available.

### What problems it solves, in a list

| Problem without it | How ClusterIP fixes it |
|---|---|
| Pod IPs change on every restart/deploy | **Fixed IP** for the lifetime of the Service |
| Hard to remember/configure IPs | **Fixed DNS name**: `gridwork-backend` (or `gridwork-backend.gridwork.svc.cluster.local`) |
| 3 backend copies = 3 IPs; who picks one? | **Built-in load balancing**: one ClusterIP, traffic spread across all healthy pods |
| A pod that's starting or unhealthy gets traffic | Only **Ready** pods (passing their readiness probe) are sent traffic |
| Other apps need to know about pod changes | They don't. Kubernetes updates the rules behind the scenes |

### Part 2: How can one node have many ClusterIPs?

Because **a ClusterIP isn't a real address on any machine**. Compare:

| | Node IP `10.224.0.4` | ClusterIP `10.0.162.81` |
|---|---|---|
| Is it on a network card? | yes, `eth0` of the VM | **no, on nothing** |
| What is it really? | the VM's address | a **rule**: "packets to 10.0.162.81:8000 → rewrite to the backend pod's IP" |
| How many can there be? | one per node | as many Services as you create (up to 65,536 in `10.0.0.0/16`) |

On your node, the rule looks like this (from `iptables-save`, see
[`SERVICES_AND_CLUSTER_IPS.md`](SERVICES_AND_CLUSTER_IPS.md)):

```
to 10.0.162.81:8000 ("gridwork-backend") → send to 10.244.0.88:8000  (now 10.244.0.157)
to 10.0.138.6:6379  ("gridwork-redis")   → send to 10.244.0.57:6379
to 10.0.212.134:80  ("gridwork-frontend")→ send to 10.244.0.135:80
...
```

It's like a **phone book / call-forwarding list** on the node. A list can have
100 entries or 10,000 entries on the same one phone. Right now, this single
node holds 7 ClusterIPs (8 Services, minus the headless Postgres one, which
has none).

### Who writes those rules?

```
1. You create a Service ───► API server gives it a ClusterIP from 10.0.0.0/16
2. Pods matching its selector are Ready ───► their IPs are listed in an EndpointSlice
3. kube-proxy (runs on EVERY node, a DaemonSet) watches both
       └─► writes/updates the forwarding rules on its node
4. A pod sends a packet to 10.0.162.81 ───► the node's rule rewrites it to the
   current pod IP ───► delivered
```

When the backend pod was replaced (`.88` → `.157`), only step 2–3 changed:
kube-proxy **updated the rule**. The ClusterIP and DNS name never changed, so
nobody calling the backend had to know.

### Why does *every* node get *every* rule?

Because a caller pod can be on **any** node, and the target pod can be on
**any** node. So each node must be able to answer "where does
10.0.162.81 go?" by itself, locally, with no central box in the middle.
That's also why it's fast: the redirect happens right on the caller's own node.
Add a second node, and kube-proxy on it writes **the same full list**. The
number of ClusterIPs depends on the number of **Services**, never on
the number of nodes.

### Remember: ClusterIP = inside only

ClusterIPs work **only for pods inside the cluster** (question 1). For
outside users you add a **LoadBalancer** Service on top, like
`gridwork-frontend-public` → `98.70.243.116`.

### One-line summary

**Pods keep changing IPs, so a ClusterIP gives them one permanent internal
address + name, with load balancing. It isn't a real address on the node,
just a forwarding rule that kube-proxy writes on every node. That's why one
node can hold any number of them.**

---

## 9. Is there one ClusterIP for each type of pod?

**Short answer: not quite. It's one ClusterIP per _Service_, not per pod
type.** A Service is something **you create** (or a Helm chart creates). It
picks its pods with a **label selector**. So a group of pods can have
**one, several, or zero** ClusterIPs, depending on how many Services point at
them.

Also: **pods themselves never get a ClusterIP.** Each pod gets a **pod IP**
(`10.244.x.x`). The ClusterIP (`10.0.x.x`) belongs to the Service in front.

### Checked in the `gridwork` namespace

```
$ kubectl get svc -n gridwork -o custom-columns='SERVICE:.metadata.name,TYPE:.spec.type,CLUSTER-IP:.spec.clusterIP,SELECTOR:.spec.selector'
SERVICE                    TYPE           CLUSTER-IP     SELECTOR
gridwork-backend           ClusterIP      10.0.162.81    app:gridwork-backend
gridwork-frontend          NodePort       10.0.212.134   app:gridwork-frontend    ┐ same pods,
gridwork-frontend-public   LoadBalancer   10.0.174.219   app:gridwork-frontend    ┘ TWO ClusterIPs
gridwork-postgres          ClusterIP      None           app:gridwork-postgres    <- headless: ZERO
gridwork-redis             ClusterIP      10.0.138.6     app:gridwork-redis
```

| Pod group | Services pointing at it | ClusterIPs it's reachable by |
|---|---|---|
| backend | 1 (`gridwork-backend`) | **1**: `10.0.162.81` |
| redis | 1 (`gridwork-redis`) | **1**: `10.0.138.6` |
| frontend | **2** (`gridwork-frontend` + `gridwork-frontend-public`, which I added) | **2**: `10.0.212.134` and `10.0.174.219` |
| postgres | 1, but **headless** | **0**: DNS gives the pod IP directly (question 6) |
| migration Job pod | **none** | **0**: nothing needs to call it; it just runs and exits |

So in gridwork, "one ClusterIP per pod type" *looks* true for backend and
redis, but only because the Helm chart happened to create one Service for
each.

### How a Service "finds" its pods: labels

```
Service gridwork-backend
  selector: app=gridwork-backend    ← "send traffic to any Ready pod with this label"
        │
        ├──► pod gridwork-backend-...  (label app=gridwork-backend)   ✔
        ├──► (a 2nd replica would be picked up automatically)        ✔
        └──✗ pod gridwork-redis-...    (label app=gridwork-redis)     not matched
```

The Service doesn't care whether pods come from a Deployment, a StatefulSet
or anything else. **It only matches labels.** Scale the backend to 5 pods,
and it's still **one** ClusterIP with 5 pods behind it.

### The rules, in simple words

| Statement | True? |
|---|---|
| Every Service (except headless) gets exactly **one** ClusterIP | ✅ |
| A Service with several ports still has **one** ClusterIP (e.g. `kube-dns` `10.0.0.10`: ports `dns` 53/UDP + `dns-tcp` 53/TCP) | ✅ |
| Many pods behind one Service share **one** ClusterIP | ✅ |
| A pod gets a ClusterIP | ❌ pods get pod IPs |
| Every pod type automatically gets a ClusterIP | ❌ only if someone creates a Service for it (the migrate Job has none) |
| A pod group can have only one ClusterIP | ❌ frontend has two |

### When would you want more than one Service for the same pods?

- **Different exposure:** one internal (ClusterIP) for other pods, one public
  (LoadBalancer) for the internet. That's exactly gridwork's frontend.
- **Different ports for different callers:** e.g. an app's port 8080 for
  users and 9090 for metrics, as two separate Services.
- **Headless + normal together:** databases often have a headless Service
  (reach a specific member) *and* a normal one (reach any member).

### One-line summary

**ClusterIPs come from Services, not pods: one per (non-headless) Service,
shared by all pods it selects by label. A pod group can have 0, 1 or many,
depending on how many Services point at it.**

---

## 10. Do I have any NodePort Services? Any LoadBalancer Services?

**Yes, one of each, both in `gridwork`, both in front of the frontend pods.**
Everything else in the cluster is ClusterIP.

```
$ kubectl get svc -A -o custom-columns='NAMESPACE:...,NAME:...,TYPE:...,CLUSTER-IP:...,EXTERNAL-IP:...,PORTS:...,NODEPORTS:...'
NAMESPACE     NAME                       TYPE           CLUSTER-IP     EXTERNAL-IP     PORTS   NODEPORTS
default       kubernetes                 ClusterIP      10.0.0.1       <none>          443     <none>
gridwork      gridwork-backend           ClusterIP      10.0.162.81    <none>          8000    <none>
gridwork      gridwork-frontend          NodePort       10.0.212.134   <none>          80      30932     ◄ NodePort
gridwork      gridwork-frontend-public   LoadBalancer   10.0.174.219   98.70.243.116   80      30757     ◄ LoadBalancer
gridwork      gridwork-postgres          ClusterIP      None           <none>          5432    <none>
gridwork      gridwork-redis             ClusterIP      10.0.138.6     <none>          6379    <none>
kube-system   kube-dns                   ClusterIP      10.0.0.10      <none>          53,53   <none>
kube-system   metrics-server             ClusterIP      10.0.6.36      <none>          443     <none>
```

| Type | Count | Which | Who created it |
|---|---|---|---|
| ClusterIP | 6 (5 with an IP + 1 headless) | backend, redis, postgres, kubernetes, kube-dns, metrics-server | Helm chart / Kubernetes / AKS |
| **NodePort** | **1** | `gridwork-frontend` | gridwork's Helm chart (its default when ingress is off) |
| **LoadBalancer** | **1** | `gridwork-frontend-public` | me, via `gridwork/frontend-lb.yaml` ([`DEPLOY_GRIDWORK.md`](DEPLOY_GRIDWORK.md)) |

(The two test LoadBalancers `web-lb-a` / `web-lb-b` from the
[`README.md`](README.md) experiment were deleted earlier.)

### Remember: the types are layers

```
ClusterIP     10.0.212.134:80                      ← inside the cluster only
NodePort      = ClusterIP + port 30932 on EVERY node's IP
LoadBalancer  = NodePort  + a public IP on the Azure LB (98.70.243.116)
```

That's why the LoadBalancer Service **also** has a node port (`30757`) and a
ClusterIP (`10.0.174.219`). It's all three layers at once.

### Can I actually reach them? (tested)

```
Your laptop → http://98.70.243.116/          → 200   ✅ LoadBalancer: public, works
Your laptop → http://10.224.0.4:30932/       → timeout ❌ NodePort: node IP is private (question 1)
Pod inside VNet → http://10.224.0.4:30932/   → 200   ✅ NodePort works, but only from inside the network
```

So on AKS:

| Type | Reachable from the internet? | Typical use |
|---|---|---|
| ClusterIP | ❌ | pod-to-pod calls (the most common) |
| NodePort | ❌ here: nodes have **no public IP** | building block for LoadBalancer; useful on minikube / bare-metal, or from other VMs in the same VNet |
| LoadBalancer | ✅ via the Azure LB's public IP | exposing an app to the outside world |

The `gridwork-frontend` NodePort is effectively **unused** in this setup. It
exists because gridwork's chart was written for minikube, where
`minikube service` reaches the node port directly. It's harmless: no extra
Azure cost, just an open port on the node that the NSG blocks from outside.

### One-line summary

**One NodePort (`gridwork-frontend`, port 30932, only reachable inside the
VNet) and one LoadBalancer (`gridwork-frontend-public`, public IP
`98.70.243.116`). Everything else is ClusterIP.**

---

## 11. I don't understand Service types at all. Can we see the problem first, then how each type solves it?

Done as a separate hands-on lab with Mermaid diagrams:
**[`service-types-lab/SERVICE_TYPES_LAB.md`](service-types-lab/SERVICE_TYPES_LAB.md)**.

The short version:

| Stage | What we tried | Result |
|---|---|---|
| No Service | laptop → pod IP | ❌ pod IPs are private to the cluster |
| No Service | pod → pod IP, then the pod gets replaced | ❌ the IP changed, so the caller broke |
| No Service | pod → `http://hello` | ❌ no name exists; 2 pods, which one to call? |
| **ClusterIP** | pod → `http://hello-clusterip` | ✅ one fixed name/IP, spread across pods, survives pod replacement. ❌ laptop still can't reach it |
| **NodePort** | VNet → `10.224.0.4:30080` | ✅ from inside the private network. ❌ laptop can't, because the node has no public IP |
| **LoadBalancer** | laptop → `20.235.233.22` | ✅ public, load-balanced |

**One-line summary:** ClusterIP solves "pods keep changing" (inside only),
NodePort opens a port on every node (useful only where node IPs are reachable),
and LoadBalancer puts a public IP in front, which is the one that works from the internet on AKS.
