terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~>6.0"
    }
  }
}

provider "aws" {
  region = "us-east-1"
}

variable "instaces_names" {
  type        = map(string)
  description = "ec2 instances name list list"
  default = {
    dev = "inst1"
    stage = "inst2"
  }
}

resource "aws_instance" "env_instances" {
  for_each       = var.instaces_names
  ami            = "ami-025d99823a4caad37"
  instance_type = "t2.micro"
  tags = {
    Key   = each.key
    value = each.value
  }
}