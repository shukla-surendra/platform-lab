output "control_plane_public_ip" {
  description = "SSH here first — this is where kubeadm init runs."
  value       = aws_instance.control_plane.public_ip
}

output "worker_public_ips" {
  description = "SSH here to run kubeadm join, once you have the join command from the control-plane."
  value       = aws_instance.worker[*].public_ip
}

output "ssh_key_path" {
  description = "Private key Terraform generated for this cluster. Never committed — see .gitignore."
  value       = local_sensitive_file.private_key.filename
}

output "ssh_control_plane" {
  description = "Ready-to-paste SSH command for the control-plane node."
  value       = "ssh -i ${local_sensitive_file.private_key.filename} ubuntu@${aws_instance.control_plane.public_ip}"
}

output "ssh_workers" {
  description = "Ready-to-paste SSH commands for each worker node."
  value       = [for ip in aws_instance.worker[*].public_ip : "ssh -i ${local_sensitive_file.private_key.filename} ubuntu@${ip}"]
}
