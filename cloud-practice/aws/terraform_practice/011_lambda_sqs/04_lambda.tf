# ---------------------------------------------------------------------------
# STEP 4: Package the code, upload it to S3, create the Lambda
# ---------------------------------------------------------------------------

# 4a. Zip everything in ./src. output_base64sha256 changes whenever any file in
#     src/ changes: that is how Terraform detects "the code changed".
data "archive_file" "lambda" {
  type        = "zip"
  source_dir  = "${path.module}/src"
  output_path = "${path.module}/build/processor.zip"
}

# 4b. Upload the zip to the artifacts bucket (new upload = new object version)
resource "aws_s3_object" "code" {
  bucket = aws_s3_bucket.artifacts.id
  key    = "lambda/processor.zip"
  source = data.archive_file.lambda.output_path
  etag   = data.archive_file.lambda.output_md5

  depends_on = [aws_s3_bucket_versioning.artifacts]
}

# 4c. Log group created by us so we control retention (otherwise Lambda creates
#     one with "never expire")
resource "aws_cloudwatch_log_group" "lambda" {
  name              = "/aws/lambda/${var.project}-processor"
  retention_in_days = 7
}

# 4d. The function
resource "aws_lambda_function" "processor" {
  function_name = "${var.project}-processor"
  role          = aws_iam_role.lambda.arn

  runtime       = "python3.13"
  architectures = ["arm64"]                # cheaper than x86_64
  handler       = "handler.lambda_handler" # file handler.py, function lambda_handler
  timeout       = var.lambda_timeout_seconds
  memory_size   = 128

  # Code comes from S3 (pinned to the exact object version we just uploaded)
  s3_bucket         = aws_s3_bucket.artifacts.id
  s3_key            = aws_s3_object.code.key
  s3_object_version = aws_s3_object.code.version_id

  # Tells Terraform to call "update function code" when the zip contents change
  source_code_hash = data.archive_file.lambda.output_base64sha256

  # --- Alternative: let CI/scripts deploy code, Terraform only owns the infra ---
  # Uncomment so Terraform STOPS reverting code you deployed with scripts/deploy_code.sh:
  # lifecycle {
  #   ignore_changes = [s3_key, s3_object_version, source_code_hash]
  # }

  depends_on = [
    aws_iam_role_policy_attachment.logs,
    aws_cloudwatch_log_group.lambda,
  ]
}

# ---------------------------------------------------------------------------
# STEP 5: SQS -> Lambda trigger (event source mapping)
# ---------------------------------------------------------------------------
# Lambda's internal poller reads the queue and invokes the function with a
# batch of messages. If the function returns successfully, the poller deletes
# the batch from the queue; if it throws, messages reappear after the
# visibility timeout and are retried (up to max_receive_count, then DLQ).

resource "aws_lambda_event_source_mapping" "sqs" {
  event_source_arn = aws_sqs_queue.main.arn
  function_name    = aws_lambda_function.processor.arn
  batch_size       = var.batch_size

  # Lets the handler report WHICH messages failed so only those are retried,
  # not the whole batch.
  function_response_types = ["ReportBatchItemFailures"]

  # Wait up to 5s to fill a batch before invoking
  maximum_batching_window_in_seconds = 5

  depends_on = [aws_iam_role_policy_attachment.sqs]
}
