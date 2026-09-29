# 22 · Troubleshooting

## 🎯 Goal

Diagnose Terraform errors calmly and quickly: know which **layer** an
error comes from, recognise the 15 errors you'll meet most, and have a
fix for each.

---

## 🧠 Mental model: which layer is complaining?

```
 1. HCL / config     "Unsupported argument", "Invalid reference", "Cycle"        → your code
 2. Terraform Core   "Invalid for_each argument", "state lock", "inconsistent"   → Terraform rules / state
 3. Provider         "Provider produced inconsistent…", "timeout while waiting"  → the plugin
 4. AWS API          "AccessDenied", "AlreadyExists", "LimitExceeded", "InvalidParameter" → AWS said no
 5. Credentials      "No valid credential sources found", "ExpiredToken"         → your identity
```

**Read errors from the bottom up.** The last lines usually contain the
real API message. For AWS errors, look for the **operation name** (like
`CreateBucket`) and the **status code**. They tell you exactly which API
call failed.

---

## 🛠 The error catalogue

### 1. No credentials / expired credentials

```
Error: No valid credential sources found
Error: ... ExpiredToken: The security token included in the request is expired
```

**Fix:** `aws sts get-caller-identity` to see what your shell really
uses. Then `aws sso login`, check `AWS_PROFILE`, or refresh the CI OIDC setup.

### 2. AccessDenied / UnauthorizedOperation

```
Error: creating EC2 Instance: operation error EC2: RunInstances,
  api error UnauthorizedOperation: You are not authorized to perform this operation.
  Encoded authorization failure message: 4Ztx...
```

**Fix:** find the action (`ec2:RunInstances`) and add it to the Terraform
role. EC2 gives an encoded message, which you decode to see exactly which
policy denied it:

```bash
aws sts decode-authorization-message --encoded-message 4Ztx... --query DecodedMessage --output text | jq
```

Also check SCPs, permission boundaries, and KMS key policies. They can
deny even when the IAM policy allows.

### 3. Resource already exists

```
Error: creating S3 Bucket (notes-app-assets): BucketAlreadyOwnedByYou
Error: creating IAM Role (notes-app): EntityAlreadyExists
```

It exists in AWS but not in this state: created by hand, by another
state, or left behind after a lost state. **Fix:** import it (lesson 13),
or rename yours if it belongs to someone else.

### 4. State lock

```
Error: Error acquiring the state lock
  Lock Info: ID: 6d2f..., Who: runner@ci, Operation: OperationTypeApply
```

**Fix:** wait (`-lock-timeout=5m`). If you're **sure** the holder is dead:
`terraform force-unlock 6d2f...` (lesson 12).

### 5. Cycle

```
Error: Cycle: aws_security_group.app, aws_security_group.db
```

Two things reference each other. **Fix:** break the loop. The usual cause
is security groups with inline rules pointing at each other. Create the
groups empty and add the rules as separate resources. Use
`terraform graph` to visualise it.

### 6. Invalid for_each / count argument

```
Error: Invalid for_each argument
  ... includes values derived from resource attributes that cannot be determined until apply
```

**Fix:** key on values you control (names from variables or locals),
and use unknown attributes only inside each instance (lesson 09). As a
one-time bootstrap only: `terraform apply -target=<dependency>`, then
apply normally.

### 7. Perpetual diff (plan always shows a change)

The same `~` change appears on every plan, even right after apply.
Common causes:

| Cause | Fix |
|---|---|
| a JSON policy string that AWS reformats | use `jsonencode()` or `aws_iam_policy_document` |
| case or format normalisation (`TCP` vs `tcp`, `10.0.0.0/16` vs `10.0.0.0/16 `) | write the value exactly as AWS returns it |
| `timestamp()` / `uuid()` in arguments | remove them, or use `terraform_data` / `ignore_changes` |
| two resources managing the same thing (inline `ingress` + separate rule resources) | pick one style |
| something outside keeps changing it (autoscaling, tags added by another tool) | `lifecycle { ignore_changes = [...] }` |
| a provider bug | upgrade the provider; search its GitHub issues |

### 8. Unexpected replacement

```
-/+ resource "aws_instance" "web" {
      ~ ami = "ami-0abc" -> "ami-0def" # forces replacement
```

**Find the `# forces replacement` line.** Then either revert the change,
accept it with `create_before_destroy`, or `ignore_changes` the attribute
if something else manages it (a `most_recent` AMI is the classic culprit).

### 9. Provider produced inconsistent result after apply

```
Error: Provider produced inconsistent result after apply
  When applying changes to aws_x.y, provider produced an unexpected new value: .tags: ...
  This is a bug in the provider...
```

The resource was probably **created**, but its state may be imperfect.
**Fix:** run `plan` again (it usually reconciles). Upgrade the provider,
check its issues, and adjust the config to avoid the normalisation (e.g.
the tags/case trigger).

### 10. Provider configuration not present

```
Error: Provider configuration not present
  To work with module.old.aws_s3_bucket.x its original provider configuration
  at module.old.provider["registry.terraform.io/hashicorp/aws"] is required, but it has been removed.
```

You removed a module (or an aliased provider) that had its own provider
block, and the state still has its resources. **Fix:** temporarily
restore the provider config so Terraform can destroy them (or use
`removed` blocks), then delete it. This is why modules shouldn't contain
provider blocks (lesson 14).

### 11. Destroy fails

