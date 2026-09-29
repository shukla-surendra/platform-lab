# 03 · The core workflow in depth

## 🎯 Goal

Know exactly what each command does under the hood, read any plan
fluently, and use the everyday supporting commands (`fmt`, `validate`,
`output`, `show`, `console`).

---

## 🧠 Mental model: three sources of truth

Every Terraform run juggles three things. Keep this picture in your head,
because almost every Terraform surprise is one of these three disagreeing.

```
  ┌────────────────┐     ┌────────────────────┐     ┌────────────────┐
  │   CONFIG       │     │      STATE         │     │  REAL WORLD    │
  │  (*.tf files)  │     │ (terraform.tfstate)│     │  (AWS APIs)    │
  │                │     │                    │     │                │
  │ what you WANT  │     │ what Terraform     │     │ what actually  │
  │                │     │ REMEMBERS managing │     │ EXISTS now     │
  └────────────────┘     └────────────────────┘     └────────────────┘
```

- **Config vs state** decides **create / delete**: in config but not
  state means "create it", and in state but not config means "destroy it".
- **State vs real world** decides **drift**: Terraform refreshes the
  state from AWS, and notices if someone changed things by hand.
- **Config vs (refreshed) state** decides **update**: a different value means "change it".

---

## 🛠 Walkthrough

### Step 1: what `plan` really does, step by step

```
terraform plan
  1. Load all *.tf files in the current directory (not subfolders!)
  2. Read the state file
  3. REFRESH: for every resource in state, ask AWS "what does it look like now?"
  4. For every resource in config: compare desired vs refreshed values
  5. Build a list of actions, ordered by dependencies
  6. Print it. Change nothing.
```

Point 1 matters: **every `.tf` file in the folder is merged into one
configuration**. Splitting code into `main.tf`, `variables.tf`, and
`outputs.tf` is just for humans. Terraform doesn't care about file names,
and it ignores subfolders (those are for modules, lesson 14).

### Step 2: reading a plan like a pro

| Symbol | Words in the plan | Meaning | Danger |
|---|---|---|---|
| `+` | will be created | new resource | low |
| `~` | will be updated in-place | same resource, some attributes change | usually low |
| `-/+` | must be replaced | destroy, then create a new one | **high**: new ID, data lost |
| `+/-` | must be replaced | create the new one first, then destroy the old (`create_before_destroy`) | medium |
| `-` | will be destroyed | deleted | **high** |
| `<=` | will be read during apply | a data source that must wait for something | none |
| `# forces replacement` | next to an attribute | *this* attribute is why it's being replaced | read it! |

Two more lines you'll see:

- `(known after apply)`: a value decided by AWS at creation time.
- `# (5 unchanged attributes hidden)`: Terraform hides noise. It's not an error.

**How a professional reads a plan, in this order:**

1. The **summary line**. Are the numbers what I expect?
2. **Search for `destroy` and `replaced`.** Is each one intended?
3. Then read the `~` details.

### Step 3: saved plans, so what you review is what runs

```bash
terraform plan -out=tfplan      # save the exact plan to a file
terraform show tfplan           # read it again later (human-readable)
terraform apply tfplan          # apply EXACTLY this plan; no questions asked
```

Why it matters: between your `plan` and a later `apply`, someone might
change AWS or the code. A plain `apply` recomputes the plan. Applying a
**saved** plan executes exactly what was reviewed, and fails if the state
changed in the meantime. CI pipelines always work this way (lesson 21).

### Step 4: what `apply` does

```
terraform apply
  1. Do everything plan does (unless given a saved plan)
  2. Ask for "yes" (skip with -auto-approve, only in automation)
  3. Walk the dependency graph: independent resources in PARALLEL (10 at a time by default)
  4. For each resource: call AWS (create / update / delete)
  5. After EACH resource finishes, write the result to state
  6. Print outputs
```

Point 5 means that if apply fails halfway, the state still records what
*did* get created. Terraform doesn't roll back. You fix the problem and run
`apply` again, and it continues from where reality is.

### Step 5: the supporting commands you'll use every day

