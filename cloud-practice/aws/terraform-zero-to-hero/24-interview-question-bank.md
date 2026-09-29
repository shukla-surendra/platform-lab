# 24 · Interview question bank

**How to use this:** cover the answer, say yours **out loud** (interviews
are spoken), then compare. The answers are deliberately compact: they're
what a strong candidate says in 30–60 seconds. The lesson number in
brackets is where to go deeper.

Levels: 🟢 junior · 🟡 mid · 🔴 senior/staff

---

## A. Fundamentals

**🟢 1. What is Terraform?** [01]
A declarative Infrastructure-as-Code tool. You describe the desired end
state in HCL, and Terraform computes and executes the changes via
provider plugins, tracking what it manages in a state file.

**🟢 2. Declarative vs imperative IaC?** [01]
Imperative = a sequence of steps, so you handle the current state yourself.
Declarative = the end state, where the tool diffs and converges. Terraform
is declarative, which makes applies idempotent.

**🟢 3. What does `terraform init` do?** [02, 17]
It initialises the backend, downloads modules, and installs providers that
satisfy the constraints and the lock file (verifying checksums). Re-run it
after changing providers, modules, or the backend.

**🟢 4. `plan` vs `apply`?** [03]
`plan` refreshes, diffs, and shows proposed changes without changing
anything. `apply` executes a plan (a fresh one or a saved one) and updates state.

**🟢 5. What do `+`, `~`, `-/+`, `+/-`, `-`, `<=` mean in a plan?** [03]
Create; update in place; replace (destroy first); replace (create first,
create_before_destroy); destroy; data source read during apply.

**🟢 6. What's a provider?** [05]
A plugin that implements resources and data sources for an API (AWS,
GitHub…). Core talks to it over gRPC.

**🟢 7. Resource vs data source?** [06]
A resource is managed (CRUD + state). A data source is read-only lookup.

**🟡 8. Terraform vs CloudFormation?** [01]
Both are declarative. CloudFormation is AWS-only with AWS-managed state
and automatic rollback. Terraform is multi-provider with self-managed
state, a big ecosystem, a pre-apply plan, and no automatic rollback (fix forward).

**🟡 9. Terraform vs Ansible?** [01]
Terraform provisions infrastructure declaratively with state. Ansible is
mainly configuration management inside machines (procedural-ish,
agentless, no state). They're complementary.

**🟡 10. What is OpenTofu, and why does it exist?** [01, 18]
An open-source (MPL) fork of Terraform created after HashiCorp moved
Terraform to the Business Source License in 2023. It's largely
compatible, and has added its own features (e.g. state encryption, early
evaluation of variables in backend/module source).

---

## B. HCL and the language

**🟢 11. What are the Terraform data types?** [04]
Primitive: string, number, bool. Collection: list, set, map (one element
type). Structural: object, tuple (per-attribute/position types). Plus
`any` and `null`.

**🟡 12. Map vs object? List vs tuple?** [04, 18]
Map/list: one element type, any size. Object/tuple: a fixed schema with
per-element types. Literals start as object/tuple and are converted when
a constraint requires it.

**🟢 13. Variables vs locals vs outputs?** [07]
Inputs set by callers, internal derived values, and exported values.

**🟡 14. Variable precedence?** [07]
Default < `TF_VAR_` env < `terraform.tfvars` < `terraform.tfvars.json` <
`*.auto.tfvars(.json)` (lexical) < `-var`/`-var-file` (the last one on the
command line wins).

**🟡 15. What does `sensitive = true` do?** [07, 19]
It redacts values in CLI output and propagates to derived values. It does
**not** encrypt: the value is still plain text in state and plan files.

**🟡 16. How do you validate inputs?** [07]
`validation` blocks with `condition` + `error_message` (they can reference
other variables since 1.9). Also pre/postconditions and `check` blocks.

**🟡 17. How do you loop in Terraform?** [08, 09, 10]
`count`/`for_each` for multiple resources or modules; `for` expressions
to transform data; `dynamic` blocks for repeated nested blocks.

