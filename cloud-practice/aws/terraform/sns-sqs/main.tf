locals {
  name = var.project
  tags = merge(
    {
      Project   = var.project
      ManagedBy = "terraform"
      Module    = "aws/terraform/sns-sqs"
    },
    var.extra_tags,
  )
  wire_lambda = var.lambda_function_arn != ""
}

##############################################################################
# SNS topic — the fan-out point. One publish here can reach this queue AND,
# later, any number of other subscribers (another SQS queue, an email
# address, another Lambda) with zero changes to the publisher.
##############################################################################
resource "aws_sns_topic" "this" {
  name = local.name
}

##############################################################################
# Dead-letter queue — messages that failed max_receive_count times land
# here instead of retrying forever or vanishing silently.
##############################################################################
resource "aws_sqs_queue" "dlq" {
  name                      = "${local.name}-dlq"
  message_retention_seconds = 1209600 # 14 days — the max, since a DLQ's whole purpose is "give a human time to notice and investigate"
}

##############################################################################
# Main queue — subscribed to the SNS topic
##############################################################################
resource "aws_sqs_queue" "this" {
  name                       = local.name
  visibility_timeout_seconds = var.visibility_timeout_seconds
  message_retention_seconds  = var.message_retention_seconds

  redrive_policy = jsonencode({
    deadLetterTargetArn = aws_sqs_queue.dlq.arn
    maxReceiveCount     = var.max_receive_count
  })
}

# The DLQ needs to know which live queue is allowed to redrive INTO it —
# without this, SQS has no record of the relationship for
# aws_sqs_queue_redrive_allow_policy-aware tooling/console warnings.
resource "aws_sqs_queue_redrive_allow_policy" "dlq" {
  queue_url = aws_sqs_queue.dlq.id
  redrive_allow_policy = jsonencode({
    redrivePermission = "byQueue"
    sourceQueueArns   = [aws_sqs_queue.this.arn]
  })
}

# SQS queues are private by default — SNS needs an explicit policy statement
# granting it SendMessage, scoped to THIS topic only via the Condition.
resource "aws_sqs_queue_policy" "allow_sns" {
  queue_url = aws_sqs_queue.this.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Sid       = "AllowSNSPublish"
      Effect    = "Allow"
      Principal = { Service = "sns.amazonaws.com" }
      Action    = "sqs:SendMessage"
      Resource  = aws_sqs_queue.this.arn
      Condition = {
        ArnEquals = { "aws:SourceArn" = aws_sns_topic.this.arn }
      }
    }]
  })
}

resource "aws_sns_topic_subscription" "sqs" {
  topic_arn            = aws_sns_topic.this.arn
  protocol             = "sqs"
  endpoint             = aws_sqs_queue.this.arn
  raw_message_delivery = true # without this, SQS gets an SNS *envelope* JSON wrapping your message; raw delivery hands your original payload straight through
}

##############################################################################
# Optional: SQS -> Lambda. NOTE: this only creates the poller side. The
# Lambda's OWN execution role (owned by the lambda/ module's state, not this
# one) still needs sqs:ReceiveMessage/DeleteMessage/GetQueueAttributes on
# this queue — see outputs.next_steps for the exact policy to attach there.
##############################################################################
resource "aws_lambda_event_source_mapping" "sqs_to_lambda" {
  count            = local.wire_lambda ? 1 : 0
  event_source_arn = aws_sqs_queue.this.arn
  function_name    = var.lambda_function_arn
  batch_size       = 10
}
