# 016 – VPC endpoints: a private instance with no internet

Checked so far *(verified)*: `terraform validate` passes; the `expect`/`check` helpers behave correctly against a stubbed `aws` CLI. **Not applied in AWS yet**; behaviour below is what to confirm tomorrow.

```
VPC 10.50.0.0/16
└─ private subnet   (no internet gateway, no NAT, no public IP, empty route table)
     private instance
        ├─ Gateway endpoint   ──▶ S3                    (route-table entry, free, with an endpoint POLICY)
        └─ Interface endpoints ──▶ ssm, ssmmessages, ec2messages   (private ENIs + private DNS, billed)
```

## What this teaches

| Concept | Where |
|---|---|
| **Interface endpoint**: private ENI + private IP + private DNS for an AWS service | `aws_vpc_endpoint.ssm` (3 services) |
| **Gateway endpoint** (S3, DynamoDB only): a route to a *prefix list*, no ENI, free | `aws_vpc_endpoint.s3` |
| **Private DNS**: `ssm.us-east-1.amazonaws.com` resolves to a `10.50.x.x` address inside the VPC | test 1 |
| No internet, yet AWS APIs work | tests 2 and 3 |
| **Endpoint policy**: a resource policy on the endpoint (one more layer on top of IAM) | allowed vs denied bucket |
| Why SSM needs **three** endpoints | `for_each` over ssm / ssmmessages / ec2messages |
| VPC needs `enable_dns_hostnames` and `enable_dns_support` for private DNS | `aws_vpc.this` |

The instance role may read **both** buckets, but the S3 endpoint policy allows only one. So when the second one fails, the cause is the endpoint policy, not IAM. The test also shows that **your laptop** can read it (control case).

## Run

```
terraform init
terraform plan
terraform apply          # ~3-5 min (endpoints take a couple of minutes)
./scripts/test_endpoints.sh
```

Expected (confirm tomorrow):

```
PASS  route table has the S3 gateway endpoint route (vpce-...)
PASS  route table has NO internet gateway route
PASS  laptop can list the denied bucket (so it is the endpoint policy that blocks the instance)
PASS  ssm hostname resolves to a PRIVATE IP (interface endpoint, private DNS)
PASS  no internet: curl https://example.com fails
PASS  S3 allowed bucket readable through the gateway endpoint
PASS  S3 denied bucket blocked by the ENDPOINT policy (role allows it)
```

You can also connect interactively: `aws ssm start-session --target $(terraform output -raw instance_id)`, then try `aws s3 ls s3://<bucket>`, `nslookup ssm.us-east-1.amazonaws.com`, `curl -m 5 https://example.com`.

## Experiment: remove the interface endpoints

```
terraform apply -var create_interface_endpoints=false
```
The instance has no route to SSM, so the SSM agent can't register and the test script cannot reach it (it says so and exits). S3 via the gateway endpoint is a separate path and would still work if you could get in. This is the cleanest way to feel why private subnets need interface endpoints (or a NAT gateway) for SSM. Revert with `terraform apply`.

## Gateway vs interface endpoints

| | Gateway | Interface (PrivateLink) |
|---|---|---|
| Services | **S3 and DynamoDB only** | most AWS services + your own / partner services |
| Mechanism | route-table entry to a prefix list | ENI with private IP(s) in your subnet(s) |
| DNS | service name still resolves to public IPs; the route keeps traffic on AWS network | private DNS name resolves to the ENI's private IP |
| Cost | **free** | per hour per AZ + per GB |
| Reachable from on-prem / peered VPC | no | yes (via the ENI IP) |
| Security | endpoint policy + route tables | endpoint policy + security group on the ENI |

## Cost *(approximate; verify)*

Gateway endpoint: free. Interface endpoints: about $0.01 per AZ-hour **each** (3 in one AZ ≈ $0.03/hr ≈ $22/month) plus about $0.01/GB. One t4g.nano. A NAT gateway would cost more (~$0.045/hr) but gives general internet access; endpoints give private access only to the listed services. **Destroy when done**: `terraform destroy`.

## Things to watch (not verified)

- The S3 endpoint policy allows only the lab bucket. That also blocks anything else through the endpoint, such as the Amazon Linux package repositories (hosted in S3), so `dnf install` would fail in this VPC. Fine for this demo; widen the policy for real use.
- In production you often also add a **bucket policy** restricting access to the endpoint (`aws:SourceVpce`). It is not done here because it would lock your own laptop/Terraform out of the bucket.
- If the test can't reach the instance: wait a few minutes after apply (agent registration), and confirm the three interface endpoints are `available` with private DNS enabled.
