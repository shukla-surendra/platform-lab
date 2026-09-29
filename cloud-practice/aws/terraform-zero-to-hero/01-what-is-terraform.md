# 01 · What Terraform is, and why it exists

## 🎯 Goal

Explain in plain words what Terraform does, what problem it solves, and how
it differs from clicking in the AWS console, writing scripts, or using
CloudFormation.

---

## 🧠 Mental model: the architect's blueprint

Imagine building a house in two ways.

**Way 1: give the builder instructions.** "Pour a foundation. Build four
walls. Add a roof." If the builder already poured the foundation yesterday
and you give the same instructions again, you get *two* foundations. You
have to remember what's already been done.

**Way 2: give the builder a blueprint.** "The finished house looks like
*this*." The builder walks around, compares the blueprint with what's
already standing, and does only what's missing. Hand over the same
blueprint twice and nothing happens the second time, because the house
already matches.

Terraform is **Way 2**. You describe the infrastructure you **want**, and
Terraform works out the steps to get there.

```
   what you WANT            what EXISTS                 what Terraform does
 ┌──────────────┐        ┌──────────────┐          ┌──────────────────────┐
 │ 1 VPC        │        │ 1 VPC        │          │ nothing              │
 │ 2 subnets    │ vs.    │ 1 subnet     │   ──▶    │ create 1 subnet      │
 │ 3 servers    │        │ 4 servers    │          │ delete 1 server      │
 └──────────────┘        └──────────────┘          └──────────────────────┘
```

---

## 🛠 Walkthrough

### Step 1: the problem with clicking in the console

Say you build your app's infrastructure by clicking: a VPC, subnets, a
security group, an EC2 instance, an RDS database. It works. Now:

- **"Make a staging copy."** You click it all again and get something slightly different.
- **"Who opened port 22 to the world last month?"** Nobody knows.
- **"The region went down. Rebuild in another region."** How long would that take?
- **"What exactly is running in prod?"** You'd have to look at 40 console pages.

Clicking has no **history**, no **review**, and no **repeatability**.

### Step 2: Infrastructure as Code (IaC)

**Infrastructure as Code** means your infrastructure is described in text
files that live in Git, just like application code. You immediately get:

| Benefit | What it means |
|---|---|
| **Repeatable** | the same files build dev, staging, and prod identically |
| **Reviewable** | changes go through pull requests; a teammate reads the diff before prod changes |
| **Auditable** | `git log` tells you who changed what, when, and why |
| **Recoverable** | lost a region? Apply the same code somewhere else |
| **Self-documenting** | the code *is* the up-to-date description of what exists |

### Step 3: declarative vs imperative

There are two ways to write IaC.

**Imperative** (a script with steps):

```bash
aws ec2 create-security-group --group-name web ...
aws ec2 authorize-security-group-ingress --group-name web --port 443 ...
aws ec2 run-instances --security-groups web ...
```

Run it twice and it fails ("group already exists"), or worse, creates two
servers. You must write your own "does it exist yet?" checks for every step.

**Declarative** (Terraform):

```hcl
resource "aws_security_group" "web" {
  name = "web"
}

resource "aws_instance" "app" {
  ami                    = "ami-0abc123"
  instance_type          = "t3.micro"
  vpc_security_group_ids = [aws_security_group.web.id]
}
```

You never say "create". You say "this should exist", and Terraform
compares that with reality and creates, updates, or deletes as needed. Run
it a hundred times and you get the same result. That property has a name:
**idempotent**.

### Step 4: how Terraform actually does it (the 30-second version)

```
   your .tf files  ──┐
                     ├──▶  TERRAFORM  ──▶  plan: "+ create subnet, ~ update SG"
   state file     ───┤        │
   (its memory)      │        ▼
   real AWS  ────────┘   calls AWS APIs to make it happen
```

Terraform needs three inputs:

1. **Your code**: what you want.
2. **The state file**: a record of which real AWS objects Terraform
   created, for example "my `aws_instance.app` is `i-0a1b2c3d`". Lesson 11
   covers this in depth.
3. **Real AWS**: Terraform reads current settings from the AWS APIs.

It compares them, shows you a **plan** (the list of changes), and after
you approve, calls the AWS APIs to make those changes.

### Step 5: providers: how one tool speaks to every cloud

