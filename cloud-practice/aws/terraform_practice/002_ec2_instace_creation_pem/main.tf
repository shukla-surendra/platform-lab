provider "aws" {
  region = "us-east-1"
}


resource "tls_private_key" "ssh" {
  algorithm = "RSA"
  rsa_bits  = 4096
}

resource "aws_key_pair" "ec2" {
  key_name   = "my-ec2-key"
  public_key = tls_private_key.ssh.public_key_openssh
}

# BUG FIXED: the instance had no security group of its own, so AWS attached
# the VPC's default SG — which only allows traffic FROM other resources in
# that same SG, not from the internet. Port 22 was never actually reachable;
# every `ssh` attempt was hanging on the TCP handshake, not failing on auth.
resource "aws_security_group" "ssh" {
  name        = "my-ec2-ssh"
  description = "Allow SSH from my IP only"

  ingress {
    description = "SSH"
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["14.143.254.170/32"] # your current public IP — narrow further or update if it changes
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

resource "aws_instance" "example_instance" {
  ami                    = "ami-0b6d9d3d33ba97d99" # Ubuntu 26.04 — SSH user is "ubuntu", not "ec2-user"
  instance_type          = "t2.micro"
  key_name               = aws_key_pair.ec2.key_name
  vpc_security_group_ids = [aws_security_group.ssh.id]
}

output "instance_ip" {
  # BUG FIXED: this referenced aws_instance.server, a resource that doesn't
  # exist anywhere in this file (the real resource is example_instance) —
  # that typo alone made `terraform validate`/`plan`/`output` fail outright,
  # which is why `terraform output instance_ip` reported "No outputs found":
  # Terraform couldn't even load the config to know what outputs exist.
  value = aws_instance.example_instance.public_ip
}

# BUG FIXED: there was no "private_key" output at all. `terraform output -raw
# private_key > my-key.pem` therefore had nothing to print — the redirect
# still created my-key.pem, just EMPTY (0 bytes), which is why every ssh -i
# attempt had a worthless key even before the network/SG issue above.
output "private_key" {
  value     = tls_private_key.ssh.private_key_pem
  sensitive = true
}