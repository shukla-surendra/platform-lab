# Terraform: API Gateway (HTTP API) — Lambda proxy integration

Creates an API Gateway **HTTP API** (v2 — cheaper and simpler than the
older REST API/v1) with a single `AWS_PROXY` Lambda integration, a
catch-all `{proxy+}` route, and CloudWatch access logging. Requires
`lambda/` applied first.

> **Effectively free at this scale** — HTTP APIs bill $1.00 per million
> requests after a Free Tier allowance, versus REST APIs' higher $3.50.

## What it creates

```
CloudWatch Log Group (access logs, /aws/apigateway/<project>)
HTTP API
  $default stage (auto_deploy = true — no manual "deploy API" step, ever)
  Integration -> your Lambda function (AWS_PROXY, payload format 2.0)
  Route: ANY /{proxy+}
  Route: ANY /
Lambda permission (lets THIS specific API invoke the function)
```

## Files
| File | Purpose |
|---|---|
| `versions.tf` | Provider pin + default tags |
| `variables.tf` | Which Lambda function to front, throttling limits |
| `main.tf` | API, stage, integration, routes, Lambda permission |
| `outputs.tf` | The endpoint URL + a `next_steps` runbook |

## Usage
```bash
cd aws/terraform/api-gateway
cp terraform.tfvars.example terraform.tfvars   # paste in lambda/'s outputs
terraform init
terraform apply
curl "$(terraform output -raw api_endpoint)/"
```

## Things to try (mini-labs)
1. `curl` a few different paths (`/foo`, `/foo/bar`, `/`) — all reach the same Lambda function, and inspect `event["rawPath"]`/`event["requestContext"]` inside `lambda/`'s handler to see how the function tells routes apart.
2. `curl -X POST -d '{"x":1}' .../anything` — see the POST body show up inside `event["body"]` (base64-encoded if binary, plain if `isBase64Encoded` is false).
3. Hammer the API past `throttling_rate_limit` (e.g. a quick loop of 30 requests) and watch some come back `429 Too Many Requests`.
4. Tail the access log group and watch `$context.integrationLatency` — this is exactly the number that tells you "is my Lambda slow, or is API Gateway itself the bottleneck."

## Deliberately minimal
- No custom domain / ACM certificate, no JWT/Lambda authorizer (every
  route is public). No request validation — the Lambda function itself
  is responsible for validating its input.