Terraform itself knows **nothing** about AWS. It knows how to read your
code, build a plan, and track state. The AWS knowledge lives in a plugin
called the **AWS provider**, which Terraform downloads.

```
                 ┌──────────── Terraform Core ────────────┐
                 │  reads code · builds plan · keeps state │
                 └───────┬──────────────┬──────────────┬───┘
                         │              │              │
                   AWS provider   Azure provider   GitHub provider   … 4,000+ more
                         │
                   AWS APIs (EC2, S3, IAM…)
```

That's why the same workflow manages AWS, Azure, Kubernetes, GitHub,
Datadog, Cloudflare… Lesson 17 shows how Core and providers talk to each other.

### Step 6: where Terraform fits among other tools

| Tool | What it's for | How it relates to Terraform |
|---|---|---|
| **AWS Console** | clicking | fine for exploring; not for anything you need to reproduce |
| **AWS CLI / SDK scripts** | imperative automation | great for one-off tasks; bad at "make it match" |
| **CloudFormation** | AWS's own declarative IaC (YAML/JSON) | same idea, AWS-only; AWS keeps the state for you |
| **AWS CDK** | write CloudFormation in TypeScript/Python | real programming language; still AWS-only underneath |
| **Pulumi** | declarative IaC in TypeScript/Python/Go | like Terraform but in general-purpose languages |
| **OpenTofu** | an open-source **fork** of Terraform | near drop-in compatible; created after HashiCorp changed Terraform's licence in 2023 |
| **Ansible / Chef** | configure *inside* servers (packages, files) | complementary: Terraform builds the server, Ansible configures it |

Terraform's strengths are **one workflow for every cloud and SaaS**, a
huge ecosystem of providers and modules, and a plan you can read before
anything changes.

---

## ⚠️ Common mistakes (in understanding)

- **"Terraform is a scripting language."** It isn't. It's a description of an end state. You can't write "do this, then that" (at least not directly).
- **"Terraform configures servers."** Mostly not. It creates the server. Installing software inside it is a job for user data, images (Packer), or configuration tools.
- **"Terraform watches my infrastructure."** It doesn't. It only looks when you run `plan` or `apply`. Anything changed in between is detected on the next run (that's "drift", lesson 13).
- **"If I delete the code, nothing happens."** Wrong. If a resource is in the state but no longer in the code, Terraform **destroys** it on the next apply.

---

## 🎤 Interview corner

**Q: What is Terraform and why would a team use it?**

> Terraform is a declarative Infrastructure-as-Code tool. You describe the
> desired end state of your infrastructure in HCL, and Terraform computes
> and executes the changes needed to reach it by calling provider APIs.
> Teams use it for repeatability across environments, code review of
> infrastructure changes, an audit trail through Git, and one workflow
> across many clouds and SaaS products thanks to its provider model.

**Q: Declarative vs imperative?**

> Imperative describes *steps* ("create X, then Y"), so the author has to
> handle the current state themselves. Declarative describes the *end
> state*, and the tool computes the steps by diffing desired and actual
> state. That makes Terraform idempotent: applying the same code twice
> changes nothing the second time.

**Q: Terraform vs CloudFormation?**

> Both are declarative. CloudFormation is AWS-only, and AWS manages the
> state for you, with native rollback on failure. Terraform is
> multi-provider, and you manage the state yourself (usually in S3). It has
> a larger ecosystem and a plan you can see before any change.
> CloudFormation change sets are the rough equivalent of that plan.
> Terraform does **not** roll back automatically: a failed apply leaves a
> partial result that you fix forward.

---

## ✅ Check yourself

1. In one sentence, what does "idempotent" mean for Terraform?
2. Terraform shows a plan to create 3 servers. You apply. Then you run `apply` again without changing anything. What happens?
3. Where does Terraform's knowledge of AWS come from?
4. A teammate stops a Terraform-managed EC2 instance from the console. When will Terraform notice?

<details><summary>Answers</summary>

1. Applying the same code again produces no further changes, because reality already matches.
2. Nothing: "No changes. Your infrastructure matches the configuration."
3. From the **AWS provider**, a plugin Terraform downloads. Terraform Core itself knows no cloud APIs.
4. Only the next time someone runs `terraform plan` or `apply`. Terraform doesn't watch continuously.

</details>

➡️ **Next:** [02 · Your first resource](02-first-resource.md)
