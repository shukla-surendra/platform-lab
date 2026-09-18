output "public_ip" {
  value       = try(data.aws_instance.primary.public_ip, null)
  description = "Null until the instance has actually launched — if this is null right after apply, wait ~30s and re-run `terraform output`."
}

output "api_base_url" {
  value       = try("http://${data.aws_instance.primary.public_ip}:8000/v1", null)
  description = "OpenAI-compatible base_url. Point any OpenAI SDK at this."
}

output "instance_id" {
  value       = try(data.aws_instance.primary.id, null)
  description = "Current instance ID (changes if the ASG ever replaces it)."
}

output "instance_type" {
  value       = try(data.aws_instance.primary.instance_type, null)
  description = "Which entry in gpu_instance_types actually got capacity — g6.* = L4, g5.* = A10G fallback."
}

output "pem_file_path" {
  value       = try(local_sensitive_file.pem[0].filename, null)
  description = "Local path to the generated private key. chmod 400 already applied. NEVER commit this (it's in the repo's root .gitignore already)."
}

output "ssh_command" {
  value       = try("ssh -i ${local_sensitive_file.pem[0].filename} ec2-user@${data.aws_instance.primary.public_ip}", "N/A — create_key_pair = false or instance not up yet")
  description = "Direct SSH using the generated .pem. Prefer the SSM command below when you don't specifically need SSH."
}

output "ssm_command" {
  value       = try("aws ssm start-session --target ${data.aws_instance.primary.id}", null)
  description = "No .pem needed — IAM-governed, audit-logged shell access. This is the recommended default; see the GPU/LLM guide."
}

output "next_steps" {
  value = <<-EOT
    1. Wait for the model to load (first boot only — downloads from Hugging Face):
         aws ssm start-session --target $(terraform output -raw instance_id)
         # once connected:
         sudo docker logs -f vllm
         # wait for: "Uvicorn running on http://0.0.0.0:8000"
    2. Smoke-test the API:
         curl $(terraform output -raw api_base_url)/models
    3. Send a chat completion:
         curl $(terraform output -raw api_base_url)/chat/completions \
           -H "Content-Type: application/json" \
           -d '{"model":"${var.model_id}","messages":[{"role":"user","content":"Say hi in five words."}]}'
    4. Or use the Python client: see client/README usage in this module's README.md.
    5. terraform destroy when done — GPU instances are the most expensive thing in this whole repo per hour.
  EOT
}
