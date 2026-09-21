# Terraform: importing an existing (manually-created) EC2 instance

Same workflow as `../import-existing-resources/` (S3), applied to an EC2
instance — a more instructive example because EC2 has several `ForceNew`
arguments, so getting the import wrong doesn't just leave a messy diff,
it can queue up a **destructive replace** on your next `apply`.

> **Near-Free-Tier cost** — the worked example is a single `t3.micro`.
> Run `scripts/cleanup.sh` when done so it doesn't keep running.

## What gets imported

Three resources, because a running instance with a stable public IP is
never just `aws_instance` — its security group and its Elastic IP are
separate resources too:

```
aws_security_group.imported   (SSH ingress + all-outbound egress)
aws_instance.imported         (t3.micro, references the SG above)
aws_eip.imported               (associated to the instance -- see "Preserving IP addresses")
```

## One import block per resource

`imports.tf` has three `import { }` blocks — one per resource address.
There is no "import everything attached to this instance" shortcut:
`generate-config-out` only drafts config for addresses you gave it an
`import` block for. Forget the security-group or EIP block and you'd end
up hand-writing that resource from scratch anyway (or, worse, importing
the instance and never noticing its EIP was left outside Terraform's
management — see below).

## Step-by-step

### 1. Create something "by hand" to practice on
```bash
cd scripts
./create-manual-ec2.sh us-east-1a
cd ..
```
Prints `instance_id`, `security_group_id`, `ami_id`, `private_ip`, and
`eip_allocation_id` — copy them exactly into `terraform.tfvars` in the
next step. In real life, skip this step; you already have the instance.

### 2. Point variables at it
```bash
cp terraform.tfvars.example terraform.tfvars
# edit terraform.tfvars with the values the script printed
terraform init
```

### 3. Generate config from the live resources
```bash
terraform plan -generate-config-out=generated.tf
```
Reads both the real security group and the real instance through the AWS
provider and drafts resource blocks for each into `generated.tf`. Doesn't
touch state or `main.tf`.

### 4. Cleaning up generated config
The raw `aws_instance` draft is the noisiest thing `generate-config-out`
produces — it includes every computed attribute the API returns:

```hcl
# __generated__ by Terraform
resource "aws_instance" "imported" {
  ami                                  = "ami-0abc..."
  arn                                  = "arn:aws:ec2:..."          # computed, delete
  instance_state                       = "running"                  # computed, delete
  private_dns                          = "ip-10-0-1-23.ec2.internal" # computed, delete
  public_dns                           = "..."                       # computed, delete
  public_ip                            = "54.x.x.x"                  # computed, delete
  primary_network_interface_id         = "eni-..."                   # computed, delete
  credit_specification { cpu_credits = "standard" }                  # leave at account default, delete
  root_block_device {
    volume_id   = "vol-..."           # computed, delete
    device_name = "/dev/xvda"         # computed, delete
    tags        = {}
    volume_type = "gp3"
    volume_size = 8
    encrypted   = true
  }
  # ... network_interface {} blocks, capacity_reservation_specification, etc.
}
```

`main.tf` in this repo is the cleaned result: only the arguments that
actually describe "what this box is" survive — `ami`, `instance_type`,
`availability_zone`, `subnet_id`, `vpc_security_group_ids`,
`root_block_device` sizing/encryption, `tags`. Everything computed-only is
gone.

### 5. Actually import
```bash
terraform plan    # sanity check first — see the ami warning below
terraform apply   # this is the step that writes state; plan never does
terraform state list
```

### 6. Confirm it's really managed
```bash
terraform plan   # "No changes" — Terraform's view now matches reality
```

## The EC2-specific gotcha: `ami` and `private_ip` are ForceNew

`ami` and `private_ip` (like `availability_zone` and `subnet_id` in most
configurations) are `ForceNew` arguments on `aws_instance`: if the value in
your `.tf` doesn't **exactly** match the instance's real values, Terraform
doesn't show a benign diff — it shows `# forces replacement`, meaning the
very next `apply` would terminate the real instance and launch a new one.
That's the opposite of what importing existing infrastructure is supposed
to do.

