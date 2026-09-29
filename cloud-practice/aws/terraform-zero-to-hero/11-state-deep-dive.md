# 11 · State deep dive

## 🎯 Goal

Understand exactly what the state file is, what's in it, why Terraform
can't live without it, and how to inspect and safely edit it. After this
lesson, "state" should feel boring rather than scary.

---

## 🧠 Mental model: the coat-check ticket

At a coat check you hand over your coat and get **ticket #42**. Later you
don't describe your coat ("the blue one, slightly worn…"). You hand over
ticket #42, and the attendant knows exactly which coat is yours.

The **state file is Terraform's pile of tickets**:

```
 your code says:              state says (the ticket):          AWS has:
 aws_instance.web      ───▶   aws_instance.web = i-0a1b2c3d ───▶ the instance i-0a1b2c3d
 aws_s3_bucket.assets  ───▶   aws_s3_bucket.assets = notes-…  ─▶ the bucket notes-…
```

Your code only has **names you invented** (`aws_instance.web`). AWS only
knows **real IDs** (`i-0a1b2c3d`). **The state is the mapping between them.**
Lose the ticket and the attendant can't tell which coat is yours. Lose
the state and Terraform can't tell which instances are its own.

---

## 🛠 Walkthrough

### Step 1: why can't Terraform just look at AWS?

Four reasons, and each is a common interview answer:

1. **Mapping.** Nothing in AWS says "this instance is `aws_instance.web`".
   Tags could be changed or missing, and many resource types don't support tags.
2. **Knowing what to delete.** If you delete a block from your code,
   Terraform must know that it once created something, to destroy it.
   Only the state remembers that.
3. **Dependencies for deletion.** When a resource is gone from the code,
   its references are gone too. The state records the dependencies so
   Terraform can still destroy things in the right order.
4. **Performance.** Scanning every resource in an AWS account (and in 100
   other providers) on every run would be very slow. The state tells
   Terraform exactly which objects to refresh.

### Step 2: what's inside

The state is JSON. A trimmed real example:

```json
{
  "version": 4,
  "terraform_version": "1.10.5",
  "serial": 17,
  "lineage": "3f2a9c1e-8b7d-4e2f-9a1b-5c6d7e8f9a0b",
  "outputs": {
    "web_public_ip": { "value": "13.235.10.20", "type": "string" }
  },
  "resources": [
    {
      "mode": "managed",
      "type": "aws_instance",
      "name": "web",
      "provider": "provider[\"registry.terraform.io/hashicorp/aws\"]",
      "instances": [
        {
          "schema_version": 1,
          "attributes": {
            "id": "i-0a1b2c3d4e5f67890",
            "ami": "ami-0abc123",
            "instance_type": "t3.micro",
            "public_ip": "13.235.10.20",
            "subnet_id": "subnet-0123abcd",
            "tags": { "Name": "notes-app-web" }
          },
          "sensitive_attributes": [],
          "dependencies": ["aws_subnet.public", "aws_security_group.web"]
        }
      ]
    }
  ]
}
```

Field by field:

| Field | What it's for |
|---|---|
| `version` | format of the state file itself (4 for all modern Terraform) |
| `terraform_version` | the Terraform that last wrote it. An older CLI refuses to use a newer state |
| **`serial`** | a counter that goes up on **every** write. Used to detect stale or overwritten state |
| **`lineage`** | a unique ID set when the state is first created. Stops you from accidentally pushing a *different* project's state over this one |
| `outputs` | the root outputs' values |
| `mode` | `managed` (resource) or `data` (data source) |
| `instances` | one per instance. With `count`/`for_each`, each has an `index_key` (`0` or `"ap-south-1a"`) |
| `attributes` | **every** attribute of the real object, as last seen, **including secrets in plain text** |
| `schema_version` | lets a newer provider upgrade old stored attributes |
| `dependencies` | recorded for correct destroy ordering |

### Step 3: refresh: keeping the state honest

Before planning, Terraform **refreshes**: for each resource in state, it
asks the provider to read the real object and updates its in-memory copy.

```
 state says instance_type = t3.micro
 AWS says   instance_type = t3.small   (someone changed it in the console)
 ───────────────────────────────────────────
 plan: ~ instance_type = "t3.small" -> "t3.micro"   (your code wins)
```

If a resource was **deleted outside Terraform**, the refresh finds nothing,
Terraform drops it from state, and the plan says it "will be created"
again. There are three ways to deal with drift, covered in lesson 13.

### Step 4: inspecting state safely

```bash
terraform state list                         # every address
terraform state list 'aws_subnet.private'    # filter
terraform state show 'aws_instance.web'      # all attributes of one resource
terraform show                               # whole state, human readable
terraform show -json | jq '.values.root_module.resources[].address'
```

**Never edit the JSON by hand.** Use these commands. They keep serial,
lineage, and format consistent.

### Step 5: the state-changing commands

