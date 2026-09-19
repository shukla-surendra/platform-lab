# Debug notes — SSH wouldn't connect

## Symptom
```
$ terraform output instance_ip
│ Warning: No outputs found
$ terraform output -raw private_key > my-key.pem
$ chmod 400 my-key.pem
$ ssh -i my-key.pem ec2-user@100.59.36.55
^C
$ ssh -i my-key.pem ubunutu@100.59.36.55   # typo, then another typo
^C
```

## Root causes — three separate bugs, all in `main.tf`

**1. `output "instance_ip"` referenced a resource that doesn't exist.**
```hcl
output "instance_ip" {
  value = aws_instance.server.public_ip   # no resource named "server" anywhere
}
```
The actual resource is `aws_instance.example_instance`. A bad reference in
ANY output makes Terraform unable to evaluate outputs AT ALL — that's why
`terraform output instance_ip` said "No outputs found" instead of a more
specific error; the CLI's `output` command wasn't reporting on `instance_ip`
specifically, it was failing to load the config's outputs in general.
`terraform validate` shows this precisely:
```
Error: Reference to undeclared resource
  on main.tf line 23, in output "instance_ip":
  23:   value = aws_instance.server.public_ip
```

**2. There was no `output "private_key"` block at all.**
`terraform output -raw private_key > my-key.pem` had nothing to print for
an output that didn't exist. The `>` redirect still creates the file — just
empty. `my-key.pem` was 0 bytes. Every `ssh -i my-key.pem` attempt after
that was doomed regardless of anything else, because the key file had no
key in it.

**3. The instance had no security group of its own.**
```hcl
resource "aws_instance" "example_instance" {
  ami           = "ami-0b6d9d3d33ba97d99"
  instance_type = "t2.micro"
  key_name      = aws_key_pair.ec2.key_name
  # no vpc_security_group_ids -> AWS attaches the VPC's "default" SG
}
```
The default security group's only inbound rule allows traffic **from other
resources in that same security group** — nothing from the internet. Port
22 was never reachable from outside AWS at all. This is why every `ssh`
attempt just hung (`^C` to escape it) instead of failing fast with
something like "Permission denied" — the TCP handshake itself never
completed, so SSH never even got to the authentication step where the
empty key (bug #2) would have mattered.

**Bonus, not a bug but worth knowing:** the AMI (`ami-0b6d9d3d33ba97d99`) is
**Ubuntu 26.04**, not Amazon Linux — confirmed via
`aws ec2 describe-images`. The correct SSH user is `ubuntu`, not
`ec2-user` (tried first) or `ubunutu`/`ubunut` (typos on the 2nd/3rd
tries — the right username was attempted, just misspelled).

## Fixes applied

- Added `aws_security_group.ssh`: allows port 22 from `14.143.254.170/32`
  (the IP this was debugged from — update it if your IP changes, e.g. via
  `terraform apply -var` or just editing the CIDR and re-`apply`ing) and
  attached it to the instance via `vpc_security_group_ids`. This is an
  **in-place update** in AWS (`ModifyInstanceAttribute`), not a replacement
  — confirmed via `terraform plan`: `1 to add, 1 to change, 0 to destroy`,
  no instance recreation, no new IP, no lost work.
- Fixed `output "instance_ip"` to reference `aws_instance.example_instance`.
- Added `output "private_key"` (marked `sensitive`) so
  `terraform output -raw private_key` actually has something to print.

## Verified after the fix
```bash
$ terraform apply   # 1 added (security group), 1 changed (instance's SG attachment)
$ rm my-key.pem
$ terraform output -raw private_key > my-key.pem && chmod 400 my-key.pem
$ head -1 my-key.pem
-----BEGIN RSA PRIVATE KEY-----          # real key now, not empty (3243 bytes, was 0)
$ aws ec2 describe-security-groups --group-ids sg-0df77bb21cbd07cac \
    --query 'SecurityGroups[0].IpPermissions'
# confirms: tcp/22 from 14.143.254.170/32
```

**Not verified from this session:** the actual `ssh` connection. This
sandboxed environment can't make outbound TCP connections on port 22 at
all (confirmed separately — even `ssh` to `github.com:22`, a host that's
always reachable, hangs identically here). That's a restriction of *this
environment*, unrelated to the EC2 instance. Run this from your own
terminal, where the earlier attempts were actually made:
```bash
ssh -i my-key.pem ubuntu@100.59.36.55
```

## If it still doesn't connect
1. **Your IP changed.** `curl https://checkip.amazonaws.com` and compare
   against the CIDR in `aws_security_group.ssh` — home/mobile IPs often
   aren't static. Update the CIDR and `terraform apply` again (a security
   group rule change is instant, no instance downtime).
2. **You're on a different network than the one that was debugged from**
   (VPN, different wifi, tethering) — same fix as above.
3. **Still nothing:** `nc -vz -G 5 100.59.36.55 22` (macOS) tells you fast
   whether it's a network/SG problem (connection refused/timeout) vs. an
   auth problem (connects, then SSH itself rejects the key).
