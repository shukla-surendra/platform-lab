output "application_name" {
  value       = aws_codedeploy_app.this.name
  description = "CodeDeploy application name."
}

output "deployment_group_name" {
  value       = aws_codedeploy_deployment_group.this.deployment_group_name
  description = "What codepipeline/'s deploy stage references."
}

output "revisions_bucket" {
  value       = local.bucket_name
  description = "S3 bucket deployment revisions (zipped appspec.yml + app) are uploaded to."
}

output "next_steps" {
  value = <<-EOT
    1. Package the sample app next to this module:
         cd sample-app && zip -r ../revision.zip . && cd ..
    2. Upload it as a revision:
         aws s3 cp revision.zip s3://${local.bucket_name}/revision.zip
    3. Deploy it by hand (this is exactly what codepipeline/'s deploy stage automates):
         aws deploy create-deployment \
           --application-name ${aws_codedeploy_app.this.name} \
           --deployment-group-name ${aws_codedeploy_deployment_group.this.deployment_group_name} \
           --s3-location bucket=${local.bucket_name},key=revision.zip,bundleType=zip
    4. Watch it: aws deploy get-deployment --deployment-id <id from step 3>
  EOT
}
