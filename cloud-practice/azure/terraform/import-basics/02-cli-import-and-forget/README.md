# Lesson 02: the `terraform import` command, and making Terraform forget

⏱ about 15 minutes · 💰 free · 📋 do [lesson 01](../01-first-import-resource-group/) first

**By the end you will be able to:**
1. Import with the **command** `terraform import` (the older way you'll see in blogs and at work).
2. Recognise the three common import errors and know what each means.
3. Use `terraform state rm` to make Terraform **forget** a resource without deleting it.

This folder has only `main.tf`, with **no `import.tf`**. The command replaces the block.

---

## Step 0: setup

```bash
cd import-basics/02-cli-import-and-forget
echo "subscription_id = \"$(az account show --query id -o tsv)\"" > terraform.tfvars
terraform init
SUB=$(az account show --query id -o tsv)     # used in the commands below
```

## Step 1: create by hand

```bash
az group create -n rg-lesson02 -l centralindia --tags owner=me
```

---

## Step 2: three mistakes first (they're harmless, and you'll meet them for real one day)

The command's shape is always:

```
terraform import  <address in your code>          <Azure resource ID>
terraform import  azurerm_resource_group.lesson   /subscriptions/.../resourceGroups/rg-lesson02
```

### ❌ Mistake 1: a typo in the ID

```bash
terraform import azurerm_resource_group.lesson "/subscriptions/$SUB/resourcegroups/rg-lesson02"
```

```
Error: parsing segment "resourceGroups": parsing the ResourceGroup ID:
the segment at position 2 didn't match
```

The ID is **case-sensitive** in its structure: `resourceGroups`, not
`resourcegroups`. Tip: never type IDs by hand. Copy them:
`az group show -n rg-lesson02 --query id -o tsv`.

### ❌ Mistake 2: the resource doesn't exist

```bash
terraform import azurerm_resource_group.lesson "/subscriptions/$SUB/resourceGroups/rg-does-not-exist"
```

```
Error: Cannot import non-existent remote object
```

You can only import what really exists in Azure. Check the name and the subscription.

### ✅ Now do it right

```bash
terraform import azurerm_resource_group.lesson "/subscriptions/$SUB/resourceGroups/rg-lesson02"
```

```
Import successful!
The resources that were imported are shown above. These resources are now in
your Terraform state and will henceforth be managed by Terraform.
```

```bash
terraform plan        # → No changes. Your infrastructure matches the configuration.
```

### ❌ Mistake 3: importing twice

Run the same import command again:

```
Error: Resource already managed by Terraform
```

One address in your code can only point to one real resource. It's already
in the state, so Terraform refuses.

---

## Step 3: make Terraform forget (`state rm`)

```bash
terraform state rm azurerm_resource_group.lesson
```

```
Removed azurerm_resource_group.lesson
Successfully removed 1 resource instance(s).
```

**Was the resource group deleted?**

```bash
az group exists -n rg-lesson02     # → true. It's still there!
terraform plan                     # → "will be created", Plan: 1 to add
```

`state rm` only erases Terraform's **memory**. Azure is untouched. That's
why the plan wants to "create" it again. It's the same situation as lesson 01,
Step 2.

```
            import  ─────────────▶
   STATE                             (Azure never changes during either)
            ◀─────────────  state rm
```

**When is this useful?** Moving a resource to a different Terraform project,
or handing it back to manual management. Lesson 05 shows the cleaner, modern
way to do that.

---

## Step 4: the big difference between the command and the block ⚠️

Change `owner = "me"` to `owner = "terraform"` in `main.tf` (now the code is
**wrong**), then import with the command:

```bash
terraform import azurerm_resource_group.lesson "/subscriptions/$SUB/resourceGroups/rg-lesson02"
# → Import successful!
```

**It succeeded, even though your code doesn't match Azure.** The command
never compares your code with reality. You only find out afterwards:

```bash
terraform plan
#   ~ "owner" = "me" -> "terraform"
# Plan: 0 to add, 1 to change, 0 to destroy.
```

In lesson 01 the `import` **block** showed that mismatch **before** anything
was written (`1 to import, 1 to change`). Put `owner = "me"` back and
`terraform plan` says **No changes** again.

### Block vs command

| | `import { }` block (lesson 01) | `terraform import` command (this lesson) |
|---|---|---|
| Preview before it happens | ✅ yes, it's part of `plan` | ❌ no, it writes to state right away |
| Catches a code mismatch first | ✅ | ❌ only on the next `plan` |
| Import many resources at once | ✅ one apply | one command per resource |
| Reviewable in a pull request | ✅ it's code | ❌ it's a command someone ran |
| Available since | Terraform 1.5 (2023) | forever |

**Use the block.** Know the command because you'll see it in older docs,
and it's handy for a quick one-off.

---

## Step 5: clean up

```bash
terraform destroy                   # "yes"
az group exists -n rg-lesson02      # → false
rm -f terraform.tfstate terraform.tfstate.backup
```

---

## 🧠 What you learned

- `terraform import <address> <id>` = import immediately, **no preview**.
- The three errors: **bad ID format**, **doesn't exist**, **already managed**.
- `terraform state rm <address>` = Terraform forgets, and **Azure keeps the resource**.
- State is only Terraform's memory. Import and `state rm` edit that memory and never touch Azure.

➡️ **Next:** [Lesson 03](../03-storage-account-hidden-defaults/): a real service with a trap, where your code looks right but isn't.