**🟡 18. What's a splat expression?** [08]
`list[*].attr` means "attr of every element". It works on lists (`count`),
not on maps (`for_each`); use `values(x)[*].attr` or a `for` expression there.

**🟡 19. What's a dynamic block, and when shouldn't you use one?** [10]
It generates nested blocks from a collection (blocks aren't values). Avoid
it when a standalone resource exists per item, or when literal blocks are clearer.

**🟡 20. `try` vs `can`?** [08]
`try` returns the first expression that doesn't error. `can` returns a
bool for "evaluates without error", and is used in validations.

**🟡 21. How do you conditionally create a resource? An argument? A block?** [09, 10]
Resource: `count = cond ? 1 : 0`. Argument: `arg = cond ? v : null`.
Block: `dynamic "b" { for_each = cond ? [1] : [] }`.

**🟡 22. What are `optional()` object attributes?** [10]
In type constraints (1.3+), `optional(type, default)` lets callers omit
attributes, with defaults filled in. It's great for module inputs.

**🔴 23. Can you write custom functions?** [08]
Not in HCL. Providers can ship functions (1.8+, `provider::ns::fn`).
Reuse comes from locals and modules.

**🔴 24. Why can't you build a resource reference from a string?** [18]
References are discovered by static analysis of expressions to build the
dependency graph before evaluation. There's no `eval`. A string is just a value.

---

## C. Meta-arguments and lifecycle

**🟡 25. count vs for_each?** [09]
`count` indexes by position, so removing a middle item shifts and
replaces later ones. `for_each` keys by map key or set element, so it's
stable. Use `count` for on/off or truly identical copies, and `for_each`
otherwise.

**🟡 26. Why must `count`/`for_each` be known at plan time?** [09, 17]
They define how many instances exist. Graph expansion happens during
planning, so unknown values ("known after apply") can't be expanded.

**🟡 27. How do you migrate from count to for_each without recreating anything?** [13]
`moved` blocks mapping `x[0]` → `x["key"]` for each instance (or `terraform state mv`).

**🟡 28. When is `depends_on` needed?** [09]
For hidden dependencies not expressed by references, e.g. an IAM policy
that must be attached before an instance uses it. Overuse makes plans pessimistic.

**🟡 29. Explain `create_before_destroy`, and its pitfall.** [09]
The replacement creates the new object first (no downtime). Unique names
clash (use `name_prefix`), and it propagates to dependencies to avoid cycles.

**🟡 30. `prevent_destroy`: what does it do and not do?** [09]
It fails any plan that would destroy the resource. It doesn't protect if
the block is deleted from code, or against deletion outside Terraform.

**🟡 31. Use cases for `ignore_changes`?** [09]
Attributes managed elsewhere: an ASG's `desired_capacity`, externally
added tags, AMIs rolled by another process.

**🔴 32. What's `replace_triggered_by`?** [09]
It forces replacement of a resource when another resource or attribute
changes, often via `terraform_data` for version-driven replacement.

**🔴 33. Preconditions vs postconditions vs check blocks?** [09, 20]
Pre/post are tied to a resource, data source, or output, and **fail** the
run. `check` blocks are standalone, can have scoped data sources, and only
**warn**.

**🔴 34. Why can't `lifecycle` arguments use variables?** [18, 23]
They're read while constructing the graph, before expression evaluation,
so they must be static.

**🟡 35. What's `terraform_data`?** [10]
A built-in no-op resource (replacing `null_resource`) that stores a value.
It's used to trigger replacements or host provisioners.

**🟡 36. Why are provisioners a last resort?** [10]
Their effects aren't in the plan or state, failures taint resources, and
they need connectivity and credentials. Prefer user data, images,
config management, or pipelines.

---

## D. State

**🟢 37. What's the state file, and why is it needed?** [11]
It maps config addresses to real IDs, remembers what to destroy, records
dependencies for destroy order, and caches attributes for performance.

**🟡 38. What's in the state?** [11]
Version, terraform_version, serial, lineage, outputs, resources with
instances, all their attributes (including secrets), and dependencies.

**🔴 39. `serial` vs `lineage`?** [11]
`serial` increments on each write (it prevents stale overwrites).
`lineage` is a UUID identifying a state's history (it prevents pushing
an unrelated state).

