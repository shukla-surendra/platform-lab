# Step Functions with Terraform: concepts, update lifecycle, best practices

Marked *(verified)* = checked in this lab; everything else is general knowledge, so confirm against current AWS/Terraform docs.

## 1. What Step Functions is

A managed **workflow orchestrator**. You describe a flow as a **state machine**; AWS runs it, keeps its state, retries steps, waits, branches, and records a full history.

- It **does not run your code**. Each *Task* state **calls** something: Lambda, SQS, SNS, DynamoDB, ECS, Glue, another state machine, 200+ AWS APIs (SDK integrations).
- Data flows as **JSON** from state to state.
- You get a visual graph of every execution.

Why not just chain Lambdas in code? Retries/timeouts/branching/error handling/waiting are declarative and visible, not buried in code; long waits cost nothing; each step is independently observable.

### State types

| Type | Use |
|---|---|
| `Task` | Do work (call a Lambda / AWS API) |
| `Choice` | Branch on data (if/else) |
| `Parallel` | Run branches at the same time |
| `Map` | Run the same steps for each item in a list |
| `Wait` | Pause (seconds or until a time) |
| `Pass` | Pass/transform data, no work (also useful as a placeholder) |
| `Succeed` / `Fail` | End states |

### Workflow types

| | STANDARD | EXPRESS |
|---|---|---|
| Duration | up to 1 year | up to 5 minutes |
| Semantics | exactly-once, full history | at-least-once |
| Cost model | per state transition | per request + duration |
| Use | order processing, approvals, long jobs | high-volume event processing |

## 2. How the workflow definition and Terraform "fit together"

*(Clarification on your question: Step Functions is a fully released service, not a developer preview. The point you are describing is that the **workflow logic is a developer concern (ASL JSON)** while the **AWS resources around it are an infra concern (Terraform)**.)*

Terraform does **not** understand the workflow. It treats the definition as an opaque string:

```hcl
resource "aws_sfn_state_machine" "order" {
  name       = "sfn-lab-order-workflow"
  role_arn   = aws_iam_role.sfn.arn
  definition = templatefile("${path.module}/definition.asl.json.tftpl", {
    validate_arn = aws_lambda_function.validate.arn
    process_arn  = aws_lambda_function.process.arn
  })
}
```

Division of labour:

| Lives in the ASL file (developer) | Lives in Terraform (infra) |
|---|---|
| States, order, branching | State machine resource, type, logging, tracing |
| Retry/Catch rules, timeouts | IAM role and least-privilege permissions |
| Which input/output paths to use | Lambda functions, queues, log groups |
| | **The real ARNs**, injected into the ASL via `templatefile()` |

`templatefile` is the glue: the JSON stays a readable file (and can be opened in Workflow Studio), while Terraform fills in `${validate_arn}` etc. so the file never hard-codes account-specific ARNs.

### Ways to supply the definition

| Approach | Pros | Cons |
|---|---|---|
| **`templatefile()` + separate `.asl.json.tftpl`** (this lab) | Readable, diffable, validator-friendly | Template variables to maintain |
| `jsonencode({...})` inline HCL | Can reference resources directly, typo-safe syntax | Workflow buried in HCL; harder to read/share with non-Terraform people |
| Plain `file()` JSON (no templating) | Simplest | Needs hard-coded ARNs, or use Lambda aliases/names resolved at runtime |
| Authored in **Workflow Studio**, exported JSON, committed | Visual editing | Must keep the committed file as the source of truth, or drift appears |
| CDK / SAM / Serverless | Higher-level abstractions | Different toolchain |

*(verified)* In this lab the rendered ASL passes the AWS validator, and a broken copy is rejected with a clear message.

## 3. First deployment: what `terraform apply` does, in dependency order

1. Zip `src/` and create the two Lambdas + their role.
2. Create the state machine IAM role and permissions (invoke those two Lambdas, log delivery).
3. Create the CloudWatch log group.
4. Render the template with the Lambda ARNs and **create the state machine** (`publish = true` also publishes **version 1**).
5. Create the alias `live` pointing to version 1.

Nothing runs until you start an **execution** (`start-execution`). Executions are runtime events, not Terraform resources.

## 4. Updating the workflow after the first deploy

You edit `definition.asl.json.tftpl`, then run `terraform apply`. What happens:

1. `templatefile()` renders a new definition string. `terraform plan` shows `aws_sfn_state_machine.order` **updating in place** (`~ definition`).
2. Terraform calls `UpdateStateMachine`. The ARN does **not** change; the state machine is not recreated.
3. With `publish = true`, a **new numbered version** is created.
4. The alias `live` moves to the new version (weight 100).
5. **New executions** use the new definition.
6. **Executions already running keep the definition they started with** (Step Functions behaviour: in-flight executions are not changed by an update). *(general knowledge; not tested here)*

What triggers a change in Terraform's eyes: any change to the **rendered** string (including a changed Lambda ARN). Pure formatting changes in the template can still produce a diff if the rendered text differs, so keep the file stable.

### Who deploys the update: the two models (same idea as for Lambda code)

