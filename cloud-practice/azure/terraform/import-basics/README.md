# Terraform import: from zero, one small step at a time

You (or a colleague) created something in Azure **by hand**. Now you want
**Terraform** to manage it without breaking or recreating it. This course
teaches that in 5 short lessons. Each lesson is its own folder and adds
**one** new idea.

| # | Lesson | New idea | Azure service | Time |
|---|---|---|---|---|
| 01 | [First import](01-first-import-resource-group/) | code vs state vs Azure, the `import` block, drift | Resource group | 15 min |
| 02 | [CLI import & forget](02-cli-import-and-forget/) | `terraform import` command, common errors, `state rm` | Resource group | 15 min |
| 03 | [Hidden defaults](03-storage-account-hidden-defaults/) | the #1 import trap, protecting data, `prevent_destroy` | Storage account | 25 min |
| 04 | [Generate the code](04-let-terraform-write-the-code/) | `-generate-config-out`, tidying, inline lists | Network security group | 20 min |
| 05 | [Let go](05-stop-managing-without-deleting/) | `removed` block: the reverse of import | Resource group | 10 min |

Every lesson follows the same rhythm, so you always know where you are:

```
 create by hand (az)  →  import  →  modify with Terraform  →  edge cases  →  clean up
```

Every output shown in the lessons was copied from a real run, so your
screen should look the same.

---

## Before you start

```bash
az login                      # Azure CLI, logged in
terraform version             # 1.7 or newer
```

Each lesson creates a free or near-free resource and deletes it at the end.

---

## The only 3 ideas you need

```
     YOUR CODE (.tf)              STATE (terraform.tfstate)           AZURE
   "what I want"              "what Terraform remembers        "what really exists"
                                   it owns"
```

1. **Terraform only manages what's in its state.** A resource created by
   hand isn't in the state, so to Terraform it doesn't exist, even though
   it's right there in Azure.
2. **Import = write an existing resource into the state.** It doesn't
   create, change, or delete anything in Azure.
3. **`terraform plan` compares all three** and tells you what `apply` would
   do to make Azure match your code.

---

## How to read a plan (keep this open)

| Symbol / words | Meaning | During an import you want… |
|---|---|---|
| `will be imported` | adopt an existing resource | ✅ |
| `+` / `will be created` | make a new resource | usually ❌ (did you forget an import?) |
| `~` / `updated in-place` | edit the existing resource | ❌: fix your code until it's gone |
| `-/+` / `must be replaced` / `forces replacement` | **delete then recreate** | 🔥 never: data loss |
| `-` / `will be destroyed` | delete | 🔥 never |
| `No changes.` | code = state = Azure | ✅ the goal after every step |

**The golden rule of importing:** keep editing your code until the plan says
`N to import, 0 to add, 0 to change, 0 to destroy`. Only then apply.

---

## Cheat sheet

```bash
# find a resource's ID (never type IDs by hand)
az group show -n <rg> --query id -o tsv
az resource show -g <rg> -n <name> --resource-type <type> --query id -o tsv

# import (preferred: an import block in a .tf file, then)
terraform plan                                      # preview
terraform plan -generate-config-out=generated.tf    # let Terraform write the resource code
terraform apply

# import (quick one-off, no preview)
terraform import <address> <azure-id>

# look at what Terraform remembers
terraform state list
terraform state show <address>

# forget without deleting
terraform state rm <address>        # or a removed { } block (lesson 05)
```

When you're done with all 5, the advanced lab
[`../import-existing/`](../import-existing/) puts everything together:
8 resources, an app writing real data, and automated tests.