**🟡 40. Why use remote state? How on AWS?** [12]
For sharing, locking, durability, and security. On AWS: an S3 bucket
with versioning, SSE-KMS, a public access block, and tight IAM. Locking
with `use_lockfile = true` (1.10+), or a legacy DynamoDB table.

**🟡 41. What is state locking and what happens without it?** [12]
It stops concurrent writes. Without it, simultaneous applies both read
old state and the last write wins: lost resources, orphans, corruption.

**🟡 42. A lock is stuck. What do you do?** [12, 22]
Confirm the holder is really dead, `terraform force-unlock <ID>`, then
plan to assess partial changes.

**🟡 43. Why can't the backend use variables? How do you vary it per environment?** [12, 18]
The backend is initialised before evaluation. Use partial configuration:
`terraform init -backend-config=env.hcl`.

**🟡 44. `terraform_remote_state` vs data sources/SSM?** [12]
Remote state needs read access to the whole state (including secrets) and
couples the stacks. SSM parameters or tag lookups decouple them and keep
permissions minimal.

**🟢 45. What does `terraform state rm` do?** [11]
Terraform forgets the resource. It stays in AWS.

**🟡 46. How do you rename a resource without recreating it?** [13]
A `moved` block (preferred) or `terraform state mv`.

**🔴 47. How do you move a resource between two states?** [13]
A `removed` block with `destroy = false` in the source, then an `import`
block in the destination. The cloud is untouched.

**🔴 48. How do you recover from a corrupted or accidentally modified state?** [12]
Restore a previous version from S3 versioning (check serial and lineage),
or `state pull`/`push` carefully. Then plan to confirm, and re-import
anything missing.

---

## E. Import, drift, refactoring

**🟡 49. How do you import existing infrastructure?** [13]
Import blocks (optionally `-generate-config-out`). Iterate until
"N to import, 0 to change", apply, then remove the blocks. Or the
`terraform import` command (no preview).

**🟡 50. What's drift, and how do you handle it?** [13]
Divergence between reality and state or code. Detect it via plan (or
scheduled `plan -detailed-exitcode`). Revert (apply), accept (update the
code), or `-refresh-only` to reconcile state. Prevent it with read-only
console access.

**🟡 51. `-refresh-only`: what's it for?** [13]
It updates state to match reality without proposing config-driven changes.
It replaces the deprecated `terraform refresh` and is reviewable.

**🟡 52. `taint` vs `-replace`?** [13]
Both force recreation. `taint` edited state without a preview
(deprecated). `-replace=ADDR` shows it in the plan.

**🔴 53. Pitfalls when importing on AWS?** [13]
Provider defaults differing from what's live (causing changes on import);
split sub-resources (S3 versioning, encryption, and policy are separate);
import ID formats differ per resource; `for_each` imports need stable keys.

---

## F. Modules and structure

**🟢 54. What's a module? Root vs child?** [14]
Any directory of `.tf` files. The root is where you run Terraform
(owning backend and providers). Children are called via `module` blocks,
with inputs and outputs.

**🟡 55. Module sources and versioning?** [14]
Local paths, the registry (`version` constraint), Git (`?ref=tag`), S3,
or a private registry. Always pin remote modules.

**🔴 56. How should providers work with modules?** [14]
No provider blocks in child modules. Declare `required_providers` with
minimum versions, inherit defaults, pass aliases via `providers = {}`, and
use `configuration_aliases` for multi-provider modules.

**🟡 57. Good module design principles?** [14]
Focused purpose, a small validated interface, secure defaults, rich
outputs, no hard-coded environment, semantic versioning, docs and
examples, no single-resource wrappers, shallow nesting.

**🟡 58. How do you handle multiple environments?** [15]
Directory per environment (thin roots calling shared modules), separate
state keys and accounts, per-environment tfvars, and promotion
dev → staging → prod. Terragrunt or HCP at scale.

**🟡 59. Workspaces: what and when?** [15]
Multiple states for one config and backend (`terraform.workspace`).
Good for ephemeral copies, not for prod separation (implicit context,
shared credentials, invisible in review).

