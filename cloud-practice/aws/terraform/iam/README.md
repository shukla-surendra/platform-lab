# Terraform: IAM — Group/User/Policy and a Role's Two Policies, Verified Live

Creates one S3 bucket, a Group with a custom read-only policy, a User who
is a *member* of that group (no policy of its own), and a Role with its
own independent trust policy + write-only permission policy. Demonstrates
the concepts in [`../../docs/iam/architecture.md`](../../docs/iam/architecture.md):
Users vs Groups vs Roles vs Policies, and the fact that a Role's "who can
become it" and "what it can do" are two entirely separate documents.

> ⚠️ **Mostly free.** IAM entities (Users/Groups/Roles/Policies) aren't
> billed at all. The only cost here is the S3 bucket/objects, effectively
> nothing at this scale. Run `terraform destroy` when done.

## What it creates

```
S3 bucket (aws-mastery-iam-<random>), one seed object

Group: developers ──attached──> Policy: developer-readonly
                                   (s3:GetObject, s3:ListBucket)
User: demo-user ──member of──> Group: developers
                                   (no policy of its own)

Role: uploader ──trust policy──> trusts whoever ran `terraform apply`
              ──permission policy──> Policy: uploader-permission
                                       (s3:PutObject only)
```

## Usage

```bash
cd aws/terraform/iam
cp terraform.tfvars.example terraform.tfvars
terraform init
terraform plan
terraform apply
terraform output next_steps
```

## Verify: assume the role, prove the boundary — actual output from this exact apply

```bash
ROLE_ARN=$(terraform output -raw role_arn)
BUCKET=$(terraform output -raw bucket_name)

CREDS=$(aws sts assume-role --role-arn "$ROLE_ARN" --role-session-name manual-test --query 'Credentials' --output json)
export AWS_ACCESS_KEY_ID=$(echo "$CREDS" | jq -r .AccessKeyId)
export AWS_SECRET_ACCESS_KEY=$(echo "$CREDS" | jq -r .SecretAccessKey)
export AWS_SESSION_TOKEN=$(echo "$CREDS" | jq -r .SessionToken)

aws sts get-caller-identity
```
```json
{
    "UserId": "AROAZ4W5PXJ7IN33SXZ7M:manual-test",
    "Account": "680143075966",
    "Arn": "arn:aws:sts::680143075966:assumed-role/aws-mastery-iam-uploader/manual-test"
}
```

Notice the `Arn` — no longer the User that ran `terraform apply`, now an
**assumed-role** identity, `<role-name>/<session-name>`, and this token
self-expires (`Expiration` in the `sts assume-role` response) — nothing
to manually revoke later.

**Allowed** (the permission policy grants `s3:PutObject`):

```bash
echo "hello from the uploader role" | aws s3 cp - "s3://$BUCKET/from-role.txt"
```

Succeeded — confirmed by listing the bucket with a separate, broader
identity afterward: `from-role.txt` is really there, 29 bytes.

**Denied** (the permission policy never granted `s3:GetObject`):

```bash
aws s3 cp "s3://$BUCKET/seed.txt" -
```

```
download failed: s3://aws-mastery-iam-rvfddzlb/seed.txt to -
An error occurred (403) when calling the HeadObject operation: Forbidden
```

Worth noting exactly what this says vs. what you might expect: `aws s3
cp` issues a `HeadObject` call before the actual `GetObject` (to check
the object exists / get its size for progress reporting), and *that*
call is what gets denied first — the error is `403 Forbidden` on
`HeadObject`, not the more commonly-cited `AccessDenied` on `GetObject`
directly. Same underlying cause (no read permission anywhere in the
role's policy), different API call surfaces the denial depending on
which higher-level operation you use to trigger it — worth knowing so a
`403`/`HeadObject` error doesn't read as a different, more mysterious
problem than it is.

```bash
unset AWS_ACCESS_KEY_ID AWS_SECRET_ACCESS_KEY AWS_SESSION_TOKEN   # done — back to your own identity
```

## Why no access keys for this user

`aws_iam_user.demo_user` deliberately has no paired `aws_iam_access_key`
resource. That's not an oversight — it's the same "prefer Roles over
Users, prefer temporary over permanent credentials" lesson from
`docs/iam/architecture.md` applied to this module's own design: the Group
membership and policy attachment are fully real and inspectable
(`aws iam list-groups-for-user --user-name aws-mastery-iam-demo-user`,
`aws iam list-attached-group-policies --group-name aws-mastery-iam-developers`)
without ever minting a long-lived secret that would then need rotating
or leaking-and-being-noticed. The live allow/deny proof above uses the
*Role* instead, precisely because a Role never requires that trade-off.

## Files

| File | Purpose |
|---|---|
| `versions.tf` | Provider pins + default tags |
| `variables.tf` | Region, project/name prefix |
| `main.tf` | S3 bucket, Group + policy + User + membership, Role + trust + permission policy |
| `outputs.tf` | ARNs/names + a `next_steps` runbook (the exact commands above) |

## Things to try

1. `aws iam get-policy-version --policy-arn $(terraform output -raw ...) ...`
   (command in `next_steps`) — read the actual compiled JSON policy
   document back from AWS, side by side with `main.tf`'s
   `aws_iam_policy_document` block that generated it.
2. Add `s3:GetObject` to `uploader_permission`'s `actions` and re-`apply`
   — re-run the "denied" step above, watch it succeed instead. Nothing
   about the Role or its trust policy changes; only the permission
   policy's `Action` list does.
3. Change the trust policy's `principals` block to a different AWS
   account's ARN and try to assume it from this account — watch it fail
   even though the permission policy is unchanged, proving trust and
   permission really are two independent checks.

## What's deliberately not here

No `aws_iam_access_key` for the demo user (see above). No permission
boundary or SCP (this is a single-account, non-Organizations demo — see
`docs/iam/architecture.md`'s policy-evaluation section for where those
fit). No cross-account trust policy (the Role trusts whoever applies
this, same account, purely so this module's own verification steps work
standalone). No AWS-managed policies used anywhere — both policies here
are customer-managed, written out in full, specifically so the policy
document itself stays visible and readable in `main.tf` rather than
hidden behind a name like `AmazonS3ReadOnlyAccess`.

## Teardown

```bash
terraform destroy
```
