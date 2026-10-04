# ---------------------------------------------------------------------------
# STEP 2: The state machine (the workflow)
# ---------------------------------------------------------------------------
# A state machine is defined in ASL (Amazon States Language), a JSON document.
# Terraform's job is NOT to understand the workflow: it just stores that JSON
# string in the `definition` argument and deploys it. The workflow logic lives
# in the ASL file; the AWS resources it needs (role, logs, Lambdas) live in
# Terraform.

# 2a. IAM role the state machine assumes while running
data "aws_iam_policy_document" "sfn_assume" {
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["states.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "sfn" {
  name               = "${var.project}-sfn-role"
  assume_role_policy = data.aws_iam_policy_document.sfn_assume.json
}

# What the workflow may do: invoke exactly these two Lambdas (least privilege)
data "aws_iam_policy_document" "sfn_permissions" {
  statement {
    sid     = "InvokeWorkers"
    actions = ["lambda:InvokeFunction"]
    resources = [
      aws_lambda_function.validate.arn,
      "${aws_lambda_function.validate.arn}:*",
      aws_lambda_function.process.arn,
      "${aws_lambda_function.process.arn}:*",
    ]
  }

  # CloudWatch Logs delivery: these actions do not support resource-level
  # permissions, so "*" is required by AWS.
  statement {
    sid = "LogDelivery"
    actions = [
      "logs:CreateLogDelivery",
      "logs:GetLogDelivery",
      "logs:UpdateLogDelivery",
      "logs:DeleteLogDelivery",
      "logs:ListLogDeliveries",
      "logs:PutResourcePolicy",
      "logs:DescribeResourcePolicies",
      "logs:DescribeLogGroups",
    ]
    resources = ["*"]
  }
}

resource "aws_iam_role_policy" "sfn" {
  name   = "workflow-permissions"
  role   = aws_iam_role.sfn.id
  policy = data.aws_iam_policy_document.sfn_permissions.json
}

# 2b. Execution history logs
resource "aws_cloudwatch_log_group" "sfn" {
  name              = "/aws/vendedlogs/states/${var.project}-order-workflow"
  retention_in_days = 7
}

# 2c. The workflow itself
resource "aws_sfn_state_machine" "order" {
  name     = "${var.project}-order-workflow"
  role_arn = aws_iam_role.sfn.arn
  type     = "STANDARD" # long-running, exactly-once, full history. EXPRESS = high volume, short, at-least-once.

  # templatefile() fills ${validate_arn} / ${process_arn} in the ASL file with
  # the real Lambda ARNs. This is how Terraform and the workflow "merge":
  # the JSON stays a readable file; Terraform injects the AWS-specific values.
  definition = templatefile("${path.module}/definition.asl.json.tftpl", {
    validate_arn = aws_lambda_function.validate.arn
    process_arn  = aws_lambda_function.process.arn
  })

  # Immutable numbered versions: every definition change creates a new version
  publish = true

  logging_configuration {
    log_destination        = "${aws_cloudwatch_log_group.sfn.arn}:*"
    include_execution_data = true  # logs inputs/outputs; turn OFF if data is sensitive
    level                  = "ALL" # ALL | ERROR | FATAL | OFF
  }

  tracing_configuration {
    enabled = false # set true (and add X-Ray permissions) for tracing
  }

  depends_on = [aws_iam_role_policy.sfn]
}

# 2d. Alias "live": callers start executions on the alias, not on a raw version.
# Deploy = publish a new version and move the alias. Rollback = move it back.
resource "aws_sfn_alias" "live" {
  name        = "live"
  description = "Current production version"

  routing_configuration {
    state_machine_version_arn = aws_sfn_state_machine.order.state_machine_version_arn
    weight                    = 100
  }
}