**🔴 60. How do you decide how to split state?** [16]
By blast radius, rate of change, and ownership: bootstrap / network /
data / platform / services per environment. One-way dependencies via
SSM or data sources. Keep stateful resources away from fast-changing code.

**🔴 61. Monorepo vs poly-repo for IaC?** [16]
Monorepo: discoverable, atomic changes, and needs path-aware CI and
CODEOWNERS. Poly-repo: isolation and versioned module releases, with
more coordination. The common hybrid is a versioned modules repo plus a live repo.

**🟡 62. What does Terragrunt add?** [15]
DRY backend and provider generation, dependency blocks passing outputs
between stacks, and `run --all` across stacks in order.

---

## G. Internals

**🔴 63. Describe Terraform's architecture.** [17]
Core (config, state, graph, orchestration) plus provider plugins as
separate processes over gRPC (go-plugin, protocol v5/v6). Providers
expose schemas and CRUD via RPCs, and call cloud APIs (AWS SDK for Go).

**🔴 64. What happens inside `terraform plan`?** [17]
Load config and state, get provider schemas, build the DAG from config,
state, and static references, walk it in parallel. Per resource: upgrade
state → `ReadResource` (refresh) → evaluate config → `PlanResourceChange`
(the planned state, unknowns, RequiresReplace) → choose the action.

**🔴 65. How is the dependency graph built?** [17, 18]
Transformers add nodes for config and state resources, variables,
locals, outputs, and providers. Edges come from statically analysed
expression references plus `depends_on` and provider relationships.
Cycles are detected, and a transitive reduction is applied.

**🔴 66. What's parallelism and how do you change it?** [17]
Concurrent graph walking bounded by a semaphore (default 10).
`-parallelism=N`. Lower it for API throttling.

**🔴 67. What are unknown values?** [17, 18]
Typed placeholders in cty for values determined at apply. They propagate
through expressions, and can carry refinements (1.6+) like not-null.
Not allowed where graph shape is decided.

**🔴 68. Who decides "forces replacement"?** [17]
The provider, in its `PlanResourceChange` response (`RequiresReplace`),
based on its schema.

**🔴 69. What does "Provider produced inconsistent result after apply" mean?** [17, 22]
The provider returned values that don't match what it promised at plan
time. It's usually a provider bug or API normalisation. Re-plan, upgrade,
and report it.

**🔴 70. What's in a saved plan file, and why does apply reject a stale one?** [17]
A config snapshot, prior state, planned changes (with secrets),
variables, and lock info. Apply checks the state serial and lineage
haven't changed since the plan.

**🔴 71. What is HCL, and how does Terraform use it?** [18]
A config toolkit: bodies of attributes and blocks, expressions,
templates, native and JSON syntaxes. It's decoded against schemas.
Terraform decodes the top level with its own schema, extracts
meta-arguments, and decodes resource bodies with provider schemas. Values
are represented by cty.

**🔴 72. Why do you need `init` before `validate`?** [17, 18]
Resource bodies are validated against provider schemas, which come from
the installed provider binaries.

**🔴 73. Why does changing one security group ingress rule show remove + add?** [18]
Inline rules are a set, and set elements are identified by their whole
value, so a changed rule is a different element.

**🔴 74. How does the lock file get chosen versions?** [05, 17]
`init` intersects all constraints from the root and modules, picks the
newest version satisfying them that's consistent with the lock file,
verifies hashes, and records per-platform checksums.

---

## H. Security, testing, CI/CD

**🟡 75. How do you handle secrets?** [19]
Avoid them in Terraform: `manage_master_user_password`, runtime fetch by
ARN, ephemeral resources and write-only arguments (1.10/1.11+). Otherwise
protect state (KMS, IAM, versioning). Never secrets in tfvars or Git.

**🟡 76. How should CI authenticate to AWS?** [19, 21]
OIDC federation to IAM roles, with trust conditions on repo, branch, or
environment. A read-only plan role for PRs, an apply role only for
protected environments.

