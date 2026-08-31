# gpu-scheduling-demo

Closes the biggest named-but-unbuilt gap in this repo's Kubernetes content: GPU scheduling
(`ml-platform-engineer-roadmap.md` §5, Track 3's "GPU/resource scheduling on K8s" line) is
explicitly VMware's differentiator angle (GPU virtualization/vGPU, VMware Private AI), and
nothing in `k8s_explorer/` touched it before this — for the honest reason that there's no local
GPU to run a real NVIDIA device plugin against.

This demo simulates the *scheduling mechanics* a real GPU device plugin relies on, without any
GPU hardware, using the pattern from the official Kubernetes docs ("Advertise Extra Resources on
a Node"). It doesn't teach the device-plugin gRPC protocol itself — see "What this doesn't cover"
below for exactly where the line is and how to go further.

Assumes a running, **multi-node** `minikube` cluster (`minikube status` — this repo's default
profile already has 3 nodes: `minikube`, `minikube-m02`, `minikube-m03`).

## What problem does it solve?

A real GPU device plugin (NVIDIA's, AMD's, etc.) does two things: it tells the kubelet "this node
has N of resource `nvidia.com/gpu`" (via a `ListAndWatch` gRPC call), and later, when a Pod
requesting one gets scheduled here, it tells the kubelet which physical device to hand over (the
`Allocate` call — sets `NVIDIA_VISIBLE_DEVICES`, mounts `/dev/nvidiaN`). The **scheduler itself
never talks to the device plugin at all** — it only ever sees node capacity/allocatable numbers,
the same as it sees `cpu` or `memory`. That's the piece this demo isolates: what the scheduler
actually does with a GPU-shaped resource, independent of how that number got onto the node.

## The mechanism

```bash
./patch-node-gpu.sh minikube-m03 2
```

This runs the exact API call a device plugin's `ListAndWatch` triggers indirectly — a merge patch
on `status.capacity`/`status.allocatable`:

```
node/minikube-m03 patched
Patched minikube-m03 with example.com/toygpu=2 (capacity and allocatable).
minikube-m03 capacity=2 allocatable=2
```

**Verified this isn't wiped by the kubelet's own heartbeat** (the real risk with hand-patching
node status — kubelet resyncs node status on a fixed interval): waited 15s past a heartbeat cycle
and re-checked; still there. Kubelet only reconciles the resource types it manages itself (cpu,
memory, pods, ephemeral-storage, and whatever a real device plugin registered) — it leaves
resources it doesn't recognize alone.

## Verified run — bin-packing with a scarce, indivisible resource

```bash
kubectl apply -f pods.yaml   # 3 pods, each requesting example.com/toygpu: 1, node only has 2
```

```
pod/toygpu-consumer-1 created
pod/toygpu-consumer-2 created
pod/toygpu-consumer-3 created

NAME                READY   STATUS    RESTARTS   AGE   IP            NODE           NOMINATED NODE
toygpu-consumer-1   1/1     Running   0          5s    10.244.2.22   minikube-m03   <none>
toygpu-consumer-2   1/1     Running   0          5s    10.244.2.21   minikube-m03   <none>
toygpu-consumer-3   0/1     Pending   0          5s    <none>        <none>         <none>
```

Real scheduler event on the pending Pod:

```
Warning  FailedScheduling  0/3 nodes are available: 3 Insufficient example.com/toygpu.
  no new claims to deallocate, preemption: 0/3 nodes are available:
  1 No preemption victims found for incoming pod, 2 Preemption is not helpful for scheduling.
```

The other two nodes (`minikube`, `minikube-m02`) never advertised this resource at all, so they're
"insufficient" the same as the exhausted one — the scheduler treats "doesn't have this resource"
and "has it but it's full" identically. Both consumer-1 and consumer-2 landed on the *same* node
(`minikube-m03`, the only one with capacity) — bin-packing onto the resource-bearing node, not
spread across the cluster the way CPU/memory-only Pods would be.

## Verified — extended resources are integer-only, which is exactly why MIG/time-slicing exist

```bash
kubectl apply -f - <<'EOF'
apiVersion: v1
kind: Pod
metadata: {name: toygpu-fractional-test}
spec:
  containers:
    - {name: sleeper, image: busybox:1.36, command: ["sleep","3600"],
       resources: {limits: {example.com/toygpu: "500m"}}}
EOF
```

```
The Pod "toygpu-fractional-test" is invalid:
* spec.containers[0].resources.limits[example.com/toygpu]: Invalid value: "500m": must be an integer
* spec.containers[0].resources.requests[example.com/toygpu]: Invalid value: "500m": must be an integer
```

Rejected at admission, before the scheduler is ever involved. `cpu` can be requested as `500m`
because it's a first-class, subdividable resource type; any extended resource (anything not in
Kubernetes' built-in list) is always a whole unit — you get one GPU or zero, never half. **This is
the actual reason NVIDIA MIG and time-slicing device plugins exist**: to make one physical GPU
present itself to Kubernetes as *multiple whole* extended-resource units
(`nvidia.com/gpu: 4` on a node with one physical card sliced four ways) rather than trying to make
one unit fractionally shareable — because fractional requests against a plain extended resource
aren't a validation option at all, as just demonstrated.

## What this doesn't cover (the honest boundary)

- **The device plugin's gRPC server itself** (`Register`, `ListAndWatch`, `Allocate` over a Unix
  socket at `/var/lib/kubelet/device-plugins/`) — this demo hand-patches the node status a device
  plugin would normally maintain, it doesn't implement the plugin. A toy device plugin (advertise
  N fake devices, no real hardware needed — the plugin API doesn't require one) is a legitimate
  next step and doesn't need real GPU hardware either; it's a bigger build (a gRPC server, a
  DaemonSet with a hostPath socket mount, kubelet registration) queued as a separate project
  rather than folded into this one.
- **MIG/time-slicing configuration itself** — this demo shows *why* they're needed (integer-only
  resources), not how NVIDIA's device plugin implements the slicing.
- **The vSphere/ESXi/vGPU layer** (VMware's actual angle: GPU virtualization at the hypervisor,
  below Kubernetes entirely) — genuinely can't be simulated without VMware infrastructure; stays
  conceptual per `ml-platform-engineer-roadmap.md` §4.

## Cleanup

```bash
kubectl delete -f pods.yaml       # if still applied
./unpatch-node-gpu.sh minikube-m03
```

## Reference

| File | Role |
|---|---|
| `patch-node-gpu.sh` | Advertises the fake extended resource on a node (what `ListAndWatch` does) |
| `unpatch-node-gpu.sh` | Removes it |
| `pods.yaml` | 3 pods requesting 1 unit each, against a node with capacity 2 — forces the pending case |
