# 008 – EC2 with SSM Session Manager (no SSH, no key pair)

Connect to an instance with no port 22, no key pair, and no inbound rules. Access is controlled by IAM.

Pieces: IAM role → `AmazonSSMManagedInstanceCore` policy → instance profile → EC2.

```
terraform init
terraform apply
# wait 1-2 min for the agent to register, then:
aws ssm start-session --target $(terraform output -raw instance_id) --region us-east-1
terraform destroy
```

Requirements on your machine: AWS CLI v2 + the Session Manager plugin
(`brew install --cask session-manager-plugin`).

Troubleshooting: if `start-session` says the target isn't connected, check
`aws ssm describe-instance-information` — the instance should be listed as Online.
