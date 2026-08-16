# Service Quotas — troubleshooting

Grounded in a real session: launching a `g6.xlarge` GPU instance via Terraform on a
never-used-GPU account. Three distinct errors, in the order they actually occurred —
worth reading in order, because each one looks superficially like "a permissions
problem" until you check which specific action is denied.

## 1. `UnauthorizedOperation` on `ec2:ImportKeyPair` / `ec2:CreateSecurityGroup`

```
Error: importing EC2 Key Pair: ... UnauthorizedOperation: You are not authorized
to perform: ec2:ImportKeyPair ... because no identity-based policy allows the
ec2:ImportKeyPair action.

Error: creating Security Group: ... UnauthorizedOperation: ... ec2:CreateSecurityGroup
... because no identity-based policy allows the ec2:CreateSecurityGroup action.
```

**Diagnosis.** The calling IAM user had `AmazonS3FullAccess`, `IAMFullAccess`,
`AmazonSSMFullAccess`, `AWSCloudFormationFullAccess`, `AWSCodeCommitFullAccess` —
every one of those services worked fine — but **nothing granting `ec2:*`**.
Confirm exactly what's attached before guessing:

```bash
aws iam list-attached-user-policies --user-name <user>
aws iam list-user-policies --user-name <user>            # inline policies
aws iam list-groups-for-user --user-name <user>           # then check the group too
aws iam list-attached-group-policies --group-name <group>
```

**A subtlety worth knowing:** `terraform plan` had already succeeded several times
before this — AMI lookup, subnet/VPC lookup, spot-price history all resolved fine.
Those are all `ec2:Describe*` calls. **[Inferred]** They almost certainly worked as
a side effect of `AWSCloudFormationFullAccess`, which bundles broad `ec2:Describe*`
so CloudFormation can introspect cross-service state during change-set validation —
not because EC2 access was actually granted. **Read access succeeding is not
evidence that write access will too** — Describe* and Create*/Run* are entirely
separate action namespaces in IAM, and a policy can easily grant one without the
other.

**Fix:**
```bash
aws iam attach-user-policy --user-name <user> \
  --policy-arn arn:aws:iam::aws:policy/AmazonEC2FullAccess
```
(Or a scoped custom policy — see `architecture.md`'s note on this — if the account
follows least-privilege rather than the "one FullAccess policy per service" pattern
this particular account happened to already use everywhere else.)

## 2. `AccessDeniedException` on `servicequotas:ListServiceQuotas` — even right after fixing #1

```
AccessDeniedException: ... not authorized to perform: servicequotas:ListServiceQuotas
because no identity-based policy allows the servicequotas:ListServiceQuotas action
```

**Diagnosis.** `AmazonEC2FullAccess` does **not** include `servicequotas:*` — Service
Quotas is its own IAM namespace, separate from the service it happens to be
quota-ing. Easy to assume "full EC2 access" implies "can manage EC2's quotas too";
it doesn't.

**Fix:** same pattern, different policy:
```bash
aws iam attach-user-policy --user-name <user> \
  --policy-arn arn:aws:iam::aws:policy/ServiceQuotasFullAccess
```

**Then — this genuinely happened, don't skip it:** the very next call *still*
failed with the identical error, immediately after the attach returned success
(`exit 0`) and `list-attached-user-policies` confirmed the policy was there. This
was **IAM propagation delay**, not a failed attach — AWS IAM changes are eventually
consistent, and can take anywhere from a few seconds to ~30s+ to actually take
effect for subsequent API calls, even though the control-plane `attach-user-policy`
call itself returns immediately. **Don't conclude the fix didn't work from one
immediate retry** — poll with backoff instead of guessing at a different cause:

```bash
until aws service-quotas get-service-quota --service-code ec2 \
    --quota-code L-DB2E81BA --region us-east-1 >/dev/null 2>&1 \
  || [ "$i" -ge 6 ]; do i=$((i+1)); sleep 10; done
```

## 3. `VcpuLimitExceeded` on `RunInstances` — the actual root cause, not a permissions issue

```
VcpuLimitExceeded: You have requested more vCPU capacity than your current vCPU
limit of 0 allows for the instance bucket that the specified instance type
belongs to.
```

**Diagnosis.** This is not IAM, not Terraform, not a config mistake. Every fresh
AWS account defaults to a `0` vCPU quota on GPU/accelerator instance families —
see `architecture.md` for the full mechanism and why. The fix isn't a policy
attach, it's an actual AWS-reviewed quota increase request:

```bash
aws service-quotas request-service-quota-increase \
  --service-code ec2 --quota-code L-DB2E81BA \
  --desired-value 4 --region us-east-1     # 4 = one g6.xlarge's vCPU count
```

**Fix takes real wall-clock time, not a retry.** Status starts `PENDING`; there is
nothing to debug or retry while it sits there — polling faster doesn't speed up an
AWS support review. Move on to other work and check back:

```bash
aws service-quotas get-requested-service-quota-change \
  --request-id <id-from-the-request-above> \
  --query 'RequestedQuota.Status' --output text
```

## Pattern across all three

Each error *looked* like the same category of problem ("some permission is
missing") but had a genuinely different fix — attach a policy, attach a different
policy + wait for propagation, or file a request and wait for human review. **Read
the exact denied action name before reaching for a broader policy** — `ec2:*` vs
`servicequotas:*` vs "not a permissions problem at all" are three different
diagnoses that happen to produce superficially similar-looking CLI errors.
