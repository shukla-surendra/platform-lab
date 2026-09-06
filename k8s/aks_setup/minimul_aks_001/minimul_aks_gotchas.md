# AKS + Terraform: Gotchas Found While Building This Setup

A running list of the "wait, that could go wrong" moments that came up while building the minimal AKS setup in this folder — explained in plain language, with what actually fixes each one. Think of this as the "things nobody tells you until you hit them" doc.

## 1. Your Terraform state file can leak real cluster passwords

**What's actually happening:** Every time you run `terraform apply`, Terraform writes a file called `terraform.tfstate`. Think of it as Terraform's own "receipt" — a record of everything it built for you, so it knows what already exists next time you run it.

The problem: that receipt doesn't just say *what* it built. For an AKS cluster, it also writes down the actual admin login credentials for that cluster — a certificate, a private key, and a password — in **plain, readable text**, right there in the file.

**Why it matters:** if that file ends up in a Git repository — especially a *public* one, like this one on GitHub — anyone who can see the file can copy those credentials and get full admin control of your Kubernetes cluster. Not "read access." Full control.

**What we found in this project:** both `terraform.tfstate` files in this folder had a fully-populated admin kubeconfig sitting inside them (client certificate, client key, admin password — about 9.6KB of real credential material), plus your real Azure subscription ID and tenant ID.

**The fix:**
- Add `.terraform/`, `*.tfstate`, and `*.tfstate.backup` to `.gitignore` so Git never even offers to track them. (Already done for this repo.)
- If the cluster the leaked credentials point to is still running, treat that as a separate, real problem — rotating the credentials or destroying the cluster is worth doing regardless of whether the file ever actually got committed, simply because the secret existed on disk in a way that could have leaked.

**Small bonus gotcha:** there's also a `.terraform/providers/` folder sitting next to the state file. That's just the Azure plugin program Terraform downloaded so it knows how to talk to Azure — it's hundreds of megabytes, and running `terraform init` regenerates it instantly. No reason to ever commit that either.

## 2. Creating a container registry doesn't mean your cluster can use it

**What's actually happening:** Azure Container Registry (ACR) is basically a private warehouse for your Docker images. You build an image, push it into the warehouse, and later tell Kubernetes "go grab that image and run it."

Here's the part that surprises people: creating the warehouse next door to your factory (AKS) doesn't automatically hand your factory workers a key to walk in. Azure treats "the registry exists" and "this specific cluster is allowed to pull from it" as two completely separate permissions.

**Why it matters:** without that permission, the moment Kubernetes tries to start a pod using an image from your registry, it fails with an error called `ImagePullBackOff`. Kubernetes will sit there retrying forever, never explaining that the *real* problem is a missing permission, not a missing image.

**The fix:** grant the cluster's own "worker identity" (AKS calls it the *kubelet identity* — it's the identity actually running on your nodes, separate from the identity that manages the cluster itself) the `AcrPull` role, scoped to just that one registry:

```hcl
resource "azurerm_role_assignment" "aks_acr_pull" {
  principal_id                     = azurerm_kubernetes_cluster.aks.kubelet_identity[0].object_id
  role_definition_name             = "AcrPull"
  scope                            = azurerm_container_registry.acr.id
  skip_service_principal_aad_check = true
}
```

**A gotcha hiding inside this fix:** right after Azure creates that kubelet identity, its own internal directory (Azure AD) can take a few seconds to fully "know about" the new identity everywhere. If Terraform tries to double-check that the identity exists *before* granting it the role, that check can fail with a confusing "principal not found" error — even though the identity is completely valid, it just hasn't finished propagating yet. The `skip_service_principal_aad_check = true` line tells Terraform "don't bother double-checking, just apply the permission" — which sidesteps that timing race entirely.

**Status:** this one is already fixed in the current setup.

## 3. Two node pools don't mean your workloads are actually separated

