# Lesson 05: stop managing a resource WITHOUT deleting it

⏱ about 10 minutes · 💰 free · 📋 do lessons 01–04 first

Import moves a resource **into** Terraform. Sometimes you need the reverse:
another team takes it over, or it moves to a different Terraform project.

**By the end you will be able to:**
1. See why "just delete the code" is **dangerous**.
2. Use a `removed` block to hand a resource back safely.
3. Complete the full lifecycle: manual → import → manage → release.

`main.tf` creates two resource groups: **keep** (stays in Terraform) and
**handover** (we'll let go of it).

---

## Step 0: setup and create

This time Terraform creates both resources itself, so we can focus on the release:

```bash
cd import-basics/05-stop-managing-without-deleting
echo "subscription_id = \"$(az account show --query id -o tsv)\"" > terraform.tfvars
terraform init
terraform apply        # "yes" → 2 added
```

---

## Step 1: the trap: just deleting the code 🔥

Your instinct says: "I don't want Terraform to manage `handover`, so I'll
delete its block." Delete the whole `resource "azurerm_resource_group" "handover" { ... }`
block from `main.tf` and plan:

```bash
terraform plan
```

```
  # azurerm_resource_group.handover will be destroyed
  # (because azurerm_resource_group.handover is not in configuration)
Plan: 0 to add, 0 to change, 1 to destroy.
```

**Terraform would DELETE it.** To Terraform, "in the state but missing from
the code" means "the user wants this gone". **Do not apply.**

## Step 2: the right way: a `removed` block

In the place where the `handover` block was, write:

```hcl
removed {
  from = azurerm_resource_group.handover

  lifecycle {
    destroy = false   # forget it, don't delete it
  }
}
```

```bash
terraform plan
```

```
 # azurerm_resource_group.handover will no longer be managed by Terraform, but will not be destroyed
 # (destroy = false is set in the configuration)
Plan: 0 to add, 0 to change, 0 to destroy.

Warning: Some objects will no longer be managed by Terraform
```

`0 to destroy`. That's what we want.

```bash
terraform apply
terraform state list                       # only azurerm_resource_group.keep
az group exists -n rg-lesson05-handover    # → true. Still alive in Azure ✅
```

After it's applied you can delete the `removed` block. Like an `import`
block, it's a one-time instruction.

### `removed` block vs `terraform state rm` (lesson 02)

They do the same thing: forget without deleting. The block is better for
the same reasons the import block beat the command: it shows up in `plan`
first, it's reviewable in a pull request, and it runs in your normal
workflow. (Needs Terraform 1.7+.)

---

## Step 3: prove it's really let go

```bash
terraform destroy
```

```
azurerm_resource_group.keep: Destroying...
Destroy complete! Resources: 1 destroyed.
```

Only **keep** was destroyed. Terraform doesn't touch `handover` any more.
It's back to being a "manual" resource, exactly like at the start of lesson 01:

```bash
az group exists -n rg-lesson05-keep        # → false
az group exists -n rg-lesson05-handover    # → true
```

## Step 4: clean up (by hand, since Terraform no longer owns it)

```bash
az group delete -n rg-lesson05-handover --yes
rm -f terraform.tfstate*
git checkout main.tf
```

---

## 🧠 The complete lifecycle

```
                    lesson 01–04                                   lesson 05
 ┌──────────┐   import block   ┌─────────────────────────┐   removed block   ┌──────────┐
 │  MANUAL  │ ───────────────▶ │  MANAGED BY TERRAFORM   │ ────────────────▶ │  MANUAL  │
 │ (az/UI)  │   (0 to change!) │ edit code → plan → apply│  (destroy=false)  │ (again)  │
 └──────────┘                  │ plan catches drift      │                   └──────────┘
                               └───────────┬─────────────┘
                                           │ terraform destroy
                                           ▼
                                       DELETED
```

| You want to… | Use | Azure changes? |
|---|---|---|
| start managing something that exists | `import { }` block | no |
| change it | edit code → `plan` → `apply` | yes, as the plan shows |
| stop managing it, keep it | `removed { lifecycle { destroy = false } }` | no |
| delete it | remove the code (or `terraform destroy`) | **yes, deleted** |

🎓 **You've finished the basics.** For all of it combined (8 resources, a
real app writing data, automated tests), see the advanced lab
[`../../import-existing/`](../../import-existing/).