| Error | Cause | Fix |
|---|---|---|
| `BucketNotEmpty` | S3 won't delete non-empty buckets | empty it first, or `force_destroy = true` (deliberately) |
| `DependencyViolation` on SG / subnet / VPC | something outside Terraform still uses it (an ENI from Lambda, a load balancer created by Kubernetes) | find it (`aws ec2 describe-network-interfaces --filters Name=group-id,Values=sg-…`) and delete it |
| `InvalidDBInstanceState` / deletion protection | `deletion_protection = true` | set it to false in code, apply, then destroy |
| "Instance cannot be destroyed" | `prevent_destroy` | remove it deliberately (it's there for a reason) |
| RDS wants a final snapshot | `skip_final_snapshot = false` | set `final_snapshot_identifier`, or skip for non-prod |

### 12. Version and lock problems

```
Error: Failed to query available provider packages
  ... no available releases match the given constraints >= 6.0, < 5.0
```

Two modules demand incompatible versions. **Fix:** align constraints
(modules should use `>=` minimums, lesson 14).

```
Error: Failed to install provider ... the local package doesn't match any of the checksums
```

The lock file lacks hashes for this platform. **Fix:**
`terraform providers lock -platform=linux_amd64 -platform=darwin_arm64`.

```
Error: state snapshot was created by Terraform v1.12.0, which is newer than current v1.10.5
```

**Fix:** upgrade the CLI. Pin versions across the team so this doesn't happen.

### 13. Timeouts

```
Error: waiting for RDS DB Instance (notes-prod) create: timeout while waiting for state to become 'available'
```

**Fix:** check the AWS console for the real status or error event.
Increase `timeouts { create = "90m" }` for slow resources. Re-running
`apply` usually picks up where it left off, because the resource is
recorded (possibly tainted).

### 14. LimitExceeded / quota errors

```
Error: ... VcpuLimitExceeded / AddressLimitExceeded / TooManyBuckets
```

**Fix:** check **Service Quotas** and request an increase, or clean up
unused resources (unattached Elastic IPs are a classic).

### 15. "Changes outside of Terraform" in the plan

```
Note: Objects have changed outside of Terraform
  # aws_instance.web has changed
```

That's informational. The refresh found drift, and the plan below it
shows what Terraform will do about it (lesson 13).

---

## 🛠 The debugging toolkit

```bash
terraform validate                          # layer 1 problems
terraform plan -refresh=false               # is the problem in refresh or in the diff?
terraform state show 'aws_instance.web'     # what does Terraform believe?
aws ec2 describe-instances --instance-ids i-…   # what does AWS say?
terraform console                           # evaluate the expression that's failing
terraform graph | dot -Tsvg > g.svg         # dependency problems
TF_LOG=DEBUG TF_LOG_PATH=tf.log terraform apply   # the actual API calls (contains secrets!)
```

**A calm procedure for a failed apply in production:**

1. **Don't** re-run blindly and **don't** `force-unlock` immediately.
2. Read the error bottom-up: which resource, which API call, which message?
3. `terraform plan`: what does Terraform *now* think is left to do?
4. Check AWS directly for the resource's real status.
5. Fix the cause (permission, quota, config) in code, through a PR if possible.
6. Plan again, confirm it only does the remaining work, apply.

---

## 🎤 Interview corner

**Q: Terraform keeps showing the same change on every plan. How do you debug it?**

> That's a perpetual diff. Compare the planned value with what's in state
> (`terraform state show`) and what the API returns. The usual causes are
> normalisation (JSON policies, case, formats), non-deterministic
> functions like `timestamp()`, two resources managing the same setting,
> or an external process changing it. The fixes are: canonical forms
> (`jsonencode`, `aws_iam_policy_document`), removing non-determinism,
> choosing one ownership model, `ignore_changes`, or a provider upgrade
> if it's a bug.

**Q: An apply failed halfway in production. What do you do?**

> Stop and assess before retrying. Read the actual API error, check
> whether the lock was released, and run a plan to see what Terraform
> thinks remains. Verify real resource status in AWS, fix the root cause
> (permissions, quotas, config), and re-plan and apply to converge.
> Terraform doesn't roll back, so we fix forward. Partially created
> resources are either recorded in state (possibly tainted) or need
> importing.

**Q: How do you find out which IAM permission Terraform is missing?**

> The error names the API operation, e.g. `RunInstances`, which maps to the
> IAM action `ec2:RunInstances`. For EC2's encoded failures, decode them
> with `aws sts decode-authorization-message` to see the exact denied
> action and resource. `TF_LOG=DEBUG` shows every request. Also consider
> SCPs, permission boundaries, and resource or KMS policies.

---

## ✅ Check yourself

1. Which layer does "An argument named X is not expected here" come from?
2. `terraform destroy` fails with `DependencyViolation` on a security group. What's the likely cause?
3. Name two causes of a perpetual diff.
4. What's the first command to run after a failed apply?

<details><summary>Answers</summary>

1. HCL/config decoding against the provider schema (your code).
2. Something created outside Terraform (e.g. a Lambda ENI or a load balancer from Kubernetes) still uses the group.
3. Any two: JSON normalisation; case or format differences; `timestamp()`/`uuid()`; two resources managing the same setting; external changes; a provider bug.
4. `terraform plan` (after reading the error), to see what Terraform now believes remains to be done.

</details>

➡️ **Next:** [23 · Capstone](23-capstone.md)