Always get `ami_id`/`private_ip` from the generated config or `aws ec2
describe-instances ... --query 'Reservations[0].Instances[0].[ImageId,PrivateIpAddress]'`,
never retyped from memory, and always read `terraform plan` output fully
before `apply` — "No changes" is the only acceptable result of an import
plan.

## Preserving IP addresses

There are three different "the instance's IP" concepts in EC2/Terraform,
and only one of them is actually preservable:

| | Ephemeral public IP | Private IP | Elastic IP |
|---|---|---|---|
| Resource | `aws_instance.public_ip` (computed only) | `aws_instance.private_ip` (settable, **ForceNew**) | `aws_eip` (standalone resource) |
| Survives stop/start? | No — reassigned on every start | Yes | Yes |
| Survives instance replacement (new `ami`, etc.)? | No — new instance, new IP | No — new instance, new private IP | **Yes** — Terraform just re-associates the same EIP |
| Can Terraform "preserve" it on import? | No — nothing to set, it's read-only | Only by pinning `private_ip` to the current value (see ForceNew warning above) | Yes — this is the actual mechanism |

**The answer to "how do I preserve an EC2 instance's IP through
Terraform":** attach an Elastic IP and manage it as its own resource
(`aws_eip.imported` in `main.tf`), with `instance =
aws_instance.imported.id` to associate it. Because the EIP's identity
(its allocation, and therefore its public IP) is independent of the
instance's identity, replacing the instance only updates the
`instance` attribute on the existing `aws_eip` resource — the IP address
itself never changes. Without an EIP, a public IP is fundamentally
ephemeral and no Terraform configuration can make it otherwise.

If the instance you're importing does NOT already have an EIP and you
don't want to allocate a new one, delete the `aws_eip.imported` block from
`main.tf`, its `import` block from `imports.tf`, and the `eip_allocation_id`
variable — the module works fine with just the SG + instance.

## Files
| File | Purpose |
|---|---|
| `imports.tf` | The three `import` blocks (SG, instance, EIP) |
| `main.tf` | Cleaned-up resource blocks matching the real instance + SG + EIP |
| `variables.tf` | `instance_id`, `security_group_id`, `ami_id`, `private_ip`, `eip_allocation_id` of the pre-existing resources |
| `outputs.tf` | IDs, ephemeral vs. Elastic IP, + a `next_steps` runbook |
| `versions.tf` | Terraform >= 1.5 pin (required for `import` blocks) |
| `scripts/create-manual-ec2.sh` | Creates a practice instance + SG + EIP out-of-band (run yourself) |
| `scripts/cleanup.sh` | Removes from state AND terminates the instance / releases the EIP / deletes the SG |

## Gotchas
1. **`ami` and `private_ip` are ForceNew** — see above; the ones that
   actually bite people.
2. **One import block per resource**, not per "thing a human would call
   one unit of infra" — the SG and EIP each need their own block even
   though they only exist because of the instance.
3. **`generate-config-out` refuses to overwrite an existing file** —
   delete/rename a previous `generated.tf` before re-running it.
4. **`public_ip`/`public_dns` are computed, not arguments** — don't try to
   set them in `main.tf`; they show up in `generated.tf` for visibility
   only and must be deleted, same as in the S3 example. The `aws_eip`
   resource's own `public_ip` is likewise computed — you get it as an
   output, you don't set it.
5. **An EIP not imported is an EIP Terraform doesn't know exists** — if
   you import the instance but skip the EIP, Terraform never touches it
   (fine), but it also won't show up in `terraform state list`, won't be
   destroyed by `terraform destroy`, and will keep costing money if
   disassociated (AWS bills unattached EIPs). Import it deliberately or
   release it deliberately — don't leave it in limbo.
6. **Terminating the instance destroys the root EBS volume too** (default
   `delete_on_termination = true`), same as any other Terraform-managed
   instance — `scripts/cleanup.sh` relies on that. Releasing the EIP is a
   separate step; an instance being terminated does not auto-release its
   associated EIP.

## Deliberately minimal
- No IAM instance profile / SSM access (compare `../ec2/main.tf`, which
  has both) — kept minimal so the import mechanics aren't buried under
  unrelated resource types.
- No `moved` blocks — renaming an already-managed resource is a different
  operation from importing an unmanaged one.