**🟡 77. How do you test Terraform?** [20]
Static checks (fmt, validate, tflint, Checkov/Trivy), `terraform test`
with plan assertions, `expect_failures`, mocks, real-apply tests in a
sandbox (or Terratest), policy on the plan JSON, and check blocks.

**🟡 78. What is policy as code?** [20]
Machine-enforced rules on plans: OPA/Conftest (Rego), Sentinel
(HCP/TFE), Checkov custom policies. Required tags, regions, encryption, no public access.

**🟡 79. Describe your ideal Terraform pipeline.** [21]
PR: checks + plan (read-only OIDC role) + plan comment + policy + cost.
Merge: protected environment, approval, plan → apply saved plan.
Concurrency per state, promotion across environments, nightly drift detection.

**🔴 80. Merge-then-apply vs apply-then-merge?** [21]
Merge-first keeps `main` as the desired state, but applies can fail after
merge. Apply-first (Atlantis) keeps `main` equal to deployed and applies
the exact reviewed plan, but needs PR locking.

**🟡 81. What does `plan -detailed-exitcode` return?** [21]
0 no changes, 1 error, 2 changes present.

---

## I. Scenario questions (🔴 senior favourites)

**82. "Someone deleted a Terraform-managed security group in the console. What happens and what do you do?"**
The next plan's refresh finds it missing, so it shows "will be created".
Applying recreates it with a **new ID**. Check what referenced the old ID
(instances, rules). Terraform updates references it manages, but
out-of-band references break. Then find out why console deletes are
possible, and tighten IAM.

**83. "`terraform plan` wants to replace your production database. Why might that be, and what do you do?"**
Don't apply. Look for `# forces replacement`: a changed identifier,
engine, AZ, subnet group, storage type, or encryption setting, or a
module refactor without `moved` blocks. Fix the code (revert, `moved`, or
`ignore_changes`). If the change is really needed, plan a migration
(snapshot/restore, blue/green) outside a routine apply. `prevent_destroy`
and deletion protection should have blocked it anyway.

**84. "Two teams keep getting lock errors on the same state."**
The state is too big or shared across owners. Split by ownership and rate
of change, wire the pieces with SSM or data sources, and give each its own
pipeline and concurrency group.

**85. "Plans take 15 minutes."**
Too many resources in one state, API throttling, or data sources hitting
slow APIs. Split the state, tune `-parallelism`, reduce `depends_on`
pessimism, avoid huge `for_each` data lookups, and use the provider plugin cache in CI.

**86. "How would you roll out a provider major-version upgrade across 80 states?"**
Read the upgrade guide, upgrade in one low-risk state first
(`init -upgrade`, fix deprecations, plan to zero unintended changes),
update the shared modules' minimum versions, then roll out per
environment with pinned lock files. Automate PRs (Renovate/Dependabot)
and watch plans for unexpected diffs.

**87. "A resource was created by apply but Terraform errored before saving it to state."**
It now exists outside state, so the next apply hits "already exists".
Import it (import block), plan to zero changes, and continue.

**88. "Design Terraform for a new company with 50 engineers on AWS."**
AWS Organizations with accounts per environment (and per team for large
teams). A bootstrap layer with state buckets and OIDC roles. A versioned
modules repo with tests and policies, and live repos per env/layer or per
service. CI with plan/apply separation, drift detection, policy as code,
CODEOWNERS, and no console writes in prod. Remote state with native
locking. Secrets never in state where avoidable.

**89. "How do you let developers self-serve infrastructure safely?"**
Opinionated golden-path modules (secure defaults, few inputs), templates
or a service catalogue, policy as code in the pipeline, permission
boundaries on anything IAM, cost estimation on PRs, and platform-owned
review for exceptions.

**90. "What would make you choose CloudFormation or CDK over Terraform?"**
An AWS-only shop wanting AWS-managed state, native rollback, StackSets
across accounts, day-one support for new services via the Cloud Control
API, or developers who prefer general-purpose languages (CDK). Terraform
wins with multi-cloud and SaaS, a mature module ecosystem, and one workflow
for everything.

---

➡️ **Next:** [25 · Cheat sheet](25-cheat-sheet.md)
