# Kubernetes CRD and Operator — Complete Mental Model

## 1. The short answer

**CRD and Operator are NOT the same thing.**

- **CRD (CustomResourceDefinition)** = tells Kubernetes **what a new resource type looks like**.
- **Custom Resource (CR)** = an actual object created from that CRD.
- **Operator** = a Kubernetes controller/program that **watches those objects and performs actions**.

A useful mental model:

```text
CRD       → Definition / vocabulary
Custom Resource → Actual request/object
Operator  → Behavior / automation
```

They commonly work together, but **neither one is technically a required part of the other**.

---

# 2. Why do we need a CRD?

Kubernetes already understands built-in resources such as:

```text
Pod
Deployment
Service
ConfigMap
Secret
```

Suppose we want Kubernetes to understand a new resource:

```text
InferenceService
```

Kubernetes does not know what `InferenceService` means by default.

We can install a CRD:

```yaml
kind: CustomResourceDefinition
```

The CRD tells the Kubernetes API server:

> "There is a new resource type called `InferenceService`."

After the CRD exists, we can create:

```yaml
apiVersion: serving.kserve.io/v1beta1
kind: InferenceService
metadata:
  name: my-model
spec:
  ...
```

This is called a **Custom Resource (CR)**.

---

# 3. CRD vs Custom Resource

This distinction is very important.

### CRD

The CRD is the **definition**.

```text
CRD
 |
 └── defines InferenceService
```

### Custom Resource

The Custom Resource is an **actual object**.

```text
InferenceService
    |
    ├── my-model
    ├── fraud-model
    └── recommendation-model
```

Think of a programming language:

```text
Class       → CRD
Object      → Custom Resource
```

For example:

```python
class InferenceService:
    ...
```

and:

```python
model = InferenceService()
```

This analogy is not perfect, but it is useful.

---

# 4. What is an Operator?

An Operator is essentially a **Kubernetes controller/program containing domain-specific operational logic**.

It continuously watches Kubernetes resources and tries to make the actual cluster state match the desired state.

For example:

```text
User
 |
 | creates InferenceService
 v
Kubernetes API Server
 |
 | stores object
 v
InferenceService object
 |
 | operator watches it
 v
KServe Operator
 |
 | creates/manages
 v
Deployment
Service
Pods
Autoscaling
Networking
etc.
```

The operator is the **behavior**.

The CRD is the **definition**.

---

# 5. Why is it called an "Operator"?

The name comes from the idea of a human **operator** who knows how to operate a system.

For example, imagine a database administrator.

A human operator knows:

```text
If database is unhealthy
    → restart it

If storage is full
    → increase storage

If replica fails
    → create another replica

If backup is missing
    → create a backup
```

A Kubernetes Operator puts this operational knowledge into software.

So instead of a human doing:

```text
observe → decide → act
```

the Operator continuously does:

```text
watch → reconcile → act
```

This is why it is called an **Operator**.

---

# 6. CRD + Operator

The most common architecture is:

```text
                 Kubernetes
                     |
              API Server
                     |
              +------v------+
              |     CRD     |
              |             |
              | defines     |
              | Inference   |
              | Service     |
              +------+------+
                     |
              Custom Resource
              InferenceService
                     |
                     |
              +------v------+
              |  Operator   |
              |             |
              | watches CR   |
              +------+------+
                     |
          +----------+----------+
          |          |          |
          v          v          v
      Deployment   Service    Autoscaling
          |
          v
        Pods
          |
          v
       vLLM/model
```

This is the mental model to remember.

---

# 7. Is the CRD part of the Operator?

### Conceptually: NO.

They are separate things.

```text
CRD
 |
 | defines
 v
Custom Resource

Operator
 |
 | watches/reconciles
 v
Custom Resource
```

However, when you install an Operator using a package such as Helm, the installation may include:

```text
Operator Deployment
+
CRDs
+
RBAC
+
Services
+
other configuration
```

So operationally they may be **installed together**.

But conceptually:

> **CRD ≠ Operator**

---

# 8. Is the Operator part of the CRD?

### No.

A CRD does not contain the operator's business logic.

A CRD primarily defines things such as:

```text
Resource name
API group
API version
Kind
Schema
Validation
```

For example:

```text
kind: InferenceService
```

The CRD tells Kubernetes:

> "This resource exists and these are its allowed fields."

It does NOT tell Kubernetes:

> "Create a Deployment, start vLLM, configure networking, scale it, etc."

That behavior comes from the Operator/controller.

---

# 9. Can I have a CRD without an Operator?

### YES.

You can install:

```text
CRD
```

without installing an Operator.

Then you can create:

```text
Custom Resource
```

and Kubernetes can store and serve that object through its API.

For example:

```bash
kubectl get inferenceservices
```

may work because Kubernetes knows the resource through the CRD.

But:

```text
No Operator
     ↓
No controller watching it
     ↓
No custom automation
```

The object is essentially **inert** with respect to custom behavior.

### Important

"Inert" means:

> The object exists, but no custom controller is acting on it.

It does NOT mean Kubernetes cannot store it.

---

# 10. Can I have an Operator without a CRD?

### YES, technically.