| | Model 1: Terraform owns it (this lab) | Model 2: pipeline owns the workflow |
|---|---|---|
| Edit workflow | `terraform apply` | CI runs `aws stepfunctions update-state-machine --publish` |
| Good for | Learning, small teams, infra and flow change together | Frequent workflow changes by a separate team |
| Catch | Every flow tweak needs Terraform + broad IAM | Add `lifecycle { ignore_changes = [definition] }` in Terraform or it reverts the pipeline's change |

Most teams keep **Terraform owning the state machine**, because the definition is tightly coupled to ARNs and IAM; the *Lambda code* is the part usually split off to a pipeline.

### Versions, aliases and rollback

- `publish = true` -> every definition change becomes an **immutable version**.
- Start executions on the **alias** (`live`), never on a raw version.
- **Rollback** = point the alias back to an older version (via Terraform by reverting the change, or `aws stepfunctions update-state-machine-alias`).
- The alias can also **split traffic** (e.g. 90% old / 10% new) for a gradual rollout, using `routing_configuration` with two entries. *(Supported by the resource; not exercised here.)*

## 5. Retries, catches and error names

Key point: **errors are matched by name** (`ErrorEquals`).

- Python exception class name = error name. `process.py` raises `TransientError`, which `ProcessOrder` retries; a `ValueError` matches no retry, so it goes to `Catch`.
- Built-in names: `States.ALL` (everything), `States.Timeout`, `States.TaskFailed`, `States.Runtime`.
- Lambda service-level errors (`Lambda.ServiceException`, `Lambda.TooManyRequestsException`, ...) should be retried for every Lambda task; they are transient.
- `Retry` runs first (with `IntervalSeconds`, `BackoffRate`, `MaxAttempts`); if it is exhausted or no rule matches, `Catch` runs.
- `ResultPath: "$.error"` in a Catch **keeps the original input** and adds the error beside it, instead of replacing the input with the error.

Expected behaviour for the four test inputs in `README.md`:

| Input | Path |
|---|---|
| valid order | Validate -> IsValid -> Process -> `OrderCompleted` |
| `amount: -5` | Validate -> IsValid(false) -> `OrderRejected` |
| `simulate: transient` | Process fails, retried 3x with backoff -> Catch -> `RecordFailure` -> `OrderFailed` |
| `simulate: fatal` | Process fails once, no retry rule matches -> Catch -> `OrderFailed` |

(Expected from the design and ASL semantics; not executed yet.)

## 6. Best practices

**Definition**
- Keep the workflow in its own **ASL file** (`.tftpl`), not buried in HCL; validate it in CI with `aws stepfunctions validate-state-machine-definition`.
- Always set **`TimeoutSeconds`** on Tasks that call external things; a stuck task otherwise waits as long as the service allows.
- Add **`Retry` for service-level errors** and **`Catch` with a failure path** on every Task; never leave an unhandled failure.
- Use **`ResultPath`** deliberately so you don't overwrite the whole input.
- Keep state payloads small (limit ~256 KB). Store large data in S3/DynamoDB and pass references.
- Make Lambda steps **idempotent**; retries mean a step can run more than once.
- Prefer **SDK/service integrations** (SQS, SNS, DynamoDB directly from the workflow) over writing "glue" Lambdas.
- Keep Lambdas **small and single-purpose**; put branching/looping in the state machine.
- Use **Map** for per-item work and **Parallel** for independent branches.

**Terraform / IAM**
- **Least privilege**: the role may invoke only the named Lambdas (as in `02_state_machine.tf`), not `lambda:*` on `*`.
- Log-delivery actions need `Resource: "*"` (AWS limitation); keep everything else scoped.
- Use **`templatefile()`** rather than hard-coding ARNs.
- Use **`publish = true` + an alias** and start executions on the alias.
- Add `depends_on` the role policy so the state machine isn't created before its permissions.
- Tag everything (`default_tags`), name resources with a project prefix.

**Operations**
- **Logging**: enable `level = ALL` while learning, but `include_execution_data = true` writes inputs/outputs to logs; **turn it off or use `ERROR` for sensitive data**. Set log retention.
- **X-Ray tracing** (`tracing_configuration.enabled = true` + X-Ray permissions) for latency analysis.
- **Alarms**: `ExecutionsFailed`, `ExecutionsTimedOut`, `ExecutionThrottled` CloudWatch metrics -> SNS.
- Standard for long/auditable/exactly-once; **Express** for high-volume short work (cheaper per run).
- Set a **workflow-level `TimeoutSeconds`** so nothing runs forever.
- For human approval or async callbacks use the **`.waitForTaskToken`** pattern.
- Don't write secrets into the definition or input; reference Secrets Manager/SSM from the called services.

**Cost**
- Standard is billed per **state transition**; every state, retry and Wait entry counts. Fewer, bigger steps cost less, but don't sacrifice clarity blindly.
- Polling loops (`Wait` + `Choice` + Task) multiply transitions; prefer callbacks/events.

## 7. Common problems

