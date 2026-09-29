# 17 · How Terraform works inside

## 🎯 Goal

Explain on a whiteboard what happens inside Terraform from `init` to the
end of `apply`: how Core and providers talk, how the dependency graph is
built and walked, what "unknown values" really are, and why certain
errors happen. This is where senior interviews separate "uses Terraform"
from "understands Terraform".

---

## 🧠 Mental model: a general contractor and specialists

- **Terraform Core** is the **general contractor**. It reads the
  blueprints (your config), keeps the project records (state), and decides
  the *order* of work (the graph). It never lays a brick itself.
- **Providers** are **specialist subcontractors**: the AWS one knows how
  to build EC2 instances, the GitHub one knows repositories. Core asks
  each specialist "what would it take?" (plan) and then "do it" (apply).
- They talk over a **fixed contract**: the plugin protocol.

```
 ┌──────────────────────────── terraform (Core, one Go binary) ─────────────────────────────┐
 │  config loader (HCL)  ·  state manager  ·  graph builder  ·  graph walker  ·  plan/apply  │
 └──────────────┬───────────────────────────────┬───────────────────────────────┬───────────┘
          gRPC  │                         gRPC  │                         gRPC  │
 ┌──────────────▼──────────┐   ┌────────────────▼────────┐   ┌──────────────────▼──────────┐
 │ terraform-provider-aws  │   │ terraform-provider-random│   │ terraform-provider-github  │
 │  (separate process)     │   │                          │   │                            │
 └──────────────┬──────────┘   └──────────────────────────┘   └────────────────────────────┘
                │ AWS SDK for Go (HTTPS, SigV4-signed requests)
           AWS APIs: EC2, S3, IAM, RDS …
```

---

## 🛠 Walkthrough

### Step 1: Core and providers are separate programs

When Terraform needs a provider, it **starts the provider binary as a
child process** (from `.terraform/providers/...`). They connect like this:

1. Core launches the plugin with a special environment "magic cookie", so the binary knows it's being run by Terraform.
2. The plugin starts a **gRPC server** on a local socket and prints a handshake line on stdout (protocol version, network address).
3. Core connects as a gRPC **client**. All further talk is gRPC calls.
4. When Core is done, it tells the plugin to stop.

