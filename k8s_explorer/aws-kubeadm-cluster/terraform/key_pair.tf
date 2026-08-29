# Generated here for lab convenience, so there's no "go create a key pair in the console
# first" prerequisite. Real caveat, not hidden: the private key ends up in plaintext
# inside terraform.tfstate. Acceptable for a throwaway POC you'll `terraform destroy`
# when done; NOT a pattern to carry into anything real — there, bring your own key pair
# (aws_key_pair referencing a public key you already hold) instead of generating one.

resource "tls_private_key" "ssh" {
  algorithm = "ED25519"
}

resource "aws_key_pair" "this" {
  key_name   = "${var.project}-key"
  public_key = tls_private_key.ssh.public_key_openssh
}

resource "local_sensitive_file" "private_key" {
  filename        = "${path.module}/${var.project}-key.pem"
  content         = tls_private_key.ssh.private_key_openssh
  file_permission = "0400"
}
