# 5. Device plugin deep dive: the protocol, and NVIDIA's implementation

`02-plugin-interfaces-reference.md` named device plugins as one of the six
plugin interfaces and pointed at
`fundamentals/gpu_infrastructure/phase4_kubernetes_gpu/09_gpu_operator_and_device_plugin.md`
for why they exist and how the GPU Operator packages one for production.
This doc goes one level deeper than that one: the actual gRPC contract
`kubelet` and a device plugin speak to each other, and exactly what the
NVIDIA device plugin does on each side of it. Read that doc first if "why
does Kubernetes need this at all" isn't already answered for you; this one
assumes it is.

## The problem, in one sentence

`kubelet` natively understands exactly two schedulable resources — `cpu`
and `memory`. A GPU is neither; something has to tell `kubelet` "this node
has N of a thing called `nvidia.com/gpu`," and separately, "when a
container asks for one, here's specifically what to give it." The Device
Plugin API is the fixed contract that "something" has to implement.

## Registration — how kubelet learns a plugin exists

Every device plugin runs as a process on the node (in practice, a
container inside a `DaemonSet` pod) and, at startup, does two things:

1. **Starts its own gRPC server** on a Unix domain socket under
   `/var/lib/kubelet/device-plugins/` (e.g. `nvidia.sock`), implementing
   the `DevicePlugin` service (below).
2. **Calls `kubelet`'s `Registration` gRPC service** (kubelet itself runs
   this on a well-known socket in the same directory) with: the resource
   name it wants to advertise (`nvidia.com/gpu`), the API version it
   speaks, and the path to its own socket from step 1.

From this point, `kubelet` is the **client** and the plugin is the
**server** for everything that follows — the opposite direction from most
Kubernetes components, and worth holding onto: `kubelet` calls into the
plugin, never the reverse.

## The `DevicePlugin` gRPC service — what the plugin must implement

- **`GetDevicePluginOptions`** — a capabilities handshake (does this
  plugin implement the optional RPCs below).
- **`ListAndWatch`** *(streaming)* — the plugin pushes its current device
  list down this one long-lived stream: each device's ID and health
  (`Healthy`/`Unhealthy`). `kubelet` uses every update to recompute this
  node's `status.capacity`/`status.allocatable` for that resource name —
  this is the literal mechanism behind an entry showing up (or
  disappearing) under `kubectl describe node`. A device going
  `Unhealthy` mid-stream (a real GPU fault, detected via NVML) makes
  `kubelet` stop advertising that unit without restarting anything.
- **`Allocate`** — called once per container that requested this resource,
  at container-creation time, with the specific device IDs `kubelet` has
  decided to hand it (drawn from the IDs `ListAndWatch` reported as
  healthy and not already allocated elsewhere — that bookkeeping is
  `kubelet`'s job, not the plugin's). The plugin's response can include
  environment variables, volume mounts, device nodes, and annotations to
  inject into the container **before** the container runtime (CRI, per
  `02-plugin-interfaces-reference.md`) actually creates it.
- **`GetPreferredAllocation`** *(optional)* — lets the plugin hint which
  specific device IDs it'd prefer for a given request, ahead of the real
  `Allocate` call — how a topology-aware plugin can favor devices on the
  same NUMA node/NVLink domain instead of `kubelet` picking arbitrarily
  (relevant background: `fundamentals/gpu_infrastructure/phase3_gpu_networking/`).
- **`PreStartContainer`** *(optional)* — a hook to run before the
  container starts, for plugins needing per-container setup beyond what
  `Allocate`'s response alone can express.

## What the scheduler sees vs. what actually happens

`kube-scheduler` treats `nvidia.com/gpu` as a completely opaque integer
resource, exactly like `cpu`/`memory` — it filters/scores nodes on
"does `Allocatable.nvidia.com/gpu` cover this Pod's request," with zero
awareness that GPUs differ in compute capability, memory, or
interconnect topology. All of that nuance either doesn't factor into
scheduling at all, or is pushed onto `GetPreferredAllocation` /
node-labeling + `nodeSelector`/`nodeAffinity` — the scheduler's own
resource-accounting logic is not GPU-aware in any way.

## NVIDIA's implementation, concretely

- **Discovery**: the plugin container (part of the NVIDIA device plugin
  `DaemonSet`, running on GPU nodes only) enumerates physical GPUs via
  **NVML** (the same library `nvidia-smi` is built on).
- **What `ListAndWatch` reports**: by default, **one device entry per
  physical GPU** — whole-GPU granularity only. There is no built-in way to
  request `nvidia.com/gpu: 0.5`; MIG (real hardware partitioning) and
  time-slicing (a newer, software-level sharing config via a `ConfigMap`
  setting `replicas` per GPU) are the two ways around that, covered in
  full in
  `fundamentals/gpu_infrastructure/phase4_kubernetes_gpu/10_gpu_scheduling_mig_sharing.md`
  — not re-explained here to avoid duplicating that doc.
- **What `Allocate` actually returns**: not raw `/dev/nvidiaN` bind
  mounts directly (a common assumption) — the plugin's response mainly
  sets the `NVIDIA_VISIBLE_DEVICES` environment variable to the specific
  GPU UUIDs assigned to this container. The actual work of exposing the
  driver's device nodes and userspace libraries *inside* the container is
  done by a **separate** component: the **NVIDIA Container Toolkit**,
  registered as an OCI runtime hook (`nvidia-container-runtime`) that
  fires during container creation and reads that same environment
  variable. This split — device plugin decides *which* GPU, container
  toolkit does the *actual injection* — is the single most commonly
  misunderstood part of this whole path; getting it wrong looks like
  "the device plugin should have mounted the device but didn't," when the
  real missing piece is usually the container toolkit / runtime hook not
  being configured as the node's OCI runtime at all.

## End-to-end, for one Pod

```
1. Pod requests resources.limits: {nvidia.com/gpu: 1}
2. kube-scheduler picks a node whose Allocatable.nvidia.com/gpu >= 1
     (opaque integer comparison, no GPU-specific reasoning)
3. kubelet on that node calls the NVIDIA device plugin's Allocate,
     passing the specific device ID(s) it has reserved for this Pod
4. Plugin's AllocateResponse sets NVIDIA_VISIBLE_DEVICES=<GPU-uuid>
5. CRI (containerd/CRI-O) creates the container; the NVIDIA Container
     Toolkit's OCI runtime hook fires, reads NVIDIA_VISIBLE_DEVICES,
     and bind-mounts the actual device nodes + driver libraries in
6. The container's process can now call into CUDA and see exactly
     the GPU(s) it was allocated -- nothing else on the node
```

## Why this matters beyond trivia

Debugging "my Pod can't see the GPU" now decomposes into a specific
checklist instead of a shrug: is the device plugin `DaemonSet` even
running and healthy on that node (`ListAndWatch` reporting the device as
`Healthy`)? Did the scheduler actually place the Pod on a GPU node (check
`Allocatable`)? Is the container runtime configured with the NVIDIA
runtime hook at all (a cluster-config problem, not a plugin problem)? Each
question maps to one distinct component in the chain above, which is the
entire reason to know the chain in the first place — same value this
repo's `k8s/docs/rbac/FAQ.md` gets from decomposing a 403 into "which
exact stage rejected it."
