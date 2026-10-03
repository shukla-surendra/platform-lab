terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 6.0"
    }
  }
}

provider "aws" {
  region = "us-east-1"
}

# Use the default VPC so this lesson is only about EC2 + user_data
data "aws_vpc" "default" {
  default = true
}

data "aws_ami" "ubuntu" {
  most_recent = true
  owners      = ["099720109477"] # Canonical

  filter {
    name   = "name"
    values = ["ubuntu/images/hvm-ssd/ubuntu-jammy-22.04-amd64-server-*"]
  }

  filter {
    name   = "virtualization-type"
    values = ["hvm"]
  }
}

resource "aws_security_group" "web" {
  name        = "webserver-sg"
  description = "Allow HTTP in, everything out"
  vpc_id      = data.aws_vpc.default.id

  ingress {
    description = "HTTP"
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

resource "aws_instance" "web" {
  ami                         = data.aws_ami.ubuntu.id
  instance_type               = "t3.micro"
  vpc_security_group_ids      = [aws_security_group.web.id]
  associate_public_ip_address = true

  # Runs once as root on first boot
  user_data = <<-EOF
    #!/bin/bash
    apt-get update -y
    apt-get install -y nginx
    echo "<h1>Hello from Terraform on EC2 ($(hostname))</h1><h1>Satyansh Shukla</h1>" > /var/www/html/index.html
    systemctl enable --now nginx
  EOF

  # Re-create the instance if user_data changes (otherwise it would not re-run)
  user_data_replace_on_change = true

  tags = {
    Name = "WebServer"
  }
}

output "public_ip" {
  value = aws_instance.web.public_ip
}

output "url" {
  value = "http://${aws_instance.web.public_ip}"
}
