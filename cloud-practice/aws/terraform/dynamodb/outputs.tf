output "table_name" {
  value       = aws_dynamodb_table.this.name
  description = "Table name."
}

output "table_arn" {
  value       = aws_dynamodb_table.this.arn
  description = "Grant this to a Lambda/ECS task role's IAM policy for read/write access."
}

output "stream_arn" {
  value       = try(aws_dynamodb_table.this.stream_arn, null)
  description = "Null unless enable_stream = true. Wire into a Lambda event source mapping to react to every insert/update/delete."
}

output "next_steps" {
  value = <<-EOT
    1. Write an item: aws dynamodb put-item --table-name ${aws_dynamodb_table.this.name} --item '{"${var.hash_key}":{"S":"user#1"},"${var.range_key}":{"S":"profile"}}'
    2. Read it back: aws dynamodb get-item --table-name ${aws_dynamodb_table.this.name} --key '{"${var.hash_key}":{"S":"user#1"},"${var.range_key}":{"S":"profile"}}'
    3. Query everything under one partition: aws dynamodb query --table-name ${aws_dynamodb_table.this.name} --key-condition-expression "${var.hash_key} = :pk" --expression-attribute-values '{":pk":{"S":"user#1"}}'
    4. If enable_ttl: put an item with "${var.ttl_attribute_name}" set to a past Unix timestamp and watch it disappear within ~48h (DynamoDB's TTL sweep isn't instant).
  EOT
}
