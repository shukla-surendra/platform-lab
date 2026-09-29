# Lesson 03: a real service, and the hidden-defaults trap

⏱ about 25 minutes · 💰 fractions of a cent (a storage account for a few minutes) · 📋 do lessons 01–02 first

**By the end you will be able to:**
1. Import **two related resources** at once (a storage account inside a resource group).
2. Spot the #1 import trap, **hidden defaults**, and fix it the right way.
3. Prove a resource was **updated, not recreated**, and protect it with `prevent_destroy`.

This time there's real **data** in the resource, so mistakes matter.

---

## Step 0: setup

A storage account name must be unique across **all of Azure**, so we add a random suffix:

```bash
cd import-basics/03-storage-account-hidden-defaults
SA="stlesson03$(openssl rand -hex 3)"; echo $SA          # e.g. stlesson03ccb907
printf 'subscription_id      = "%s"\nstorage_account_name = "%s"\n' \
  "$(az account show --query id -o tsv)" "$SA" > terraform.tfvars
terraform init
```

> Opening a new terminal later? Get `$SA` back with
> `SA=$(sed -n 's/storage_account_name *= *"\(.*\)"/\1/p' terraform.tfvars)`

## Step 1: create by hand, then put data in it

```bash
az group create -n rg-lesson03 -l centralindia
az storage account create -n $SA -g rg-lesson03 -l centralindia --sku Standard_LRS

echo "hello-from-lesson-03" > hello.txt
az storage container create -n data --account-name $SA --auth-mode key
az storage blob upload -c data -n hello.txt -f hello.txt --account-name $SA --auth-mode key
```

Write down the account's **birth certificate**. It can never change unless
the account is deleted and recreated:

```bash
az storage account show -n $SA -g rg-lesson03 --query creationTime -o tsv
# 2026-09-29T12:38:48.267595+00:00   ← keep this
```

---

## Step 2: the trap 🪤

Look at `main.tf`. It contains exactly what you gave `az`: name, resource
group, location, `Standard`, `LRS`. It looks correct. Plan it:

```bash
terraform plan
```

```
  # azurerm_resource_group.lesson will be imported
  # azurerm_storage_account.lesson will be updated in-place
  ~ resource "azurerm_storage_account" "lesson" {
      ~ allow_nested_items_to_be_public    = false -> true
      ~ min_tls_version                    = "TLS1_0" -> "TLS1_2"
Plan: 2 to import, 0 to add, 1 to change, 0 to destroy.
```

**`1 to change`** when you only wanted to import. Where did those two lines
come from? You never wrote either setting!

### Why this happens

Every setting you **don't write** in `main.tf` gets the **provider's
default**. And `az` has **its own defaults**, which are not always the same:

| Setting | What `az` created | Terraform provider's default | If you applied now… |
|---|---|---|---|
| `allow_nested_items_to_be_public` | `false` (private) | `true` | 🔥 blobs could be made **public** |
| `min_tls_version` | `TLS1_0` (old) | `TLS1_2` | old clients might break |

The import would have **changed a live, data-holding resource** without you
asking for it. One of those changes is a security hole.

### ✋ The rule

> During an import, **fix the code to match Azure. Never let the import change Azure.**
> Improvements come afterwards, as a separate, deliberate step.

---

## Step 3: fix the code, not Azure

Add these two lines to the storage account in `main.tf`:

```hcl
resource "azurerm_storage_account" "lesson" {
  # ... existing lines ...

  min_tls_version                 = "TLS1_0" # matches what az created
  allow_nested_items_to_be_public = false    # provider default is true!
}
```

```bash
terraform plan
# Plan: 2 to import, 0 to add, 0 to change, 0 to destroy.   ✅
```

**How would you find this on a real resource?** Always the same way: plan,
read every `~` line, and copy the value on the **left** of the arrow (that's
what Azure has now) into your code. Repeat until `0 to change`.

## Step 4: import, then remove the import blocks

```bash
terraform apply        # "yes" → Resources: 2 imported, 0 added, 0 changed
rm import.tf
terraform plan         # → No changes.
```

---

## Step 5: now improve it, on purpose

Make two changes in `main.tf`:

```hcl
  min_tls_version                 = "TLS1_2"   # ← was TLS1_0: upgrade security
  allow_nested_items_to_be_public = false

  tags = {                                      # ← new
    managed_by = "terraform"
  }
```

```bash
terraform plan
```

```
  ~ resource "azurerm_storage_account" "lesson" {
      ~ min_tls_version = "TLS1_0" -> "TLS1_2"
      ~ tags            = {
          + "managed_by" = "terraform"
Plan: 0 to add, 1 to change, 0 to destroy.
```

It's the same `TLS1_0 -> TLS1_2` line as the trap in Step 2. The difference
is that **this time you chose it**. Apply, then check that it's the same
account and the data survived:

```bash
terraform apply
az storage account show -n $SA -g rg-lesson03 --query creationTime -o tsv   # SAME as Step 1 ✅
az storage blob download -c data -n hello.txt -f out.txt --account-name $SA --auth-mode key
cat out.txt                                                                    # hello-from-lesson-03 ✅
```

---

## ⚠️ Edge cases

### Edge case A: renaming = delete + create 🔥

Some settings can't be changed on an existing resource. Try a new name
(`-var` overrides `terraform.tfvars` for one command, and nothing is changed):

```bash
terraform plan -var storage_account_name=stlesson03renamed
```

```
  # azurerm_storage_account.lesson must be replaced
      ~ name = "stlesson03ccb907" -> "stlesson03renamed" # forces replacement
Plan: 1 to add, 0 to change, 1 to destroy.
```

Applying that would **delete the account and hello.txt with it**. Read
every plan for `must be replaced` and `forces replacement`.

### Edge case B: a safety lock, `prevent_destroy`

Add this inside the storage account block in `main.tf`:

```hcl
  lifecycle {
    prevent_destroy = true
  }
```

Try the rename again, and even `terraform destroy`:

```bash
terraform plan -var storage_account_name=stlesson03renamed
terraform destroy
```

```
Error: Instance cannot be destroyed
```

Terraform now **refuses** any plan that would delete this account. Put it
on every imported resource that holds data you can't lose.

---

## Step 6: clean up

Remove the `lifecycle { prevent_destroy = true }` block first. The lock
works on `destroy` too. Then:

```bash
terraform destroy                    # "yes" → 2 destroyed
az group exists -n rg-lesson03       # → false
rm -f terraform.tfstate* hello.txt out.txt
git checkout main.tf import.tf       # back to the lesson's starting files
```

---

## 🧠 What you learned

- A setting you don't write = **the provider's default**, which can differ from the portal's or `az`'s.
- Import rule: **make the code match Azure** (`0 to change`), and only then improve it in a separate step.
- **How to fix a mismatch:** copy the value on the *left* of `->` into your code.
- `forces replacement` = delete + create = **data loss**.
- `prevent_destroy` makes Terraform refuse to delete a resource.
- `creationTime` is a simple way to prove "updated, not recreated".

➡️ **Next:** [Lesson 04](../04-let-terraform-write-the-code/): when you don't know every setting, let Terraform write the code for you.
