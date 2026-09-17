# Terraform: CloudWatch — alarms + dashboard for whatever you already applied

An "observability layer" module: every alarm and every dashboard widget
here is **optional and additive** — leave `asg_name`/`lambda_function_name`/
`alb_arn_suffix` blank and this module creates just an (empty) alarm topic
and dashboard; fill in one or more from other modules' outputs and the
matching alarm + widget appear.

> **Effectively free** — CloudWatch's Free Tier covers 10 alarms and 3
> dashboards/month forever; this module creates at most 3 alarms + 1
> dashboard.

## What it creates

```
SNS Topic (alarm notifications) + optional email subscription
Alarm: ASG average CPU > threshold        (only if asg_name is set)
Alarm: Lambda error count >= threshold    (only if lambda_function_name is set)
Alarm: ALB 5xx count >= threshold         (only if alb_arn_suffix is set)
CloudWatch Dashboard (one widget per alarm that's actually wired in)
```

## Files
| File | Purpose |
|---|---|
| `versions.tf` | Provider pin + default tags |
| `variables.tf` | Optional per-resource watch targets + thresholds |
| `main.tf` | Topic, conditional alarms, conditional dashboard widgets |
| `outputs.tf` | Dashboard URL + a `next_steps` runbook |

## Usage
```bash
cd aws/terraform/cloudwatch
cp terraform.tfvars.example terraform.tfvars   # fill in whichever outputs you have
terraform init
terraform apply
terraform output dashboard_url
```

## Getting `alb_arn_suffix`
CloudWatch's ALB metrics are dimensioned by a suffix of the load
balancer's ARN, not the ARN itself:
```bash
# full ARN:   arn:aws:elasticloadbalancing:us-east-1:123456789012:loadbalancer/app/my-alb/abc123
# suffix:                                                           app/my-alb/abc123
terraform -chdir=../alb output -raw dns_name   # then look up the ARN via:
aws elbv2 describe-load-balancers --names <name> --query 'LoadBalancers[0].LoadBalancerArn'
```

## Things to try (mini-labs)
1. Wire in `lambda_function_name`, `apply`, then invoke the function with a payload that makes it raise an exception a few times — watch the alarm state move `OK` → `ALARM` in `describe-alarms` (and by email, if `alarm_email` is confirmed).
2. Open the dashboard URL — watch the widgets actually update as you generate traffic against whichever resources you wired in.
3. Wire in all three (`asg_name`, `lambda_function_name`, `alb_arn_suffix`) and re-`apply` — see the dashboard grow a widget for each, laid out side by side.
4. Lower a threshold artificially low (e.g. `lambda_error_alarm_threshold = 0`... note CloudWatch alarms need `>`/`>=` a real threshold, so try `1` against a function that never errors) and watch it stay `OK` — a good sanity check that the alarm is actually watching the metric you think it is.

## Deliberately minimal
- Simple static thresholds, not anomaly detection (`aws_cloudwatch_metric_alarm`
  supports an `ANOMALY_DETECTION_BAND` alternative — a good next module
  to try once static thresholds feel familiar). No composite alarms
  (`aws_cloudwatch_composite_alarm`) combining several of these into one
  "is anything wrong" signal.
