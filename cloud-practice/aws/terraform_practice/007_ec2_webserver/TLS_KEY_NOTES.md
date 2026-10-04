# Where does `tls_private_key` keep the keys?

```hcl
resource "tls_private_key" "example" {
  algorithm = "ED25519"
}
```

- Generated **in memory** during `terraform apply`. No key files are written.
- Both keys are stored in **`terraform.tfstate`**, private key in plaintext.
- **Public key** → sent to AWS by `aws_key_pair` (`public_key_openssh`).
- **Private key** → `private_key_openssh`; only in state unless you export it.

## Getting the private key out

```hcl
output "private_key" {
  value     = tls_private_key.example.private_key_openssh
  sensitive = true
}
```

```
terraform output -raw private_key > key.pem && chmod 600 key.pem
ssh -i key.pem ubuntu@<public_ip>
```

(Or use a `local_file` resource with `file_permission = "0600"`.)

## Cautions

- Never commit `*.tfstate` or `*.pem`.
- Learning shortcut only. Real setups: `ssh-keygen` locally and pass just the public key to `aws_key_pair`, so no private key lands in state.
- This lesson (007) uses no key and opens no port 22.

# Best practice for SSH access to EC2 (best → worst)

1. **No SSH keys: use SSM Session Manager**
   - Attach an IAM role with `AmazonSSMManagedInstanceCore` to the instance.
   - Connect: `aws ssm start-session --target <instance-id>`
   - No port 22, no key pair, no public IP needed for access. Controlled by IAM, logged in CloudTrail. AWS-recommended.

2. **SSH with a key generated outside Terraform**
   ```
   ssh-keygen -t ed25519 -f ~/.ssh/my-aws-key
   ```
   ```hcl
   resource "aws_key_pair" "this" {
     key_name   = "my-key"
     public_key = file("~/.ssh/my-aws-key.pub")
   }
   ```
   - Only the public key enters Terraform/state; the private key stays on your machine.
   - Restrict port 22 to your own IP (`x.x.x.x/32`), never `0.0.0.0/0`.

3. **`tls_private_key`**: throwaway labs only (private key sits in plaintext in state).

## Other good habits

- Remote state backend (S3, encrypted, with locking). See `000_bootstrap_state_bucket`.
- `.gitignore`: `*.tfstate*`, `*.pem`, `.terraform/`.
- Require IMDSv2: `metadata_options { http_tokens = "required" }`.
- Real web servers: ALB in front, instance in a private subnet, no public IP.

## Possible next lesson

008: SSM role + instance profile so the 007 server is reachable without SSH.

# Teams: never share a private key

The private key is your identity. Anyone holding it can log in as you, and you can't tell who used it. Share the **public** key freely; the private key never leaves its owner.

## How teams should do it

1. **SSM Session Manager (best)**: no keys at all. Each person logs in with their own IAM/SSO identity; access is granted/revoked via IAM; every session is logged per person in CloudTrail and can be recorded to S3/CloudWatch.
2. **One key pair per person**: each runs `ssh-keygen` locally; the server trusts everyone's public key (one line each in `~/.ssh/authorized_keys`). Revoke = remove that line. Caveat: EC2 `key_name` injects only one key at launch, so you'd manage `authorized_keys` yourself (user_data/config management), which gets messy.
3. **EC2 Instance Connect**: pushes a temporary public key (~60s) gated by IAM. Per-person keys without managing `authorized_keys`.

## Reality check: the shared `.pem` anti-pattern

Very common, because EC2 takes one key pair at launch, it works instantly, and nobody revisits it.

Costs:
- **No audit trail**: logs show "the shared key" logged in, not who.
- **Painful revoke**: removing one person means rotating the key on every server; usually skipped, so ex-teammates keep access.
- **Big blast radius**: the file travels via Slack/email/laptops; one leak exposes every server using it.
- **Compliance**: SOC 2 / ISO 27001 / PCI expect individual accountability.

## If your team already does this

1. Raise it as a risk and propose SSM Session Manager (IAM role on instances + IAM/SSO for people).
2. Migrate gradually: enable SSM, confirm everyone can connect, close port 22, retire the `.pem`.
3. Meanwhile: rotate the key when someone leaves; keep it out of chat and git; store it in a password/secrets manager.

Lesson 008 (SSM) is a working example to show the team.

# Secrets in Terraform state

`tls_private_key` stores the **private key in plaintext in state**. This is not best practice for anything beyond a lab.

## Why it's a problem

- Anyone who can read state can read the key. `sensitive = true` only hides CLI output, not the state file.
- Local `terraform.tfstate` gets copied, backed up, sometimes committed to git.
- Even with an S3 backend, everyone/every pipeline with bucket read access effectively holds the key.
- Deleting the resource doesn't help: old state versions in S3 still contain it.

## What to do instead

1. **Keep secrets out of state**: generate keys with `ssh-keygen` and pass only the public key via `file()`, or use SSM and no keys at all.
2. **If a secret must be in state**: encrypted S3 backend with KMS, tight bucket IAM, versioning + lifecycle rules, no broad read access.
3. **Other secrets (DB passwords etc.)**: create in Secrets Manager / SSM Parameter Store and let the app read at runtime. Terraform 1.10+ has ephemeral values and write-only arguments to avoid state storage (provider/resource support varies; check docs).

## Then why does `tls_private_key` exist?

It's a convenience, and the provider docs warn about the state exposure.

- **Demos/labs**: working EC2 + SSH from one `apply`.
- **Dev/test**: throwaway infra where a leak doesn't matter.
- **Self-signed certs / internal CAs**: key + CSR + cert for dev clusters, mTLS in test, bootstrapping before a real CA exists.
- **Wiring resources**: when another resource needs a key generated in the same run.

State holds it because Terraform records every attribute of every resource (needed for drift detection and passing values between resources), with no concept of "don't store this". Ephemeral/write-only features came later; `tls_private_key` predates them.

Fine for a lab you destroy afterward. For production use SSM, or generate keys outside Terraform.