This design (HashiCorp's `go-plugin` library) is why:
- providers are **versioned and released independently** of Terraform;
- a provider crash doesn't corrupt Core, which reports the plugin crashed;
- providers can be written by anyone, in principle in any language (in practice, Go).

Two versions of the protocol are in use, **5 and 6**. Providers are built
with HashiCorp's SDKs: the older `terraform-plugin-sdk/v2` or the newer
`terraform-plugin-framework`. The AWS provider uses both (combined
through "muxing"), and it calls AWS using the **AWS SDK for Go v2**.

### Step 2: the provider contract (the RPCs)

These are the main calls Core makes. You don't need to memorise them,
but knowing they exist explains a lot:

| RPC | When | Purpose |
|---|---|---|
| `GetProviderSchema` | early, every run | "describe every resource, data source, and argument you support" |
| `ValidateProviderConfig` / `ValidateResourceConfig` | validate / plan | static checks on your config |
| `ConfigureProvider` | before use | hand over region, credentials, assume_role… |
| `UpgradeResourceState` | reading state | migrate stored attributes written by an older provider schema |
| **`ReadResource`** | refresh | "what does this object look like in AWS now?" |
| **`PlanResourceChange`** | plan | "given prior state + desired config, what will the new state be? Does it need replacing?" |
| **`ApplyResourceChange`** | apply | "make it so", and return the new state |
| `ImportResourceState` | import | "turn this ID into a state entry" |
| `ReadDataSource` | plan (or apply) | read a data source |
| `CallFunction` | anytime | provider-defined functions (1.8+) |

`GetProviderSchema` explains why **`terraform validate` needs `init`**:
Terraform can't know whether `instance_type` is a valid argument of
`aws_instance` until the provider tells it.

### Step 3: `terraform init` internals

1. **Backend init**: read the `backend` block and connect to it (S3).
2. **Module install**: download every `module` source into `.terraform/modules/`, recursively.
3. **Provider install**:
   - collect version constraints from the root *and* all modules;
   - intersect them, and choose the newest version that satisfies every constraint **and** the lock file;
   - discover the registry (`registry.terraform.io/.well-known/terraform.json`), download the zip for your OS and architecture;
   - **verify** it against checksums (and the publisher's signature), then record the hashes in `.terraform.lock.hcl`.

Tip: set `TF_PLUGIN_CACHE_DIR` to share one download of the ~500 MB AWS
provider across all your projects.

### Step 4: loading the configuration

Core parses every `.tf` / `.tf.json` file in each module directory (the
HCL details are in lesson 18) into an in-memory **configuration tree**:
root module → child modules → their resources, variables, and so on.

At this stage, a resource block's body is still **undecoded**. Core knows
"there's an `aws_instance` called `web`", but it checks the arguments
inside only after it has the AWS provider's schema.

### Step 5: building the graph

Core builds a **directed acyclic graph (DAG)**. The nodes aren't only
resources:

```
 nodes: provider configs · resources · data sources · variables · locals · outputs · module calls
 edges: "must be evaluated before"
```

It's built by a pipeline of **graph transformers**, roughly:

1. add a node for every resource in the **config**;
2. add nodes for resources only in the **state** (orphans, which get destroyed);
3. add variable, local, output, and provider nodes;
4. **reference edges**: for every expression, find what it references (`aws_vpc.main.id`) and add an edge. This is done by **static analysis** of the expression, without evaluating it (lesson 18);
5. add `depends_on` edges;
6. connect each resource to its provider node (the provider must be configured first);
7. check for **cycles**, and simplify with a transitive reduction.

If there's a cycle, you get:

```
Error: Cycle: aws_security_group.a, aws_security_group.b
```

The classic cause is two security groups whose inline rules reference
each other. The fix is to break the cycle: create both groups without
rules, then add the rules as separate `aws_vpc_security_group_ingress_rule`
resources that reference both.

### Step 6: walking the graph

Core walks the graph **concurrently**: any node whose dependencies are
done can start, limited by a **semaphore of 10** (`-parallelism`). That's
why independent resources are created at the same time, and why a 100-resource
apply doesn't take 100× as long.

`count` and `for_each` are handled by **dynamic expansion**: the graph
first has one node for `aws_subnet.private`. When the walker reaches it,
it evaluates `for_each`, and *then* expands it into
`["ap-south-1a"]`, `["ap-south-1b"]`… sub-nodes. It can only do that if the
`for_each` value is **known**. That's the root of the famous error
(see Step 8).

### Step 7: what happens to ONE resource during plan

```
          prior state (from last apply)
                    │
                    ▼
     UpgradeResourceState   (old schema → current schema)
                    │
                    ▼
          ReadResource ───────────────▶ AWS: DescribeInstances(i-0a1b…)
                    │                   (refresh: the "current" object)
                    ▼
     evaluate config expressions  (references resolved from other nodes' planned values)
                    │
                    ▼
     "proposed new state" = config values + prior values for computed attributes
                    │
                    ▼
     PlanResourceChange ─────────────▶ provider decides:
                    │                   - planned new state (may contain UNKNOWN values)
                    │                   - RequiresReplace: [ "ami" ]   ← "# forces replacement"
                    ▼
     Core picks the action:  no-op · create · update · replace (-/+ or +/-) · delete
```

Two important consequences:

- **"forces replacement" comes from the provider**, not from Core. The provider schema marks which attributes can't be updated in place.
- A **plan is the provider's prediction.** At apply, the provider must return a result consistent with it (Step 10).

### Step 8: unknown values, "(known after apply)"

When the plan is built, many values don't exist yet: the ID of an
instance not yet created, or its IP. Terraform represents them as
**unknown values**. They're real, typed placeholders ("an unknown string"),
not empty strings.

Unknowns **propagate**: anything computed from an unknown is also unknown.

```hcl
resource "aws_instance" "web" { ... }                     # id: unknown at plan

locals {
  url = "http://${aws_instance.web.public_ip}/"           # unknown too
}
```

This explains three things you'll meet:

1. **`(known after apply)`** in plans.
2. **`Invalid for_each argument` / `Invalid count argument`.** Graph
   expansion (Step 6) needs to know *how many* instances exist during
   planning, so an unknown count or for_each can't be expanded. Hence the
   rule: keys must come from values you control (lesson 09). (The
   last-resort workaround is `-target` to create the dependency first.
   Newer Terraform versions are adding "deferred actions" for this, but
   don't rely on them in interviews.)
3. **Data sources read during apply** (`<=`) when their arguments are unknown.

> **Advanced detail.** Since Terraform 1.6, unknown values can carry
> **refinements**, like "this unknown string is definitely not null" or
> "starts with `arn:`". That lets expressions like
> `aws_instance.web.id != null` be *known* (`true`) during plan, which
> makes some previously failing conditions work.

### Step 9: the saved plan file

`terraform plan -out=tfplan` writes a zip containing:

- a **snapshot of the configuration** and the **prior state**;
- every planned change (with before and after values, **including secrets**);
- variable values, and the provider and dependency lock details.

`terraform apply tfplan` refuses to run if the state has changed since the
plan was made (the state's serial and lineage no longer match). That's
the guarantee that you apply exactly what was reviewed. **Treat plan files
as secrets.**

### Step 10: what happens during apply

1. Core builds an **apply graph** from the plan (only nodes with changes, plus what they need).
2. It walks it, ordered by dependencies, with parallelism 10.
3. For each change: `ApplyResourceChange(prior, planned, config)`, and the provider calls AWS:
   - **create**: e.g. `RunInstances`, then **waits** until the instance is `running` (providers contain waiters and retries);
   - **update**: e.g. `ModifyInstanceAttribute`;
   - **delete**: e.g. `TerminateInstances`, and wait until it's gone.
4. The provider returns the **new state**. Core checks it against the plan:
   every value that was *known* at plan time must match. If not:

   ```
   Error: Provider produced inconsistent result after apply
   ... This is a bug in the provider, which should be reported in the provider's own issue tracker.
   ```

   That message really does mean a provider bug, or an API that changed
   the value you sent (for example by normalising a JSON policy).
5. **The state is persisted as it goes**, not only at the end. If apply
   fails halfway, completed resources are already recorded.

Replacement order: by default **destroy then create**. With
`create_before_destroy`, **create, then update the dependents, then destroy
the old one**. The *destroy* half of any apply walks the graph in
**reverse** order.

### Step 11: how the AWS provider copes with AWS itself

- **Throttling**: AWS APIs rate-limit. The provider retries with
  exponential backoff (you may see slow applies in big accounts, and
  lowering `-parallelism` can help).
- **Eventual consistency**: a new IAM role isn't usable everywhere
  instantly. The provider retries known cases ("role cannot be assumed")
  for a while, which is why IAM-dependent creates sometimes take ~10s longer.
- **Waiters**: Terraform waits for resources to become ready (RDS
  `available` can take 10+ minutes). The `timeouts` block extends this.

### Step 12: debugging the internals

```bash
TF_LOG=DEBUG terraform plan              # TRACE, DEBUG, INFO, WARN, ERROR
TF_LOG_CORE=TRACE TF_LOG_PROVIDER=DEBUG  # separate levels for Core and providers
TF_LOG_PATH=./tf.log                     # write to a file
terraform graph -type=plan | dot -Tsvg > graph.svg
```

At DEBUG level you'll see every gRPC call and the actual AWS HTTP requests
(e.g. `Action=RunInstances`). That's the fastest way to learn what a
resource really does. **The logs contain secrets**, so don't paste them publicly.

---

## ⚠️ Common misconceptions

- **"Terraform talks to AWS."** Core never does. Only the provider process does.
- **"Order in files matters."** Only the graph matters.
- **"Plans are guaranteed."** A plan is the provider's prediction. APIs can still reject the apply (quotas, permissions, name taken).
- **"Terraform rolls back on failure."** No. It persists partial progress and you fix forward.
- **"`(known after apply)` means an empty value."** It's a typed unknown placeholder that propagates through expressions.

---

## 🎤 Interview corner

**Q: Explain Terraform's architecture.**

> Terraform Core is a single binary that parses configuration, manages
> state, builds a dependency graph, and orchestrates plan and apply.
> Providers are separate plugin binaries that Core launches as child
> processes and talks to over gRPC using the plugin protocol (v5/v6).
> Providers expose schemas and implement CRUD for resources by calling
> vendor APIs. For AWS, that's the AWS SDK for Go. This decoupling lets
> providers be versioned and released independently.

**Q: What happens internally during `terraform plan`?**

> Core loads the config tree and state and gets provider schemas. It
> builds a DAG from config, state, and statically-analysed references,
> then walks it in parallel. For each resource it upgrades and refreshes
> the prior state via `ReadResource`, evaluates the configuration, and
> calls `PlanResourceChange` with prior state and proposed new state. The
> provider returns the planned state (possibly with unknown values) and
> the attributes requiring replacement. Core aggregates the actions into
> the plan. Nothing is modified.

**Q: Why can't `for_each` depend on a resource attribute like an instance ID?**

> `count` and `for_each` determine how many resource instances exist, and
> the graph has to be expanded during planning. If the value depends on
> something only known after apply, Terraform can't know the set of
> instances, so it can't produce a complete plan. Keys must come from
> known values. Unknown values can still be used inside each instance's
> arguments.

**Q: What does "Provider produced inconsistent result after apply" mean?**

> After apply, the provider returned a value that differs from a value it
> promised during plan. Core enforces that known planned values match.
> It's usually a provider bug, or the remote API normalising or altering
> input. The resource may exist but the state is suspect, so you re-plan,
> and often report it upstream.

**Q: How does Terraform achieve parallelism, and how do you control it?**

> It walks the DAG concurrently: any node whose dependencies are complete
> can run, bounded by a semaphore defaulting to 10, adjustable with
> `-parallelism=N`. Lowering it helps with API throttling.

---

## ✅ Check yourself

1. Which process actually sends HTTP requests to the EC2 API?
2. Why does `terraform validate` fail before `terraform init`?
3. Where does the "# forces replacement" decision come from?
4. What happens if you `terraform apply tfplan` after a teammate applied a different change to the same state?
5. Two security groups with inline rules referencing each other. What error, and what fix?

<details><summary>Answers</summary>

1. The AWS provider process (via the AWS SDK), not Terraform Core.
2. Validation needs the provider schemas, which come from the provider binaries that `init` downloads.
3. From the provider's `PlanResourceChange` response (the `RequiresReplace` attribute paths, based on its schema).
4. Terraform refuses: the saved plan is stale because the state changed since it was created. You re-plan.
5. `Error: Cycle`. Create the groups without inline rules, and define the rules as separate resources.

</details>

➡️ **Next:** [18 · HCL internals](18-hcl-internals.md)
