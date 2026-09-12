output "bucket_name" {
  value       = aws_s3_bucket.demo.id
  description = "The S3 bucket both the group's and the role's policies are scoped to."
}

output "group_name" {
  value       = aws_iam_group.developers.name
  description = "The developers Group (read-only policy attached here, not on the user)."
}

output "user_name" {
  value       = aws_iam_user.demo_user.name
  description = "Member of the developers group; has no policy of its own."
}

output "role_arn" {
  value       = aws_iam_role.uploader.arn
  description = "Assume this to get write-only (PutObject) temporary credentials."
}

output "role_name" {
  value = aws_iam_role.uploader.name
}

output "next_steps" {
  value = <<-EOT
    1. Inspect the group's actual attached policy document:
       aws iam get-policy-version \
         --policy-arn ${aws_iam_policy.developer_readonly.arn} \
         --version-id $(aws iam get-policy --policy-arn ${aws_iam_policy.developer_readonly.arn} --query 'Policy.DefaultVersionId' --output text)

    2. Assume the uploader role (mints temporary credentials, ~1hr):
       CREDS=$(aws sts assume-role \
         --role-arn ${aws_iam_role.uploader.arn} \
         --role-session-name manual-test \
         --query 'Credentials' --output json)

    3. Export them and try the ALLOWED action (PutObject):
       export AWS_ACCESS_KEY_ID=$(echo "$CREDS" | jq -r .AccessKeyId)
       export AWS_SECRET_ACCESS_KEY=$(echo "$CREDS" | jq -r .SecretAccessKey)
       export AWS_SESSION_TOKEN=$(echo "$CREDS" | jq -r .SessionToken)
       echo "hello" | aws s3 cp - s3://${aws_s3_bucket.demo.id}/from-role.txt

    4. Now try the DENIED action with those SAME temporary credentials
       (the role's permission policy never granted s3:GetObject):
       aws s3 cp s3://${aws_s3_bucket.demo.id}/seed.txt -
       # -> An error occurred (403) when calling the HeadObject operation: Forbidden
       # (aws s3 cp calls HeadObject before GetObject -- that's the call
       # that gets denied first; same missing permission either way)

    5. Unset the temporary credentials when done:
       unset AWS_ACCESS_KEY_ID AWS_SECRET_ACCESS_KEY AWS_SESSION_TOKEN
  EOT
}
