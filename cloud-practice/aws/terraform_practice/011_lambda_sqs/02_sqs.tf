# ---------------------------------------------------------------------------
# STEP 2: SQS queue (+ dead-letter queue)
# ---------------------------------------------------------------------------
# Producers send messages to the main queue. Lambda polls it and processes them.
# A message that fails too many times is moved to the dead-letter queue (DLQ)
# so one bad message doesn't block or loop forever.

resource "aws_sqs_queue" "dlq" {
  name                      = "${var.project}-dlq"
  message_retention_seconds = 1209600 # 14 days to investigate failures
}

resource "aws_sqs_queue" "main" {
  name = "${var.project}-queue"

  # While Lambda works on a message it is hidden from other consumers for this
  # long. AWS requires it to be >= the Lambda timeout; 6x is the recommended margin.
  visibility_timeout_seconds = var.lambda_timeout_seconds * 6

  redrive_policy = jsonencode({
    deadLetterTargetArn = aws_sqs_queue.dlq.arn
    maxReceiveCount     = var.max_receive_count
  })
}