| Symptom | Likely cause |
|---|---|
| `AccessDeniedException` calling a Lambda | State machine role lacks `lambda:InvokeFunction` on that ARN (also `:*` for aliases/versions) |
| Definition rejected on apply | ASL error (bad `Next`, missing `StartAt`); run the validator first |
| Logging config error | Log group ARN needs the `:*` suffix; role needs the log-delivery permissions |
| `plan` shows a diff after only reformatting | Rendered string changed; keep the template stable |
| Update didn't affect a running execution | By design; in-flight executions keep their original definition |
| Pipeline's workflow change got reverted | Model 2 without `ignore_changes = [definition]` |
| Execution input missing a field | Check `Parameters`/`InputPath`/`ResultPath` along the path |

## 8. Follow-up lessons

1. Replace `RecordFailure` with a direct **SNS publish** integration.
2. Add a **Map** state to process a list of orders, then a **Parallel** step.
3. Add a gradual alias rollout (two `routing_configuration` entries) and roll back.
4. Trigger the workflow from **SQS** (via EventBridge Pipes or a small Lambda) and from **EventBridge**, to connect it with lesson 011.
5. Add **CloudWatch alarms** on failed executions.

## 9. A definition change: infra pipeline or code pipeline?

**Infra pipeline (Terraform).** The definition depends on things Terraform manages: Lambda ARNs injected by `templatefile()`, the IAM role, log group and alias. The code pipeline's narrow permissions (S3 upload + `lambda:UpdateFunctionCode`) can't update a state machine anyway.

| What changed | Pipeline |
|---|---|
| `definition.asl.json.tftpl` (steps, retries, branching) | **Infra**: `plan` -> review -> `apply` |
| `src/*.py` (code a step runs) | **Code** pipeline (Model 2) or `terraform apply` (Model 1) |
| Both together (e.g. new step calling a new/changed Lambda) | Both, in a safe order (below) |
| Timeout, memory, IAM, logging, alias settings | **Infra** |

What the infra pipeline does for a definition change:
1. `plan` shows `aws_sfn_state_machine.order` updating **in place** (`~ definition`) and the alias moving to a new version.
2. `apply` updates the state machine (ARN unchanged), publishes a new version, moves `live`.
3. New executions use the new definition; running executions keep the one they started with *(general knowledge, not tested here)*.
4. Rollback = revert and re-apply, or move the alias back.

### When definition and code change together

The two pipelines don't deploy at the same instant, so make each change **backward-compatible** so either order works:

- **Adding a field or step**: ship the code first (accepting old and new input), then the definition that uses it.
- **Removing or renaming something**: ship the new definition first (stop using the old behaviour), then remove it from the code.
- If a change cannot be made backward-compatible, deploy in one pipeline run (Model 1) or version the Lambda and point the definition at the new version/alias.

Alternative: let a pipeline own the definition (`aws stepfunctions update-state-machine --publish`); then add `lifecycle { ignore_changes = [definition] }` in Terraform, or the next `terraform apply` reverts it. Less common, because ARNs and IAM tie the definition to Terraform.

## 10. Where should the state machine template live: infra repo or developer code repo?

There is no single rule; it is an ownership decision. The principle: **keep together what changes together and who owns it.** The workflow is business logic coupled to the Lambdas' input/output contracts, but it is deployed with infra resources (role, ARNs).

| Option | Where | Good when | Watch out for |
|---|---|---|---|
| **A. With the app code, in a service repo that also holds its Terraform** (recommended default) | `service-x/` has `src/`, `definition.asl.json.tftpl`, `*.tf` | Team owns its service end to end ("you build it, you run it"); definition and Lambda contracts change together | Needs a standard module/baseline so every team doesn't reinvent IAM, logging, tagging |
| **B. In the central infra repo** | `infra/` repo holds the template and Terraform | Strong central platform team, strict review, few workflows | Developers wait on the infra team for every workflow tweak; contract changes span two repos/PRs |
| **C. In the app repo, consumed by the infra repo** | App repo owns the ASL; infra repo references a **pinned** version (git tag as a module source, or a released artifact in S3) | Devs own the logic, platform team owns deployment | Version pinning discipline; two-step releases |
| **D. Monorepo (this learning lab)** | Everything in one folder | Learning, small teams | Doesn't scale to many teams without path-based pipelines |

Practical recommendation:
- **Small team or learning:** one repo (this lab's layout, option D/A). Template next to the Lambda code and Terraform.
- **Larger org with a platform team:** option A or C: the *developers own the workflow definition* (they know the contracts), the platform team owns the reusable Terraform module (role, logging, alias, alarms) that the service calls with `definition = templatefile(...)`.
- Avoid putting a developer-owned definition in a repo only the infra team can merge to, unless you add **CODEOWNERS** giving the dev team required review on that file.

Whichever you choose:
- **Pipelines by path**: `src/**` -> code pipeline; `*.tf` and `*.tftpl` -> infra pipeline (so a definition change triggers Terraform, not the code deploy).
- **Validate the ASL in CI** (`aws stepfunctions validate-state-machine-definition`) on every PR touching the template.
- **Same PR for coupled changes**, with the backward-compatible ordering above.
- Treat the template as **code**: reviewed, versioned, tested with sample inputs in a non-prod account.
