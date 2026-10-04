# AWS Config: what it does and what it costs

Prices are approximate (us-east-1) and written from memory; verify on the AWS Config pricing page.

## What it does

Records the configuration of your AWS resources over time and evaluates it against rules.

- **Inventory**: settings of EC2, security groups, S3, IAM, RDS, etc. Each recorded state is a **configuration item (CI)**.
- **History**: timeline of changes ("this security group opened port 22 on Tuesday") plus relationships between resources.
- **Rules**: managed or custom rules mark resources `COMPLIANT` / `NON_COMPLIANT` (e.g. no public S3 buckets, EBS encrypted, RDS backups on).
- **Remediation**: can trigger automatic fixes via SSM Automation.
- **Conformance packs / aggregators**: rule bundles; a view across accounts and regions.
- **Audit evidence**: compliance trail. Control Tower's *detective* controls are Config rules.

It reports (and can remediate); it does **not** block actions. Blocking is SCPs / preventive controls.

## Cost

| Item | ~Price |
|---|---|
| Configuration item, continuous recording | $0.003 each |
| Configuration item, periodic (daily) recording | $0.012 each |
| Rule evaluation | $0.001 each (first 100k/month; cheaper after) |
| Conformance pack evaluation | $0.0012 each (first 1M) |
| S3 bucket for delivery files, SNS, etc. | normal usage rates |
| Free tier | None |

## Where costs surprise people

- Continuous recording of everything: every change = a CI. Churny resources (EC2, ENIs, Lambda) add up; a busy account can reach tens of dollars a month.
- Rules × resources × accounts × regions multiplies evaluations quickly.
- Recording in regions you don't use.

## Keeping it cheap (small lab)

- Record only the resource types you need.
- Use daily (periodic) recording where possible.
- Limit regions; start with a handful of rules.
- A few dozen resources + a few rules is typically a few dollars a month or less.

## In this environment

Config is **off** (no recorders, no rules), which is why the Control Tower landing zone costs almost nothing. Enabling Config-based controls or the landing-zone Config option would turn recording on and start charges. See `ORGANIZATIONS_VS_CONTROL_TOWER.md`.
