# Lesson 01: your first import (one resource group)

⏱ about 15 minutes · 💰 free (resource groups cost nothing)

**By the end you will be able to:**
1. Explain why Terraform can't just "see" a resource you created by hand.
2. Adopt (import) that resource into Terraform.
3. Change it with Terraform, and watch Terraform catch a hand-made change.

There are only two files here:

| File | What it is |
|---|---|
| `main.tf` | describes the resource group **exactly as it already exists** in Azure |
| `import.tf` | one `import` block that says "don't create this, adopt it" |

---

## Step 0: get set up (once)

```bash
cd import-basics/01-first-import-resource-group
az login                                   # skip if you're already logged in
echo "subscription_id = \"$(az account show --query id -o tsv)\"" > terraform.tfvars
terraform init
```

`terraform.tfvars` just stores your subscription ID so you don't have to type it.

---

## Step 1: create the resource group BY HAND

Pretend a colleague did this in the portal last year:

```bash
az group create -n rg-lesson01 -l centralindia --tags owner=me
```

✅ **Check:** `az group show -n rg-lesson01 -o table` shows it.

Right now:

```
 Azure:      rg-lesson01 exists      ✔
 Your code:  describes rg-lesson01   ✔
 State:      empty                   ✘   ← Terraform has never heard of it
```

---

## Step 2: see why import is needed (on purpose, the wrong way)

Hide the import block for a moment and ask Terraform what it would do:

```bash
mv import.tf import.tf.off
terraform plan
```

You'll see:

```
  # azurerm_resource_group.lesson will be created
Plan: 1 to add, 0 to change, 0 to destroy.
```

**"Will be created"?** It already exists! Terraform doesn't scan Azure for
things. It only knows about resources recorded in its **state file**, and
the state is empty. So it thinks the resource group is new.

If you ran `terraform apply` now, Azure would refuse:

```
Error: a resource with the ID ".../resourceGroups/rg-lesson01" already exists -
to be managed via Terraform this resource needs to be imported into the State.
```

That error is Terraform telling you, in its own words, to import. Put the block back:

```bash
mv import.tf.off import.tf
```

---

## Step 3: preview the import

```bash
terraform plan
```

```
  # azurerm_resource_group.lesson will be imported
    resource "azurerm_resource_group" "lesson" {
        location = "centralindia"
        name     = "rg-lesson01"
        tags     = { "owner" = "me" }
    }
Plan: 1 to import, 0 to add, 0 to change, 0 to destroy.
```

### 🎯 How to read an import plan

| Number | Meaning | What you want |
|---|---|---|
| **to import** | resources Terraform will adopt | the count you expect |
| **to add** | resources it will *create* | **0** |
| **to change** | your code differs from Azure, so apply would **modify** it | **0** |
| **to destroy** | it would **delete** something | **0** |

`0 to change` proves that `main.tf` matches Azure exactly. The import
changes nothing in Azure. It only writes to the state file.

---

## Step 4: import it

```bash
terraform apply        # type "yes"
```

```
azurerm_resource_group.lesson: Importing...
azurerm_resource_group.lesson: Import complete
Apply complete! Resources: 1 imported, 0 added, 0 changed, 0 destroyed.
```

Now look at what Terraform remembers:

```bash
terraform state list                                  # → azurerm_resource_group.lesson
terraform state show azurerm_resource_group.lesson    # every attribute it recorded
```

```
 Azure:      rg-lesson01 exists      ✔
 Your code:  describes rg-lesson01   ✔
 State:      knows rg-lesson01       ✔   ← all three agree
```

---

## Step 5: remove the import block

The import block is a one-time instruction. Now that the resource is in the
state, it's finished:

```bash
rm import.tf
terraform plan
```

```
No changes. Your infrastructure matches the configuration.
```

**"No changes" is the sentence you want to see.** It means code, state and
Azure all agree.

---

## Step 6: change the resource with Terraform

From now on, **you change the code, not the portal.** Open `main.tf` and add a tag:

```hcl
  tags = {
    owner = "me"
    env   = "learning"     # ← add this line
  }
```

```bash
terraform plan
```

```
  ~ resource "azurerm_resource_group" "lesson" {
      ~ tags = {
          + "env" = "learning"
Plan: 0 to add, 1 to change, 0 to destroy.
```

The `~` symbol means **update in place**: the same resource group, just edited.

```bash
terraform apply                                   # "yes"
az group show -n rg-lesson01 --query tags         # → env + owner
```

---

## Step 7: drift (someone changes it by hand again)

Play the colleague who "just quickly fixes something in the portal":

```bash
az group update -n rg-lesson01 --set tags.owner=someone-else
terraform plan
```

```
      ~ tags = {
          ~ "owner" = "someone-else" -> "me"
Plan: 0 to add, 1 to change, 0 to destroy.
```

Terraform noticed. Every `plan` first **refreshes**: it reads the real
values from Azure and compares them with your code. This difference is called
**drift**. `terraform apply` puts it back to `me`.

> Real-life rule: if the hand-made change was *correct*, copy it into
> `main.tf`. Don't keep overwriting it.

---

## ⚠️ Edge cases (try them, but DON'T apply)

Do these **before Step 4** (while the import block is still there) to see
what a mismatch looks like during an import. Or do them after Step 5 to see
them as normal changes.

### Edge case A: your code has the wrong tag

Change `owner = "me"` to `owner = "terraform"` and run `terraform plan`:

```
Plan: 1 to import, 0 to add, 1 to change, 0 to destroy.
```

Importing still works, but apply would **also edit** the tag. That's
harmless here, but on a real resource it could be a setting you didn't mean
to touch. **Fix the code until you see `0 to change`.**

### Edge case B: your code has the wrong location 🔥

Change `location = "centralindia"` to `"eastus"` and run `terraform plan`:

```
  # azurerm_resource_group.lesson must be replaced
      ~ location = "centralindia" -> "eastus" # forces replacement
Plan: 1 to import, 1 to add, 0 to change, 1 to destroy.
```

**`must be replaced` = delete the old one, create a new one.** Some settings
(like location or name) can't be changed in place. For a resource group,
deleting it deletes **everything inside it**. Whenever you see
`forces replacement` or `1 to destroy` in an import plan, stop and fix your code.

Put `main.tf` back to `centralindia` and `owner = "me"` when you're done.

---

## Step 8: clean up

Terraform owns it now, so Terraform can delete it:

```bash
terraform destroy      # "yes"
az group exists -n rg-lesson01     # → false
```

To repeat the lesson from scratch, delete the local state and restore the import block:

```bash
rm -f terraform.tfstate terraform.tfstate.backup
git checkout import.tf main.tf    # or recreate import.tf from this README
```

---

## 🧠 What you learned: the import lifecycle

```
 1. CREATED BY HAND      az / portal              Azure ✔  code ✘  state ✘
 2. DESCRIBED IN CODE    write main.tf            Azure ✔  code ✔  state ✘
 3. IMPORTED             import block + apply     Azure ✔  code ✔  state ✔
 4. MANAGED              edit code → plan → apply (and plan catches drift)
 5. DESTROYED            terraform destroy        (or hand it back: lesson 05)
```

**Three words to remember:**
- **Code** (`.tf`) = what you *want*.
- **State** (`terraform.tfstate`) = what Terraform *remembers owning*.
- **Import** = add an existing resource to the state, without changing Azure.

➡️ **Next:** [Lesson 02](../02-cli-import-and-forget/): the other way to import, and how to make Terraform *forget* a resource.
