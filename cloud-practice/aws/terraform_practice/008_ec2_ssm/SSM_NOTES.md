# SSM Session Manager: observations

## 1. Why `whoami` says `ssm-user`

```
$ aws ssm start-session --target i-xxxx --region us-east-1
Starting session with SessionId: programming_user-zb7d...
$ whoami
ssm-user
```

Two separate identities:

- **AWS identity** (`programming_user`): shown in the session ID. IAM and CloudTrail record this, so every action is traceable to a person.
- **OS user** (`ssm-user`): the default Linux account the shell runs as. Created by the SSM agent on first use, same for everyone, has passwordless `sudo` (via `/etc/sudoers.d/ssm-agent-users`).

Changing it: Systems Manager → Session Manager → Preferences → Linux shell profile, or the `SSMSessionRunAs` tag on the IAM principal (Run As). The target OS user must already exist on the instance.

Auditing stays per person even with a shared `ssm-user`: use the session ID + CloudTrail (unlike a shared `.pem`).

## 2. Where the shell starts, and why `cd` failed

```
$ pwd
/var/snap/amazon-ssm-agent/13349
$ cd home
sh: 3: cd: can't cd to home
$ cd /home && ls
ssm-user  ubuntu
$ cd ubuntu
sh: 6: cd: can't cd to ubuntu
```

- **Start directory**: on Ubuntu the SSM agent is a snap, and the session starts in the agent's working directory, not a home directory.
- **`cd home` failed**: relative path; there is no `home` inside the snap dir. Use `/home`.
- **`cd ubuntu` failed**: permissions. `/home/ubuntu` is owned by `ubuntu` with mode 750, so `ssm-user` can't enter. `sh` doesn't say "permission denied". Check with `ls -ld /home/ubuntu`.
- `/home/ssm-user` is empty because nothing has used that account yet.

Handy commands inside a session:

```
bash                 # nicer shell than sh
sudo -i              # become root
sudo ls /home/ubuntu
sudo su - ubuntu     # become the ubuntu user, in its home
```

This lesson has no SSH key, so SSM is the only way in.

## 3. What makes an EC2 reachable via SSM (checklist)

1. **IAM role EC2 can assume**: `aws_iam_role.ssm`, trust policy for `ec2.amazonaws.com`.
2. **`AmazonSSMManagedInstanceCore` policy on the role**: lets the agent register with Systems Manager and open sessions.
3. **Instance profile attached to the instance**: `aws_iam_instance_profile` + `iam_instance_profile = ...` on `aws_instance`. EC2 can't use a role directly, only via a profile.
4. **SSM agent running**: preinstalled on Ubuntu 22.04 and Amazon Linux AMIs (nothing to do); install it yourself on other AMIs.
5. **Outbound access to SSM on 443**: here via the default VPC's internet gateway + public IP + open egress. In a private subnet with no internet, use a NAT gateway or VPC endpoints (`ssm`, `ssmmessages`, `ec2messages`).

Not needed: inbound rules (no port 22), key pair, a public IP for access (ours is only for the outbound path).

The *caller* also needs IAM permission for `ssm:StartSession` (worked here because `programming_user` has broad rights).

### Troubleshooting order if the instance doesn't appear

1. Instance profile attached?
2. Policy on the role?
3. Agent running?
4. Outbound 443 reachable?

Check with `aws ssm describe-instance-information` (instance should be Online).

## 4. What is an instance profile?

A small container that holds **one IAM role** so the role can be attached to an EC2 instance. It carries no permissions itself.

- A role defines *what can be done* (policies). EC2 can't take a role directly; the EC2 API only accepts an instance profile.
- Chain: **instance → instance profile → role → policies**.
- A profile holds exactly one role; an instance has one profile.

### Runtime flow

1. Instance starts with the profile attached.
2. Agent/code asks the instance metadata service (IMDS) for credentials.
3. AWS returns **temporary credentials** for the role, rotated automatically.
4. The SSM agent uses them to call Systems Manager. No access keys stored on the box.

This is the safe way to give an instance AWS permissions (instead of keys in a file).

### In Terraform

```hcl
resource "aws_iam_role" "ssm" { ... }                    # trust: ec2.amazonaws.com

resource "aws_iam_role_policy_attachment" "ssm" { ... }  # what it can do

resource "aws_iam_instance_profile" "ssm" {              # the wrapper
  name = "ec2-ssm-profile"
  role = aws_iam_role.ssm.name
}

resource "aws_instance" "ssm" {
  iam_instance_profile = aws_iam_instance_profile.ssm.name   # attaches it
}
```

### Common confusion

- The **console** hides it: creating an EC2 role there auto-creates a same-named profile.
- **Terraform/CLI** require creating the profile explicitly.
- `iam_instance_profile` takes the **profile name**, not the role name (passing the role name only works by accident when names match).

## 5. Cost note: NAT gateway (us-east-1, approx.; verify current pricing)

- About **$0.045/hr ≈ $33/month per gateway**, even when idle, plus about **$0.045/GB processed**, plus normal data-transfer-out.
- One per AZ for HA (3 AZs ≈ $100/month). Often a top bill item in small accounts.
- Cheaper: skip it (this lesson uses the default VPC + public IP); SSM VPC endpoints (`ssm`, `ssmmessages`, `ec2messages`, ~$0.01/hr/AZ each ≈ $22/month in one AZ); free S3/DynamoDB gateway endpoints; a NAT instance (cheap but self-managed); IPv6 with an egress-only internet gateway (free).
- In labs: avoid, or `terraform destroy` right after.