An Operator is fundamentally a controller/program.

It does not have to require a CRD.

A controller can watch existing Kubernetes resources such as:

```text
Pods
Deployments
Services
ConfigMaps
```

and perform custom logic.

For example:

```text
Operator
   |
   └── watches Deployments
```

No custom resource is necessarily required.

However, many Operators use CRDs because CRDs give users a clean API for expressing domain-specific desired state.

For example:

```yaml
kind: MyDatabase
```

is much cleaner than asking users to manually configure:

```text
Deployment
Service
PVC
ConfigMap
Secret
etc.
```

---

# 11. The three scenarios

## Scenario A — CRD + Operator

This is the common Operator pattern.

```text
CRD
 ↓
Custom Resource
 ↓
Operator watches it
 ↓
Operator performs actions
```

Example:

```text
KServe CRD
     ↓
InferenceService
     ↓
KServe Operator
     ↓
Deployment + Service + autoscaling/etc.
```

---

## Scenario B — CRD without Operator

```text
CRD
 ↓
Custom Resource
 ↓
No Operator
```

The API server can understand and store the object.

But there is no custom controller implementing the desired operational behavior.

Example:

```text
InferenceService
       ↓
stored in Kubernetes
       ↓
nothing automatically creates vLLM pods
```

---

## Scenario C — Operator without CRD

```text
Operator
 ↓
watches existing Kubernetes resources
 ↓
performs custom actions
```

For example, a custom controller could watch:

```text
Deployment
```

and perform some additional automation.

A CRD is therefore **not technically mandatory for every controller/operator**.

---

# 12. Why Operators commonly use CRDs

Without a CRD, users might need to configure many low-level resources.

Imagine deploying a model manually:

```text
Deployment
Service
ConfigMap
Secret
HPA
PodDisruptionBudget
Ingress
GPU configuration
```

An Operator can expose a higher-level API:

```yaml
kind: InferenceService

spec:
  model:
    image: my-vllm-image
    model: my-model
  resources:
    gpu: 1
```

Then the Operator translates this high-level desired state into the necessary Kubernetes resources.

Conceptually:

```text
                    User
                      |
                      v
             InferenceService
              (high-level API)
                      |
                      v
                 Operator
                      |
          +-----------+-----------+
          |           |           |
          v           v           v
     Deployment    Service      HPA
          |
          v
        Pod
          |
          v
        vLLM
          |
          v
       ML Model
```

This is one of the biggest benefits of an Operator.

---

# 13. KServe example

Suppose you want to serve a model using KServe.

You create:

```yaml
apiVersion: serving.kserve.io/v1beta1
kind: InferenceService

metadata:
  name: my-model

spec:
  predictor:
    model:
      modelFormat:
        name: pytorch
      storageUri: s3://models/my-model
```

You are **NOT directly creating the model Pod** here.

You are declaring:

> "I want an InferenceService called `my-model` with these desired properties."

Then:

```text
InferenceService
       |
       v
KServe Operator
       |
       v
KServe serving infrastructure
       |
       v
Pods / Deployment / Service / autoscaling
       |
       v
Model serving
```

The exact resources KServe creates/manages depend on the KServe deployment mode and configuration.

---

# 14. The most important mental model

Remember these three words:

```text
CRD       = DEFINITION
CR        = DESIRED STATE / OBJECT
OPERATOR  = BEHAVIOR
```

Or even simpler:

```text
CRD      → "What kind of thing is this?"
CR       → "What do I want?"
Operator → "I'll make it happen."
```

---

# 15. One more important distinction: Kubernetes API Server vs Operator

The API server does **not** automatically execute the meaning of every custom field.

For example:

```yaml
kind: MyModel
spec:
  replicas: 5
```

The CRD can tell Kubernetes:

> "`MyModel` exists and `replicas` is an integer."

But the API server does not inherently know:

> "Create five Pods."

The Operator/controller provides that behavior:

```text
CR
 |
 | desired state:
 | replicas = 5
 v
Operator
 |
 | reconcile
 v
5 Pods
```

---

# 16. Final picture

```text
                    KUBERNETES
                         |
                  +------v------+
                  | API Server  |
                  +------+------+
                         |
              +----------+----------+
              |                     |
              v                     v
             CRD              Built-in Resources
              |               Pod, Deployment, etc.
              |
              | defines
              v
        Custom Resource
              |
              | watched by
              v
          +---+--------+
          |  Operator  |
          +---+--------+
              |
              | reconciliation
              v
      Kubernetes Resources
       /        |              v         v         v
 Deployment   Service    HPA
      |
      v
    Pod(s)
      |
      v
  Application
```

## Bottom line

**CRD and Operator are complementary, not hierarchical.**

It is incorrect to think:

```text
Operator contains CRD
```

or:

```text
CRD contains Operator
```

A better model is:

```text
       CRD
        ↓
defines a new resource type
        ↓
       CR
        ↓
Operator watches it
        ↓
Operator reconciles desired state
        ↓
creates/updates/deletes resources
```

And this is why **CRD without Operator can exist**, and **Operator without CRD can also exist**—although the CRD + Operator combination is extremely common for Kubernetes Operators.
