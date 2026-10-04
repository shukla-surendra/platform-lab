# AWS Organizations vs AWS Control Tower

Account IDs, org IDs and emails are deliberately left out of this file (placeholders only).

## 1. Short answer: one or both?

**Both, but they are layers, not alternatives.** Control Tower is built on top of Organizations and cannot exist without it.

- **Organizations** = the structure: accounts, OUs, consolidated billing, SCPs.
- **Control Tower** = an opinionated setup + guardrails *on top of* that structure: landing zone, account enrollment/factory, preventive/detective controls, optional central logging.

You can use Organizations alone (many teams do). You cannot use Control Tower alone.

## 2. What each one does

| | AWS Organizations | AWS Control Tower |
|---|---|---|
| Purpose | Group and manage multiple accounts | Set up and govern a multi-account environment with best practices |
| Cost | Free | No fee of its own; you pay for underlying services (Config, CloudTrail, S3, CloudWatch, SNS, Service Catalog...) |
| Accounts | Create / invite / move / close | Account Factory (Service Catalog) creates/enrolls accounts with baselines |
| Grouping | OUs, root | Registers OUs; only governs accounts inside registered OUs |
| Guardrails | SCPs (you write them) | **Controls**: preventive (SCP-based), detective (Config rules), proactive (CloudFormation hooks) |
| Logging | None built in | Optional central log archive + audit accounts (CloudTrail/Config) |
| Identity | Nothing | Optional IAM Identity Center setup |
| Drift | Not tracked | Detects landing-zone/OU/account drift |
| Needs the other? | No | **Yes, requires Organizations** |

## 3. How they relate (one picture in words)

```
Organizations (always there)
 ├─ Root
 │   ├─ OU (registered in Control Tower)  → governed: baselines + controls apply
 │   └─ OU / accounts NOT registered      → plain Organizations only (SCPs, billing)
 └─ Management account  (hosts both; never "enrolled" itself)

Control Tower = landing zone + controls + Account Factory, driving Organizations,
Service Catalog, CloudFormation StackSets, Config, CloudTrail, IAM Identity Center
```

So the same "accounts / OUs" you see in Control Tower **are** the Organizations objects. There aren't two separate sets; Control Tower is a managed view and workflow over the Organizations tree.

## 4. Findings from this environment (read-only checks)

- Organization exists, feature set **ALL**; trusted services include `controltower.amazonaws.com` and CloudFormation StackSets.
- Two accounts, both joined by **invitation**, both directly under **Root**:
  - **Management account** (shows "Enabled" in Control Tower: it hosts it).
  - **Member account** `awscertification` (shows "Not enabled": never enrolled).
- **No OUs** exist in the organization.
- Landing zone: **ACTIVE**, in sync, one governed region (`us-east-1`), version 4.0.
- Landing zone features all **disabled**: AWS Config, centralized logging, backup, access management (Identity Center), security roles.
- **No** Config recorders/rules, CloudTrail trails, `controltower*` S3 buckets, CloudFormation stacks, or enabled controls/baselines.
- Service Catalog has the "AWS Control Tower Account Factory" product.
- Cost: this is the lowest-cost landing-zone shape (see §6).

### Why the member account is "Not enabled"

Control Tower governs only accounts in OUs it has **registered**. The minimal landing zone created no OUs, so everything under Root is outside it. The member account joined years before the landing zone and was never enrolled.

## 5. How to enroll the member account (not done yet)

1. Create an OU (e.g. `Sandbox`) in Organizations.
2. Control Tower → Organization → **Register OU**.
3. Move the member account into that OU, or use **Enroll account**.
4. Prerequisite for an existing account: an IAM role `AWSControlTowerExecution` in the member account, trusting the management account, with admin permissions. Enrollment fails without it. (Not verified whether it exists; checking requires assuming a role into that account.)
5. No conflicting Config recorder/delivery channel in the member account (none expected, since Config is off).

Enrollment applies baseline stacks; with Config/logging off the extra cost should stay small.

## 6. Cost notes

- Organizations: free. Control Tower: no fee of its own.
- Billable underneath (by usage): Config, CloudTrail, S3, CloudWatch, SNS, Service Catalog, VPC.
- Current setup has Config/logging/backup off, so expected cost is pennies.
- Would add cost: Config-based controls, enabling centralized logging, more governed regions, Account Factory VPCs with NAT gateways.
- Set a budget alert (~$5) and check Cost Explorer after a few days.
- No-cancel note: an in-progress landing-zone setup can't be cancelled; wait for it to finish, then decommission (`aws controltower delete-landing-zone`) and check for leftovers (`AWSControlTower*` stacks, roles, Service Catalog products).

## 7. When to use which (rule of thumb)

- **Organizations only**: small/personal, few accounts, you're happy writing SCPs and managing baselines yourself (or via Terraform).
- **Organizations + Control Tower**: many accounts, need standard guardrails, audited logging, repeatable account vending, drift detection.
- **Control Tower + Terraform**: Control Tower for the landing zone; Account Factory for Terraform (AFT) or custom pipelines for account customization.
- For this lab: either is fine; keep Control Tower only if you want to practice enrollment/controls.