```bash
terraform fmt                # rewrite files in the canonical style (indentation, alignment)
terraform fmt -check -recursive   # CI: fail if anything isn't formatted

terraform validate           # check syntax + types, WITHOUT calling AWS
                             # (needs init first, because it uses provider schemas)

terraform output             # print all outputs from the state
terraform output -raw bucket_name   # just the value, for scripts
terraform output -json       # machine-readable

terraform show               # the current state, human-readable
terraform state list         # every resource address Terraform manages

terraform console            # an interactive REPL to try expressions (lesson 08)

terraform providers          # which providers the code + state need
terraform graph | dot -Tpng > graph.png   # draw the dependency graph
```

### Step 6: useful flags

| Flag | Used with | What it does |
|---|---|---|
| `-out=FILE` | plan | save the plan |
| `-auto-approve` | apply, destroy | skip the "yes" prompt (CI only) |
| `-var 'k=v'` / `-var-file=f.tfvars` | plan, apply | set variables (lesson 07) |
| `-target=ADDRESS` | plan, apply | only this resource and its dependencies. **Emergency use only** |
| `-replace=ADDRESS` | plan, apply | force recreation of one resource (lesson 13) |
| `-refresh-only` | plan, apply | only update state from reality, change nothing (lesson 13) |
| `-refresh=false` | plan | skip the refresh (faster, less accurate) |
| `-parallelism=N` | plan, apply | how many operations run at once (default 10) |
| `-lock-timeout=5m` | most | wait for a state lock instead of failing (lesson 12) |
| `-destroy` | plan | preview a destroy |

### Step 7: the files in a working directory

```
notes-app/
├── *.tf                    your code (commit)
├── .terraform.lock.hcl     provider versions + checksums (commit)
├── .terraform/             providers, modules, backend config cache (ignore)
├── terraform.tfstate       state, if using a local backend (NEVER commit; use remote state)
├── terraform.tfstate.backup  the previous state (ignore)
├── terraform.tfvars        variable values (commit only if no secrets)
└── tfplan                  a saved plan (ignore; it can contain secrets)
```

---

## ⚠️ Common mistakes

- **Running Terraform from the wrong folder.** It only reads `.tf` files in the *current* directory. An empty folder happily plans "No changes".
- **Treating `-target` as normal.** It builds a partial graph and can leave things inconsistent. Use it to recover from trouble, not as a habit.
- **Expecting rollback.** A failed apply leaves partial changes. Fix and re-apply.
- **`-auto-approve` on your laptop.** One typo away from deleting production.
- **Forgetting that `validate` doesn't talk to AWS.** Valid code can still fail on apply (wrong AMI, missing permission, name taken).

---

## 🎤 Interview corner

**Q: Walk me through what happens when you run `terraform apply`.**

> Terraform loads and merges all `.tf` files in the directory, reads the
> state, and refreshes each managed resource from the provider. It diffs
> desired versus current values and builds a dependency graph of actions.
> After approval, it walks the graph, running independent operations in
> parallel (10 by default), calling the provider for each create, update,
> or delete, and persisting state after each resource. There's no
> automatic rollback: on failure, completed changes stay recorded in state
> and you fix forward.

**Q: Why use `plan -out`?**

> To guarantee the apply executes exactly the reviewed plan. Otherwise
> `apply` recomputes, and the result could differ if code or
> infrastructure changed. Terraform also refuses to apply a saved plan if
> the state changed since it was created.

**Q: When would you use `-target`?**

> Rarely: to recover from a broken state or to apply a critical fix in
> isolation. It creates a partial plan and Terraform itself warns that it
> isn't for routine use. Routine use points to a structure problem, like
> too much in one state.

---

## ✅ Check yourself

1. You have `network.tf` and `app.tf` in one folder. How many configurations does Terraform see?
2. Apply fails on the 7th of 10 resources. What does the state contain, and what do you do?
3. Which symbol in a plan should make you stop and think hardest?
4. Does `terraform validate` catch "this AMI doesn't exist"?

<details><summary>Answers</summary>

1. One. All `.tf` files in a directory are merged.
2. The 6 (or so) resources that were created successfully. Fix the cause and run `apply` again. Terraform continues with what's left.
3. `-/+` (replacement) and `-` (destroy), plus `# forces replacement`.
4. No. `validate` checks syntax and types locally. It never calls AWS.

</details>

➡️ **Next:** [04 · HCL syntax and types](04-hcl-syntax-and-types.md)
