# vLLM + Ray + KubeRay + Kubernetes: how the four layers fit together

The four names show up together constantly in LLM-serving architecture diagrams, and
it's easy to walk away thinking they're four competing choices. They're not — each
one answers a *different* question, and normally only shows up once the layer below
it stops being enough:

```
vLLM         "how do I run this one model efficiently on a GPU?"
Ray           "how do I run work — this model included — across many GPUs/machines?"
KubeRay        "how do I run a Ray cluster as a Kubernetes-native, declarative resource?"
Kubernetes      "how do I manage the containers/Pods/nodes/GPUs underneath all of that?"
```

One sentence version: **vLLM is the LLM inference engine, Ray is the
distributed-computing layer underneath it, KubeRay is the Kubernetes operator that
runs Ray *as* Kubernetes resources, and Kubernetes manages the infrastructure all
three sit on.** None of them replaces another — each is scoped to a narrower problem
than the one below it.

## Ray: the layer vLLM and KubeRay both sit on

[Ray](../ray/README.md) is a general-purpose Python distributed-computing framework
(tasks, actors, an object store) — not LLM-specific at all. It's covered in depth,
hands-on, with real benchmarks, in that doc. The short version relevant here: Ray
gives you a way to run arbitrary Python work across many CPUs/GPUs/machines without
hand-rolling the coordination yourself.

## KubeRay: Ray, expressed as a Kubernetes resource

[KubeRay](README.md) is a Kubernetes **operator** — it turns "a Ray cluster" (a head
process + worker processes) into a `RayCluster` custom resource that Kubernetes
itself reconciles, instead of a cluster you'd stand up by hand with `ray up` or raw
Pods. Full mechanism, autoscaling model, and a verified hands-on demo (including what
actually broke running it locally) are in [`README.md`](README.md) in this same
folder — this doc doesn't repeat that; it focuses on where **vLLM** fits into the
stack, which the main doc doesn't cover.

Different scaling questions, stacked:

```
Ray workload demand (tasks/actors waiting for resources)
        ↓
Ray's own autoscaler decides more Ray workers are needed
        ↓
KubeRay turns that into more worker Pods
        ↓
If the Kubernetes cluster itself is out of node capacity...
        ↓
a Kubernetes cluster-autoscaler (separate, K8s-native) adds nodes
```

Kubernetes' own autoscaler reasons in Pods/nodes — it has no idea what a "task" or
an "actor" is. Ray reasons in exactly those terms, but has no idea how to provision
a Kubernetes node. KubeRay is the piece that lets Ray's workload-level scaling
decisions actually turn into Kubernetes-level Pod changes.

## Where vLLM actually plugs in

[vLLM](../vllm/README.md) (full doc: what PagedAttention and continuous batching
are, how it compares to TGI/TensorRT-LLM/Ollama) is the piece that makes serving
*one* model efficient — the KV-cache/batching mechanics, not the multi-machine
story. The multi-machine story only shows up once a model, or the request volume,
outgrows a single GPU or a single node:

```
                                  single GPU, model fits
Client → vLLM → GPU                    (no Ray at all)


                                  single node, multiple GPUs — tensor parallelism
Client → vLLM → [GPU0, GPU1, GPU2, GPU3]
                (vLLM's own multiprocessing backend handles this — still no Ray)


                                  multiple nodes — the model or the traffic
                                  no longer fits on one machine
Client → vLLM → Ray → [Node1: GPU GPU]
                       [Node2: GPU GPU]
                       [Node3: GPU GPU]
```

**The mechanism, concretely:** vLLM has a `distributed_executor_backend` setting
with two options — `"mp"` (Python multiprocessing, the default) and `"ray"`. Single
node, multiple GPUs, tensor-parallel across them: `"mp"` is enough — it's just local
processes talking over NCCL, no cluster coordination needed. The moment the
deployment spans **multiple nodes** (the model doesn't fit on one machine's GPUs, or
pipeline parallelism is split across nodes, or you're running many model replicas
that need a shared scheduler), vLLM switches to `"ray"` — at that point it's Ray
doing the actual cross-node process placement and coordination, with vLLM's engine
running inside the workers Ray manages. **This is the concrete answer to "why does
Ray show up in vLLM's dependency tree at all": vLLM doesn't reimplement multi-node
orchestration — it delegates to Ray for it, the same way it delegates KV-cache
management to PagedAttention instead of reinventing memory allocation.**

So: **you don't need Ray just because you're using vLLM.** You need it once the
deployment crosses the single-node boundary. And you don't need KubeRay just because
you're using Ray — you need it once you want that Ray cluster to be a
Kubernetes-native, declarative resource instead of something stood up out-of-band.

## The full stack, layered

```
Client
  │
  ▼
vLLM / serving layer      ← efficient single-model inference (PagedAttention, batching)
  │
  ▼
Ray                       ← cross-node distributed execution (only if multi-node)
  │
  ▼
KubeRay                   ← runs that Ray cluster as a Kubernetes RayCluster resource
  │
  ▼
Kubernetes                ← Pods, nodes, GPU scheduling, the infra underneath all of it
```

Each arrow is optional in isolation — a single-GPU vLLM deployment never touches Ray
or KubeRay at all — but once you *do* see all four in one architecture diagram, this
is why: multi-node LLM serving, running on a Kubernetes-managed GPU fleet.

## Relationship to other docs in this repo

- **[KubeRay `README.md`](README.md)** — the operator itself: what problem it
  solves, the two-loop autoscaling model, a verified `RayCluster` running locally
  on minikube, and the real gotchas hit getting there (a job-submission bug, a
  `kubectl exec`-triggered raylet crash, probe flakiness under host CPU load). Read
  that first if the question is "how does KubeRay actually work," not "where does
  vLLM fit."
- **[Ray `README.md`](../ray/README.md)** — Ray Core itself, hands-on: tasks,
  actors, the object store, verified benchmarks including a case where Ray makes
  things *slower*. This doc assumes that one as background.
- **[vLLM `README.md`](../vllm/README.md)** — PagedAttention, continuous batching,
  how vLLM compares to TGI/TensorRT-LLM/Ollama/SGLang, and where it fits against
  this repo's existing Ollama-based GenAI demos and the KServe inference chart.
  Doesn't currently cover the Ray backend mechanism above — this doc is the more
  detailed source for that specific question until it's merged in there.
- **[`k8s/k8s_explorer/kuberay-demo/`](../../../../k8s/k8s_explorer/practice/kuberay-demo/README.md)**
  — the actual runnable KubeRay demo referenced above, on minikube.
