# Terraform: Zero to Hero (on AWS)

A complete Terraform course for someone who already knows basic AWS (what
an EC2 instance, an S3 bucket, a VPC, and IAM are) and has never used
Terraform, or has used it by copy-pasting without really understanding it.

By the end you will be able to:

- write clean Terraform for real AWS infrastructure, from memory;
- explain **why** Terraform behaves the way it does (state, the graph, unknown values, HCL evaluation);
- structure code for a team (modules, environments, remote state, CI/CD);
- answer senior-level interview questions with confidence.

---

## How this course teaches

**One idea per lesson.** Each file adds exactly one new concept on top of
the previous ones. If a lesson feels easy, good: that means the previous
one did its job.

**One running project.** We build the same thing all course long: a small
web app called **`notes-app`**. It starts as a single S3 bucket in
lesson 02 and grows into a VPC, a load balancer, auto-scaled servers, and
a database, split into modules and environments. You'll see *why* each new
feature exists, because you'll hit the problem it solves first.

**Every lesson has the same shape:**

| Section | What it's for |
|---|---|
| 🎯 **Goal** | what you'll be able to do after this lesson |
| 🧠 **Mental model** | a picture or analogy to hang the details on |
| 🛠 **Walkthrough** | the concept, built up step by step with real code |
| ⚠️ **Common mistakes** | what trips people up (and interviewers know it) |
| 🎤 **Interview corner** | how this topic gets asked, and a strong answer |
| ✅ **Check yourself** | questions with hidden answers. Try before peeking |

You don't have to run anything to learn from these lessons. Every example
is complete enough to run, though, if you want to (see "Running the
examples" below).

---

## The course map

### Part 1: Foundations: what Terraform is and how you use it
| # | Lesson | You'll learn |
|---|---|---|
| 01 | [What Terraform is, and why it exists](01-what-is-terraform.md) | IaC, declarative vs imperative, where Terraform fits |
| 02 | [Your first resource](02-first-resource.md) | install, AWS credentials, `init` / `plan` / `apply` / `destroy` |
| 03 | [The core workflow in depth](03-core-workflow.md) | reading plans, what each command really does, the files it creates |

### Part 2: The HCL language
| # | Lesson | You'll learn |
|---|---|---|
| 04 | [HCL syntax and types](04-hcl-syntax-and-types.md) | blocks, arguments, expressions, every type (list/map/set/object/tuple) |
| 05 | [Providers](05-providers.md) | versions, the lock file, aliases (multi-region, multi-account), `default_tags` |
| 06 | [Resources, data sources, and references](06-resources-and-data-sources.md) | addresses, attributes, implicit dependencies, looking things up |
| 07 | [Variables, locals, and outputs](07-variables-locals-outputs.md) | inputs/outputs, validation, `sensitive`, **variable precedence** |
| 08 | [Expressions and functions](08-expressions-and-functions.md) | conditionals, `for` expressions, splat, templates, the function toolbox |
| 09 | [Meta-arguments: count, for_each, depends_on, lifecycle](09-meta-arguments.md) | **count vs for_each**, lifecycle rules, pre/postconditions |
| 10 | [Dynamic blocks and advanced patterns](10-dynamic-blocks-and-patterns.md) | `dynamic`, nested loops with `flatten`, `optional()`, `try`/`can` |

### Part 3: State: Terraform's memory
| # | Lesson | You'll learn |
|---|---|---|
| 11 | [State deep dive](11-state-deep-dive.md) | what's inside the state file, refresh, serial/lineage, state commands |
| 12 | [Remote state and locking on AWS](12-remote-state-and-locking.md) | S3 backend, native locking, bootstrapping, sharing outputs |
| 13 | [Import, drift, and refactoring](13-import-drift-refactoring.md) | `import`, `moved`, `removed`, `-replace`, `-refresh-only` |

### Part 4: Organising real code
| # | Lesson | You'll learn |
|---|---|---|
| 14 | [Modules](14-modules.md) | writing, versioning, and composing modules. Passing providers |
| 15 | [Environments: dev, staging, prod](15-environments.md) | workspaces vs directories vs Terragrunt, and when to use each |
| 16 | [Project structure and blast radius](16-project-structure.md) | how to split state, repo layouts, naming, team ownership |

### Part 5: Internals (the interview-winning part)
| # | Lesson | You'll learn |
|---|---|---|
| 17 | [How Terraform works inside](17-terraform-internals.md) | Core vs providers, gRPC, the dependency graph, plan/apply phases, unknown values |
| 18 | [HCL internals](18-hcl-internals.md) | parsing, bodies and schemas, the `cty` type system, evaluation order, why some things can't be variables |

### Part 6: Production
| # | Lesson | You'll learn |
|---|---|---|
| 19 | [Security and secrets](19-security-and-secrets.md) | secrets in state, ephemeral values, OIDC, least privilege, scanners |
| 20 | [Testing and policy](20-testing-and-policy.md) | `validate`, `tflint`, `terraform test`, `check` blocks, policy as code |
| 21 | [CI/CD and team workflow](21-cicd-and-team-workflow.md) | PR plans, saved plans, OIDC to AWS, drift detection, Atlantis / HCP Terraform |
| 22 | [Troubleshooting](22-troubleshooting.md) | reading errors, `TF_LOG`, stuck locks, cycles, provider bugs |
| 23 | [Capstone: notes-app, production-shaped](23-capstone.md) | everything together: VPC + ALB + ASG + RDS, modules, environments, CI |

### Reference
| | |
|---|---|
| [24 · Interview question bank](24-interview-question-bank.md) | 80+ questions from junior to staff level, with model answers and scenarios |
| [25 · Cheat sheet](25-cheat-sheet.md) | commands, syntax, and patterns on a few pages |

---

## Suggested study plan

| Week | Lessons | Goal |
|---|---|---|
| 1 | 01 → 06 | You can write and apply basic resources and read any plan |
| 2 | 07 → 10 | You can write flexible, loop-driven, validated code |
| 3 | 11 → 13 | You understand state and never fear it again |
| 4 | 14 → 16 | You can structure code the way teams do |
| 5 | 17 → 18 | You can explain Terraform's internals on a whiteboard |
| 6 | 19 → 23 | You can run Terraform in production |
| ongoing | 24 | Practise answering out loud |

**Study tip:** after each lesson, close it and explain the main idea out
loud in two minutes, as if to a colleague. If you get stuck, that's the
part to re-read. This single habit is worth more than re-reading everything twice.

---

## Running the examples (optional)

- Terraform **1.10 or newer** (some later lessons mention newer features and say so).
- An AWS account you're allowed to experiment in, and the AWS CLI configured (`aws sts get-caller-identity` works).
- Examples use region `ap-south-1` (Mumbai) and small or free-tier sizes. **Always run `terraform destroy` when you finish playing.**

Related material in this repo:
- [`../../Terraform-Complete-Reference/`](../../Terraform-Complete-Reference/): a short reference to review after this course.
- [`../terraform/`](../terraform/): ready-made Terraform for ~30 AWS services, good for reading "real" code once you've done Part 2.
- [`../terraform_practice/`](../terraform_practice/): hands-on practice projects.
