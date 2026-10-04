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

data "aws_vpc" "default" {
  default = true
}

# Default VPC has one subnet per AZ; RDS subnet group and RDS Proxy both need >= 2 AZs
data "aws_subnets" "default" {
  filter {
    name   = "vpc-id"
    values = [data.aws_vpc.default.id]
  }
}

resource "aws_db_subnet_group" "this" {
  name       = "rds-proxy-lab"
  subnet_ids = data.aws_subnets.default.ids
}

# ---------- Security groups ----------

# Proxy: accepts MySQL from inside the VPC (clients), talks out to the DB
resource "aws_security_group" "proxy" {
  name        = "rds-proxy-sg"
  description = "RDS Proxy"
  vpc_id      = data.aws_vpc.default.id

  ingress {
    description = "PostgreSQL from VPC"
    from_port   = 5432
    to_port     = 5432
    protocol    = "tcp"
    cidr_blocks = [data.aws_vpc.default.cidr_block]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

# DB: only reachable from the proxy
resource "aws_security_group" "db" {
  name        = "rds-db-sg"
  description = "RDS instance - only from proxy"
  vpc_id      = data.aws_vpc.default.id

  ingress {
    description     = "PostgreSQL from proxy"
    from_port       = 5432
    to_port         = 5432
    protocol        = "tcp"
    security_groups = [aws_security_group.proxy.id]
  }
}

# ---------- RDS (smallest practical) ----------

resource "aws_db_instance" "this" {
  identifier     = "proxy-lab-db"
  engine         = "postgres"
  engine_version = "16"
  instance_class = "db.t4g.micro" # smallest current-gen class

  allocated_storage = 20 # minimum for gp3
  storage_type      = "gp3"

  db_name  = "labdb"
  username = "dbadmin" # "admin" is reserved in PostgreSQL

  # RDS creates and stores the password in Secrets Manager (never in Terraform state)
  manage_master_user_password = true

  db_subnet_group_name   = aws_db_subnet_group.this.name
  vpc_security_group_ids = [aws_security_group.db.id]
  publicly_accessible    = false
  multi_az               = false

  # Lab settings: cheap and easy to destroy
  backup_retention_period = 0
  skip_final_snapshot     = true
  deletion_protection     = false
}

# ---------- IAM role the proxy uses to read the DB secret ----------

resource "aws_iam_role" "proxy" {
  name = "rds-proxy-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Action    = "sts:AssumeRole"
      Principal = { Service = "rds.amazonaws.com" }
    }]
  })
}

resource "aws_iam_role_policy" "proxy" {
  name = "read-db-secret"
  role = aws_iam_role.proxy.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect   = "Allow"
        Action   = ["secretsmanager:GetSecretValue"]
        Resource = aws_db_instance.this.master_user_secret[0].secret_arn
      },
      {
        # Secret is encrypted with the default aws/secretsmanager key
        Effect    = "Allow"
        Action    = ["kms:Decrypt"]
        Resource  = "*"
        Condition = { StringEquals = { "kms:ViaService" = "secretsmanager.us-east-1.amazonaws.com" } }
      }
    ]
  })
}

# ---------- RDS Proxy ----------

resource "aws_db_proxy" "this" {
  name                   = "proxy-lab"
  engine_family          = "POSTGRESQL"
  role_arn               = aws_iam_role.proxy.arn
  vpc_subnet_ids         = data.aws_subnets.default.ids
  vpc_security_group_ids = [aws_security_group.proxy.id]
  require_tls            = true
  idle_client_timeout    = 1800

  auth {
    auth_scheme = "SECRETS"
    iam_auth    = "DISABLED"
    secret_arn  = aws_db_instance.this.master_user_secret[0].secret_arn
  }
}

resource "aws_db_proxy_default_target_group" "this" {
  db_proxy_name = aws_db_proxy.this.name

  connection_pool_config {
    max_connections_percent      = 100
    max_idle_connections_percent = 50
    connection_borrow_timeout    = 120
  }
}

resource "aws_db_proxy_target" "this" {
  db_proxy_name          = aws_db_proxy.this.name
  target_group_name      = aws_db_proxy_default_target_group.this.name
  db_instance_identifier = aws_db_instance.this.identifier
}

output "db_endpoint" {
  value = aws_db_instance.this.address
}

output "proxy_endpoint" {
  value = aws_db_proxy.this.endpoint
}

output "secret_arn" {
  value = aws_db_instance.this.master_user_secret[0].secret_arn
}
