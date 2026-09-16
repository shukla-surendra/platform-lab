# Installing KServe CRDs and Operator

> **Version used in this guide:** KServe `v0.20.0`
>
> KServe's current installation documentation separates the **CRD charts** from the **resources/controller chart**. The CRDs define resources such as `InferenceService`; the resources chart installs the KServe controller/operator, RBAC, webhooks, and related resources. citeturn0search0turn0search6

---

## 1. What are we installing?

The important pieces are:

```text
KServe CRD
    |
    | defines
    v
InferenceService resource type
    |
    | user creates
    v
InferenceService object
    |
    | watched by
    v
KServe Controller / Operator
    |
    | reconciles
    v
Kubernetes serving resources
    |
    v
Pods / Services / Autoscaling / etc.
```

Think:

```text
CRD       = definition
CR        = actual object
Operator  = behavior/controller
```

---

# 2. Prerequisites

You need:

- A running Kubernetes cluster
- `kubectl`
- `helm`

Verify:

```bash
kubectl version --client
helm version
```

KServe's official quickstart lists `kubectl`, Helm, and Git as required tooling. citeturn0search1

---

# 3. KServe deployment modes

KServe supports two main deployment modes:

### Standard mode

Uses normal Kubernetes deployment primitives.

```text
InferenceService
      |
      v
KServe Controller
      |
      v
Kubernetes Deployment
      |
      v
Pod
```

### Knative mode

Uses Knative for serverless behavior such as scale-to-zero and request-driven scaling.

```text
InferenceService
      |
      v
KServe Controller
      |
      v
Knative Serving
      |
      v
Revision / Pod
```

KServe's current documentation lists **Standard** and **Knative** as its two deployment modes. citeturn0search0

For learning the Kubernetes concepts, **Standard mode is easier to understand** because it uses normal Kubernetes deployment primitives.

---

# 4. Step 1 — Create the KServe namespace

```bash
kubectl create namespace kserve
```

Or let Helm create it for you with:

```bash
--create-namespace
```

---

# 5. Step 2 — Install the KServe CRDs

The official KServe Helm installation provides a dedicated `kserve-crd` chart.

Run:

```bash
helm install kserve-crd   oci://ghcr.io/kserve/charts/kserve-crd   --version v0.20.0   --namespace kserve   --create-namespace
```

This installs the **CustomResourceDefinitions**.

The official documentation recommends the OCI registry for Helm installation. citeturn0search0

---

# 6. What did Step 2 actually do?

It did **NOT** deploy your model.

It did **NOT** create a vLLM pod.

It did **NOT** create the KServe controller.

It mainly tells the Kubernetes API server about KServe's custom resource types.

Conceptually:

```text
Before:

Kubernetes API Server
        |
        +-- Pod
        +-- Deployment
        +-- Service
        +-- ...

After installing KServe CRDs:

Kubernetes API Server
        |
        +-- Pod
        +-- Deployment
        +-- Service
        |
        +-- InferenceService   <-- KServe CRD
        +-- other KServe CRs
```

Now Kubernetes understands something like:

```yaml
kind: InferenceService
```

---

# 7. Verify the CRDs

Run:

```bash
kubectl get crd
```

You should see KServe CRDs.

To specifically look for the InferenceService CRD:

```bash
kubectl get crd inferenceservices.serving.kserve.io
```

You can also run:

```bash
kubectl describe crd inferenceservices.serving.kserve.io
```

---

# 8. Step 3 — Install KServe resources/controller

Now install the KServe resources chart.

For **Standard mode**:

```bash
helm install kserve-resources   oci://ghcr.io/kserve/charts/kserve-resources   --version v0.20.0   --namespace kserve   --set kserve.controller.deploymentMode=Standard   --wait
```

The official installation documentation provides this Standard-mode Helm installation. citeturn0search0

---

# 9. What does this second Helm chart install?

The resources chart is responsible for the KServe runtime/control-plane resources, including the controller and related components.

Conceptually:

```text
kserve-resources
       |
       +-- KServe Controller
       |
       +-- RBAC
       |
       +-- Webhooks
       |
       +-- shared KServe resources
       |
       +-- configuration
```

The important component for our CRD/operator mental model is:

```text
KServe Controller
```

The current KServe Helm architecture describes the resources charts as installing controllers, RBAC, webhooks, and shared resources. citeturn0search6

---

# 10. Verify the KServe controller

Run:

```bash
kubectl get pods -n kserve
```

You should see KServe-related pods.

Also check:

```bash
kubectl get deployments -n kserve
```

You can inspect the installed Helm releases:

```bash
helm list -n kserve
```

You should have releases similar to:

```text
kserve-crd
kserve-resources
```

---

# 11. CRD vs Operator after installation

After both installation steps, your cluster conceptually looks like this:

```text
                     Kubernetes API Server
                              |
               +--------------+--------------+
               |                             |
               v                             v
        KServe CRD                    KServe Controller
               |                             |
               | defines                      | watches
               v                             |
       InferenceService <---------------------+
               |
               | actual object
               v
        my-model
               |
               | controller reconciles
               v
      Kubernetes resources
               |
        +------+------+
        |             |
        v             v
    Deployment      Service
        |
        v
       Pod
        |
        v
    Model server
```

This is the key architecture to remember.

---

# 12. Step 4 — Create an InferenceService

Once the CRD exists, Kubernetes accepts an object such as:

```yaml
apiVersion: serving.kserve.io/v1beta1
kind: InferenceService
metadata:
  name: my-model
spec:
  predictor:
    model:
      modelFormat:
        name: sklearn
      storageUri: gs://my-bucket/my-model
```

