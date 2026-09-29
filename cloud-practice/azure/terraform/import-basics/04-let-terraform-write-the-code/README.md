# Lesson 04: let Terraform write the code for you

⏱ about 20 minutes · 💰 free (a network security group costs nothing) · 📋 do lessons 01–03 first

In lesson 03 you found the right settings by reading the plan and fixing
one line at a time. That's fine for 2 settings. A real resource can have 40.

**By the end you will be able to:**
1. Make Terraform **generate** the resource code from what exists in Azure.
2. Turn that generated code into clean code a human can maintain.
3. Understand a common surprise: **Terraform deletes things added by hand** to a list it owns.

The service is a **Network Security Group (NSG)**, a firewall with a list of
rules. `main.tf` has only the provider and **no resource blocks**.
`import.tf` has two import blocks.

---

## Step 0: setup

```bash
cd import-basics/04-let-terraform-write-the-code
echo "subscription_id = \"$(az account show --query id -o tsv)\"" > terraform.tfvars
terraform init
```

## Step 1: create by hand: resource group + firewall + one rule

```bash
az group create -n rg-lesson04 -l centralindia
az network nsg create -n nsg-web -g rg-lesson04 -l centralindia
az network nsg rule create --nsg-name nsg-web -g rg-lesson04 -n allow-https \
  --priority 100 --access Allow --direction Inbound --protocol Tcp --destination-port-ranges 443
```

---

## Step 2: a normal plan fails, because there's no code to import into

```bash
terraform plan
```

```
Error: Configuration for import target does not exist
  on import.tf line 5, in import:
   5:   to = azurerm_resource_group.lesson
```

An import block needs a `resource` block to attach to. We don't have one yet.

## Step 3: ask Terraform to write it ✨

```bash
terraform plan -generate-config-out=generated.tf
```

```
  # azurerm_network_security_group.web will be imported
  # (config will be generated)
  # azurerm_resource_group.lesson will be imported
  # (config will be generated)
Plan: 2 to import, 0 to add, 0 to change, 0 to destroy.

Warning: Config generation is experimental
```

Open `generated.tf`. Here's part of it:

```hcl
resource "azurerm_network_security_group" "web" {
  location            = "centralindia"
  name                = "nsg-web"
  resource_group_name = "rg-lesson04"
  security_rule = [{
    access                                     = "Allow"
    description                                = ""
    destination_address_prefix                 = "*"
    destination_address_prefixes               = []
    destination_application_security_group_ids = []
    destination_port_range                     = "443"
    ...16 lines for one rule...
  }]
  tags = {}
}
```

Terraform read the NSG from Azure and wrote **every** attribute, including
empty ones. It's correct, but ugly. Because it came from reality, there's no
hidden-defaults trap: `0 to change`.

## Step 4: import with the generated code

```bash
terraform apply        # → Resources: 2 imported, 0 added, 0 changed
terraform plan         # → No changes.
```

---

## Step 5: tidy it up (a normal part of the job)

Generated code is a **first draft**. You'd never commit it as-is. Replace
it with a clean file:

```bash
rm import.tf generated.tf
cp solution/network.tf .
```

Compare `solution/network.tf` with what was generated. We:

| Changed | Why |
|---|---|
| deleted `[]`, `{}`, `""`, `null` lines | they're defaults and only add noise |
| `security_rule = [{...}]` → `security_rule { ... }` blocks | the normal, readable style |
| `"rg-lesson04"` → `azurerm_resource_group.lesson.name` | a **reference**: Terraform learns the NSG depends on the RG |
| added comments | the next person to read it |

**Check that tidying didn't change the meaning:**

```bash
terraform plan         # → No changes.  ✅
```

> This is the loop for real imports: generate → import → tidy →
> `plan` says No changes → commit. If tidying gave you `1 to change`, you
> deleted a line that wasn't really a default. Put it back.

---

## Step 6: modify: add a rule with Terraform

Add a second `security_rule` block inside the NSG in `network.tf`:

```hcl
  security_rule {
    name                       = "allow-ssh-office"
    priority                   = 110
    direction                  = "Inbound"
    access                     = "Allow"
    protocol                   = "Tcp"
    source_port_range          = "*"
    destination_port_range     = "22"
    source_address_prefix      = "203.0.113.0/24"   # only the office network
    destination_address_prefix = "*"
  }
```

```bash
terraform plan         # Plan: 0 to add, 1 to change, 0 to destroy.
terraform apply
az network nsg rule list --nsg-name nsg-web -g rg-lesson04 -o table   # allow-https + allow-ssh-office
```

> 💡 The plan shows **every** rule with `-` and `+`, as if it were deleting
> and re-adding all of them. That's just how Terraform *displays* a
> changed set. The resource line says `~` (update in place), and only the new
> rule is actually added.

---

## ⚠️ Edge case: a rule added by hand gets DELETED

A teammate debugging something adds a rule in the portal:

```bash
az network nsg rule create --nsg-name nsg-web -g rg-lesson04 -n temp-debug-8080 \
  --priority 200 --access Allow --direction Inbound --protocol Tcp --destination-port-ranges 8080
terraform plan
```

```
  ~ resource "azurerm_network_security_group" "web" {
          - { name = "allow-ssh-office" ...
          - { name = "allow-https" ...
          - { name = "temp-debug-8080" ...
          + { name = "allow-ssh-office" ...
          + { name = "allow-https" ...
Plan: 0 to add, 1 to change, 0 to destroy.
```

Read what gets `-` and does **not** come back with `+`: **temp-debug-8080**.

```bash
terraform apply
az network nsg rule list --nsg-name nsg-web -g rg-lesson04 --query '[].name' -o tsv
# allow-https
# allow-ssh-office        ← the hand-made rule is gone
```

**Why?** Rules written **inside** the NSG block mean "the rule list is
**exactly** these". Anything else is drift, and Terraform removes it.

- 👍 Good if you want strict control: no surprise holes in your firewall.
- 👎 Bad if another team is *supposed* to add rules. The fix is to write each
  rule as its **own** resource (`azurerm_network_security_rule`). Terraform
  then only manages the rules it knows about and ignores the rest. The
  advanced lab [`../../import-existing/`](../../import-existing/) does it that way.

The same "inline list owns everything" behaviour applies to subnets inside a
VNet, tags, and many other lists.

---

## Step 7: clean up

```bash
terraform destroy                    # "yes" → 2 destroyed
az group exists -n rg-lesson04       # → false
rm -f network.tf terraform.tfstate*
git checkout import.tf               # restore the lesson's starting files
```

---

## 🧠 What you learned

- `terraform plan -generate-config-out=generated.tf` writes resource code from what really exists.
- Generated code is a **draft**: import with it, tidy it, and prove the tidy version gives **No changes**.
- References (`azurerm_resource_group.lesson.name`) beat copy-pasted strings.
- An **inline list** (rules inside the NSG) is owned completely: items added by hand get deleted.
- A set changes in the plan look like "remove all, add all", so look at the **net** difference.

➡️ **Next:** [Lesson 05](../05-stop-managing-without-deleting/): the reverse of import. Hand a resource back without deleting it.