| Command | What it does | Touches AWS? |
|---|---|---|
| `terraform state mv A B` | rename an address (e.g. after refactoring) | no |
| `terraform state rm A` | forget a resource (it stays in AWS) | no |
| `terraform import A ID` | adopt an existing object into address A | no (reads only) |
| `terraform state pull > s.json` | download the current state | no |
| `terraform state push s.json` | upload a state (dangerous, a last resort) | no |
| `terraform state replace-provider` | change the provider source (e.g. registry move) | no |
| `terraform force-unlock ID` | remove a stuck lock (lesson 12) | no |

Notice **none of them change AWS**. They only change Terraform's memory.
Modern Terraform replaces the most common ones with **code** (`moved`,
`import`, and `removed` blocks, lesson 13), which is reviewable and shows
in the plan. Prefer those.

### Step 6: examples

**Rename a resource without recreating it:**

```hcl
# before: resource "aws_instance" "web" { ... }
# after:  resource "aws_instance" "frontend" { ... }
```

Without help, Terraform sees "`web` removed, `frontend` added", so it
**destroys and recreates** the instance. Tell it that it's the same object:

```bash
terraform state mv aws_instance.web aws_instance.frontend
```

or, better, in code:

```hcl
moved {
  from = aws_instance.web
  to   = aws_instance.frontend
}
```

The plan now shows `# aws_instance.web has moved to aws_instance.frontend`
with **0 changes**.

**Quote your addresses** in the shell: `'aws_subnet.private["ap-south-1a"]'`.
The brackets and quotes otherwise get mangled.

### Step 7: sensitive data in state

The state stores **every attribute**, including:

- database passwords you passed in;
- generated passwords (`random_password.result`);
- private keys from the `tls` provider;
- secrets read via data sources.

`sensitive = true` only hides values on screen. So:

> **Treat the state file as a secret.** Store it encrypted, restrict who
> can read it, and never commit it. Lesson 12 shows how on AWS, and
> lesson 19 shows how to keep secrets out of it where possible.

### Step 8: state and `terraform_version`

When a newer Terraform writes the state, older CLIs refuse to read it.
In a team, **pin `required_version`** and upgrade together (CI first), or
someone's newer laptop CLI will "upgrade" the shared state for everyone.

---

## ⚠️ Common mistakes

- **Committing `terraform.tfstate` to Git.** You leak secrets, and two people applying from different copies overwrite each other's changes. Use a remote backend.
- **Editing state JSON by hand.** Use `state mv`/`rm` or `moved`/`removed` blocks.
- **Deleting state "to start fresh".** Terraform forgets *everything*, so the next apply tries to create duplicates, which fail or double your bill. Everything must then be imported back.
- **`state rm` expecting it to delete the resource.** It only forgets it.
- **Running a newer Terraform locally** against shared state and breaking older CI runners.

---

## 🎤 Interview corner

**Q: Why does Terraform need state?**

> It maps resource addresses in configuration to real object IDs. It
> remembers what Terraform created so it can destroy things removed from
> the code. It records dependencies for correct destroy ordering. And it
> caches attributes so Terraform only has to refresh known objects instead
> of scanning the whole account. Without state, Terraform couldn't tell
> which real objects it owns.

**Q: What are `serial` and `lineage`?**

> `serial` increments on every state write. Backends use it to avoid
> writing an older state over a newer one. `lineage` is a UUID assigned
> when a state is first created. It identifies that particular state's
> history and prevents pushing a state from a different lineage over it.

**Q: You renamed a resource and the plan shows destroy/create. What do you do?**

> Add a `moved` block from the old address to the new one (or use
> `terraform state mv`). The plan then shows a move with no infrastructure
> change. Moved blocks are better because they're versioned in code and
> apply automatically in every environment and workspace.

**Q: Is the state file sensitive?**

> Yes. It stores all resource attributes in plain text, including
> passwords and keys. It should live in an encrypted remote backend with
> tight IAM, versioning, and no human write access in normal operation.

---

## ✅ Check yourself

1. Give two reasons Terraform can't work without state.
2. You `terraform state rm aws_s3_bucket.assets`, then `apply`. What happens?
3. What's the difference between `serial` and `lineage`?
4. A teammate deleted an EC2 instance from the console. What does the next plan show?

<details><summary>Answers</summary>

1. Any two of: mapping code addresses to real IDs; knowing what to destroy when code is removed; destroy ordering via recorded dependencies; performance (refresh only known objects).
2. Terraform no longer knows the bucket, so it tries to **create** it again, which fails with "BucketAlreadyOwnedByYou" (or it creates a duplicate for resource types without unique names).
3. `serial` counts writes within one state's history. `lineage` identifies which history it is.
4. The refresh finds it missing, so the plan shows it "will be created".

</details>

➡️ **Next:** [12 · Remote state and locking on AWS](12-remote-state-and-locking.md)