Apply it:

```bash
kubectl apply -f inference-service.yaml
```

At this point:

```text
kubectl
  |
  v
API Server
  |
  v
InferenceService object
  |
  v
KServe Controller sees it
  |
  v
KServe reconciles desired state
```

---

# 13. Important: You don't put the model inside the KServe controller pod

This is a common misunderstanding.

You have:

```text
KServe Controller Pod
        |
        | manages
        v
Model Serving Pod(s)
        |
        v
Model server
```

The KServe controller is **not** the model-serving pod.

For example, if your model server is vLLM:

```text
KServe Controller
       |
       | creates/manages
       v
Model-serving workload
       |
       v
vLLM container
       |
       v
LLM
```

The GPU/model workload is separate from the controller.

---

# 14. What happens when you create InferenceService?

Suppose you run:

```bash
kubectl apply -f inference-service.yaml
```

The flow is approximately:

```text
1. kubectl sends object
          |
          v
2. Kubernetes API Server
          |
          v
3. InferenceService stored
          |
          v
4. KServe Controller watches it
          |
          v
5. Controller reconciles desired state
          |
          v
6. Controller creates/manages serving resources
          |
          v
7. Kubernetes schedules Pods
          |
          v
8. Model server starts
```

The exact resources depend on the selected deployment mode and KServe configuration.

---

# 15. Why can't Kubernetes do this without the Operator?

Because the CRD only defines the API.

For example:

```yaml
kind: InferenceService

spec:
  predictor:
    ...
```

The API server knows:

> "This is a valid InferenceService object."

But the API server does not inherently know:

> "I should create a model-serving Deployment, configure it, expose it, and reconcile it."

That behavior comes from the KServe controller.

So:

```text
CRD
 |
 | tells Kubernetes WHAT
 v
InferenceService

KServe Controller
 |
 | tells Kubernetes HOW to make it happen
 v
Serving infrastructure
```

---

# 16. Useful verification commands

### List CRDs

```bash
kubectl get crd
```

### Check InferenceService CRD

```bash
kubectl get crd inferenceservices.serving.kserve.io
```

### List KServe pods

```bash
kubectl get pods -n kserve
```

### List KServe deployments

```bash
kubectl get deployments -n kserve
```

### List Helm releases

```bash
helm list -n kserve
```

### Check InferenceServices

```bash
kubectl get inferenceservices -A
```

or:

```bash
kubectl get isvc -A
```

`isvc` is a common short name for InferenceService.

---

# 17. Helm installation in one view

For Standard mode:

```bash
# 1. Install CRD
helm install kserve-crd   oci://ghcr.io/kserve/charts/kserve-crd   --version v0.20.0   --namespace kserve   --create-namespace

# 2. Install KServe controller/resources
helm install kserve-resources   oci://ghcr.io/kserve/charts/kserve-resources   --version v0.20.0   --namespace kserve   --set kserve.controller.deploymentMode=Standard   --wait
```

Then verify:

```bash
kubectl get crd | grep kserve
kubectl get pods -n kserve
helm list -n kserve
```

---

# 18. Alternative: install using YAML

KServe also provides YAML-based installation.

The current documentation shows:

```bash
kubectl apply --server-side   -f https://github.com/kserve/kserve/releases/download/v0.20.0/kserve.yaml
```

This installation includes the KServe CRDs and controller. The `--server-side` option is important because the InferenceService CRD is large. citeturn0search3

You can also install the built-in ClusterServingRuntimes:

```bash
kubectl apply --server-side   -f https://github.com/kserve/kserve/releases/download/v0.20.0/kserve-cluster-resources.yaml
```

For learning, however, the separate Helm commands are useful because they make the distinction between **CRDs** and **KServe resources/controller** very visible.

---

# 19. Standard vs Knative

If you choose Knative mode instead, the controller installation is:

```bash
helm install kserve-resources   oci://ghcr.io/kserve/charts/kserve-resources   --version v0.20.0   --namespace kserve   --set kserve.controller.deploymentMode=Knative   --wait
```

But Knative mode has additional dependencies. KServe's documentation recommends installing the required infrastructure such as networking and cert-manager for the Knative setup. citeturn0search3turn0search8

For a simple Kubernetes learning environment, Standard mode is usually the easier architecture to follow.

---

# 20. Uninstall

Remove the resources/controller:

```bash
helm uninstall kserve-resources -n kserve
```

Remove the CRD chart:

```bash
helm uninstall kserve-crd -n kserve
```

Then, if appropriate:

```bash
kubectl delete namespace kserve
```

**Be careful with CRD deletion:** deleting CRDs can also remove the custom resources associated with them.

---

# 21. The mental model you should remember

Don't memorize the Helm commands first.

Understand this:

```text
              INSTALL CRD
                   |
                   v
       Kubernetes learns:
       "InferenceService exists"
                   |
                   v
       CREATE InferenceService
                   |
                   v
          KServe Controller
                   |
             watches/reconciles
                   |
                   v
       Creates/manages serving
           infrastructure
                   |
                   v
              Model Pod
                   |
                   v
             Model Server
```

Or in one sentence:

> **The CRD teaches Kubernetes what an InferenceService is; the KServe Operator/Controller watches InferenceService objects and makes the required serving infrastructure happen.**

---

## Official references

- KServe Installation Guide: https://kserve.github.io/website/docs/install/kserve-install
- KServe Quickstart: https://kserve.github.io/website/docs/getting-started/quickstart-guide
- KServe Installation Concepts: https://kserve.github.io/website/docs/install/overview
