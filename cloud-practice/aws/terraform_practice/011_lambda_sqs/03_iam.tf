# ---------------------------------------------------------------------------
# STEP 3: IAM role for the Lambda function (its "execution role")
# ---------------------------------------------------------------------------
# TRUST policy: lets the Lambda service assume the role.
# PERMISSION policies: what the function may do while running.

data "aws_iam_policy_document" "lambda_assume" {
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["lambda.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "lambda" {
  name               = "${var.project}-lambda-role"
  assume_role_policy = data.aws_iam_policy_document.lambda_assume.json
}

# Write logs to CloudWatch
resource "aws_iam_role_policy_attachment" "logs" {
  role       = aws_iam_role.lambda.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

# Read / delete messages from SQS (needed by the SQS -> Lambda poller)
resource "aws_iam_role_policy_attachment" "sqs" {
  role       = aws_iam_role.lambda.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaSQSQueueExecutionRole"
}

# NOTE: no S3 permission is needed. Lambda downloads its own code from S3 at
# deploy time using the identity that creates/updates the function (you), not
# this role.
