# Terraform: Lambda — function, IAM role, log group, and a public URL

Creates a Lambda function from the Python source in `src/index.py`,
zipped automatically by the `hashicorp/archive` provider (no manual zip
step, no local-exec). Exposes a public **Function URL** by default —
the fastest way to hit it over HTTPS with zero API Gateway setup. Pairs
with `api-gateway/` when you want a real REST/HTTP API in front of it
instead (custom domains, request validation, usage plans, etc.).

> **Effectively free at this scale** — Lambda's Free Tier is 1M
> requests + 400,000 GB-seconds/month, forever (not just 12 months).

## What it creates

```
CloudWatch Log Group (/aws/lambda/<project>)
IAM Role (CreateLogStream/PutLogEvents only — least privilege)
Lambda Function (Python 3.12, zipped from src/ via archive_file)
Function URL (public HTTPS, optional)
```

## Files
| File | Purpose |
|---|---|
| `versions.tf` | Provider pins (aws + archive) + default tags |
| `variables.tf` | Runtime, sizing, environment variables, Function URL toggle |
| `src/index.py` | The actual function code — edit this |
| `main.tf` | Zip packaging, log group, IAM role, function, Function URL |
| `outputs.tf` | ARNs + Function URL + a `next_steps` runbook |

## Usage
```bash
cd aws/terraform/lambda
cp terraform.tfvars.example terraform.tfvars
terraform init
terraform apply
curl "$(terraform output -raw function_url)"
terraform destroy
```

## Things to try (mini-labs)
1. `apply`, then `curl` the Function URL — see your event/timestamp echoed back as JSON.
2. Edit `src/index.py` (e.g. add a field to the response dict) and `apply` again — Terraform detects the content hash changed and deploys a new version automatically, no version bump needed by hand.
3. `aws lambda invoke --payload '{"name":"test"}' ...` and inspect how `event` shows up inside the handler — this is how you'll wire real input from API Gateway/EventBridge/S3 triggers later.
4. Drop `memory_size` to 128 vs raise it to 1024 and compare `aws lambda invoke`'s `Duration`/`Billed Duration` in the response — more memory also means more CPU in Lambda, often making a CPU-bound function finish faster for a similar total cost.

## Deliberately minimal
- `authorization_type = "NONE"` on the Function URL means literally
  anyone with the URL can invoke it — fine for a lab, never for
  anything holding real data. Switch to `"AWS_IAM"` and sign requests
  with SigV4, or put it behind `api-gateway/` with a proper authorizer,
  for real usage.
- Task role has zero AWS permissions beyond logging — add
  `aws_iam_role_policy` statements to `aws_iam_role.lambda` as your
  function actually needs to call other services.