**What's actually happening:** Picture two office buildings on the same campus — one for critical staff only (the *system* pool, running things Kubernetes itself needs to function), and one for everyone else (the *user* pool, meant for your applications).

Just constructing the second building doesn't stop people from wandering into the first one and taking up desks there. Kubernetes' scheduler (the thing that decides which machine runs which piece of software) doesn't know "this pool is special" unless you tell it. Left alone, it'll happily put your application pods on the system pool, and system pods on your application pool — whichever has room.

**The two tools that actually create separation:**
- A **taint** is like a sign on a door: "staff only, unless you're carrying a pass." In Kubernetes, the matching pass is called a **toleration**.
- A **nodeSelector** works the other direction — it's a note on an employee's badge saying "always place me in the second building specifically."

**The fix, the easy way:** AKS gives you a one-line way to taint the system pool:

```hcl
default_node_pool {
  name           = "system"
  vm_size        = "Standard_D4s_v5"
  node_count     = 1
  vnet_subnet_id = azurerm_subnet.aks.id
  only_critical_addons_enabled = true
}
```

This isn't a made-up taint — it's AKS's own built-in convention (`CriticalAddonsOnly=true:NoSchedule`), and AKS's own critical background processes (things like CoreDNS, which is how pods find each other by name) already carry the matching "pass," so they're unaffected. Everything else — meaning your own applications — gets turned away from that pool.

To finish the picture, your application's Kubernetes deployment should also say which pool it *wants* (this part lives in your app's Kubernetes YAML, not in this Terraform file):

```yaml
nodeSelector:
  agentpool: userpool
```

AKS automatically labels every node with which pool it belongs to, so no extra setup is needed for that label to exist — you're just telling your own deployment to look for it.

**Why you generally want both, not just one:** the taint stops the system pool from accepting your pods. The nodeSelector tells your pods exactly where to go. Without the taint, the user pool alone doesn't stop critical pods from wandering onto it. Without the nodeSelector, your pods have no explicit preference if you ever add a third pool later.

**Status:** not yet applied — this is still an open gap in the current setup.

## 4. Two different "auto-scaling" systems exist, and mixing them on the same pool is not allowed

**What's actually happening:** "Scaling" just means "deciding how many machines to run, and when to add or remove one." AKS actually offers two different systems that can make that decision, and they think about the problem in opposite ways:

- **The classic way — Cluster Autoscaler:** you tell each node pool directly, "stay between 1 and 5 machines; add more if things get busy." It watches the pool.
- **The newer way — Node Autoprovisioning (NAP):** this is Microsoft's version of an open-source tool called Karpenter. Instead of watching pools, it watches *pending pods* (pieces of your application waiting for somewhere to run) and creates whatever machine best fits them, on demand.

**Why it matters:** you cannot put both systems in charge of deciding the size of the *same* pool. Each one assumes it's the only one making that decision, and Azure will simply refuse the configuration if you try to enable the classic autoscaler on a pool while NAP (`mode = "Auto"`) is switched on for the cluster.

**Where this project actually stands:** the manually-created user pool in this setup has no auto-scaling turned on at all right now — it's a fixed size (`node_count = 1`). So today, there's no real conflict; NAP mode and the static pool simply aren't touching each other.

This only becomes a real problem the moment someone later adds classic autoscaling (`enable_auto_scaling = true` plus `min_count`/`max_count`) directly onto that same manually-defined pool, while NAP mode is still `Auto` for the cluster.

**The decision you'll eventually need to make** (not a code fix — an either/or choice):
1. **Turn NAP off** for the cluster and autoscale the user pool the classic way, or
2. **Keep NAP on**, and let it create/manage extra capacity itself through its own mechanism (separate Kubernetes objects called `NodePool` and `AKSNodeClass`) — leaving the manually-defined pool as a fixed-size pool for anything you specifically want pinned rather than dynamically created.

Either is valid; you just can't do both to the same pool at once.
