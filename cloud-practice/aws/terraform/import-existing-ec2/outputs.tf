output "instance_id" {
  description = "ID of the now-Terraform-managed instance."
  value       = aws_instance.imported.id
}

output "security_group_id" {
  description = "ID of the now-Terraform-managed security group."
  value       = aws_security_group.imported.id
}

output "ephemeral_public_ip" {
  description = "The instance's OWN public IP if it had one -- ignored here since an EIP is attached; would change across stop/start and is never a thing Terraform can 'preserve'."
  value       = aws_instance.imported.public_ip
}

output "elastic_ip" {
  description = "The durable public IP -- stable across stop/start AND instance replacement, because it lives on aws_eip.imported, not on the instance."
  value       = aws_eip.imported.public_ip
}

output "next_steps" {
  description = "What to do after the import succeeds."
  value       = <<-EOT
    1. terraform state list                 # confirm all three resources are present
    2. terraform plan                       # should now show "No changes"
       If it instead shows "aws_instance.imported must be replaced", stop --
       var.ami_id or var.private_ip (ForceNew arguments) don't match reality.
       Fix main.tf/terraform.tfvars, DO NOT apply a replace on someone's live box.
    3. Delete generated.tf if you haven't already merged/cleaned it into main.tf
    4. Optionally remove the `import` blocks from imports.tf -- they're a
       no-op from here on, but some teams keep them as a record of provenance.
  EOT
}
