# 012 – Step Functions state machine with Terraform

Nothing here is applied automatically. Read, then run it yourself.

What was checked so far *(verified)*: `terraform validate` passes; the rendered ASL JSON passes the AWS validator (`validate-state-machine-definition` returns `OK`, and a deliberately broken copy returns `FAIL: Missing 'Next' target`); both Lambda handlers were run locally. **Not yet applied or executed in AWS.**

## The workflow

```
            ┌──────────────┐   valid?   ┌──────────────┐
 input ───▶ │ ValidateOrder│──── yes ──▶│ ProcessOrder │──▶ OrderCompleted (Succeed)
            └──────┬───────┘            └──────┬───────┘
                   │ no                        │ error after retries
                   ▼                           ▼
            OrderRejected (Fail)         RecordFailure (Pass) ──▶ OrderFailed (Fail)
            (also: ValidateOrder error ──────────────────────▶ RecordFailure)
```

Input: `{"order_id": "o-1", "amount": 25}`. Each state's output is merged into the JSON that flows to the next state (`ResultPath`).

## Files

| File | Purpose |
|---|---|
| `00_versions_and_provider.tf` | aws + archive providers |
| `variables.tf` | region, name prefix |
| `01_lambdas.tf` | zips `src/`, creates the two worker Lambdas + their role |
| `02_state_machine.tf` | state machine IAM role, log group, `aws_sfn_state_machine`, alias `live` |
| `definition.asl.json.tftpl` | **the workflow itself** (ASL JSON template) |
| `src/validate.py`, `src/process.py` | the Lambda code the workflow calls |
| `outputs.tf` | ARNs and a ready-made `start-execution` command |
| `STEP_FUNCTIONS_GUIDE.md` | concepts, update lifecycle, best practices |

## Run it

```
terraform init
terraform plan
terraform apply
```

### Start executions (use the alias ARN)

```
ALIAS=$(terraform output -raw alias_arn)

# 1. Happy path
aws stepfunctions start-execution --region us-east-1 --state-machine-arn $ALIAS \
  --input '{"order_id":"o-1","amount":25}'

# 2. Rejected by validation (negative amount) -> OrderRejected
aws stepfunctions start-execution --region us-east-1 --state-machine-arn $ALIAS \
  --input '{"order_id":"o-2","amount":-5}'

# 3. Transient error -> 3 retries with backoff, then RecordFailure -> OrderFailed
aws stepfunctions start-execution --region us-east-1 --state-machine-arn $ALIAS \
  --input '{"order_id":"o-3","amount":10,"simulate":"transient"}'

# 4. Fatal error -> no retry match, straight to Catch -> OrderFailed
aws stepfunctions start-execution --region us-east-1 --state-machine-arn $ALIAS \
  --input '{"order_id":"o-4","amount":10,"simulate":"fatal"}'
```

### Look at the result

```
# status and output of an execution (use the executionArn printed by start-execution)
aws stepfunctions describe-execution --region us-east-1 --execution-arn <executionArn>

# step-by-step history (which state ran, retries, timings)
aws stepfunctions get-execution-history --region us-east-1 --execution-arn <executionArn> \
  --query 'events[].{id:id,type:type}' --output table
```
Console: Step Functions -> State machines -> `sfn-lab-order-workflow` -> Executions -> click one: you get the **graph view** with each state coloured green/red and the input/output of every step.

### Destroy

`terraform destroy`. Executions history disappears with the state machine.

## Try an update (see GUIDE section 4)

1. Edit `definition.asl.json.tftpl` (e.g. change `MaxAttempts` or add a `Wait` state).
2. `terraform plan`: shows the state machine updating **in place** (and the alias moving to a new version).
3. `terraform apply`, start a new execution, compare the graph.

## Cost (approx.; verify)

Standard workflows are billed per **state transition** (about $0.025 per 1,000 after a monthly free allowance), plus Lambda and CloudWatch Logs. A lab costs cents or less. Idle state machines cost nothing.
