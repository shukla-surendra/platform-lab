locals {
  name = var.project
  tags = merge(
    {
      Project   = var.project
      ManagedBy = "terraform"
      Module    = "aws/terraform/rds"
    },
    var.extra_tags,
  )
}

data "aws_vpc" "default" {
  default = true
}

data "aws_subnets" "all_in_vpc" {
  filter {
    name   = "vpc-id"
    values = [data.aws_vpc.default.id]
  }
}

##############################################################################
# Master password — generated, never hand-typed, and stored in Secrets
# Manager instead of a plaintext tfvars file or Terraform state alone.
##############################################################################
resource "random_password" "master" {
  length  = 24
  special = false # some RDS engines reject certain special characters in the master password; safe to exclude entirely
}

resource "aws_secretsmanager_secret" "db" {
  name                    = "${local.name}-master-credentials"
  recovery_window_in_days = 0 # lab default: immediate delete on destroy, not the usual 7-30 day recovery window
}

resource "aws_secretsmanager_secret_version" "db" {
  secret_id = aws_secretsmanager_secret.db.id
  secret_string = jsonencode({
    username = var.master_username
    password = random_password.master.result
    engine   = "postgres"
    host     = aws_db_instance.this.address
    port     = aws_db_instance.this.port
    dbname   = var.db_name
  })
}

##############################################################################
# Networking — subnet group across the default VPC's subnets, SG allowing
# 5432 only from within the VPC (not the internet)
##############################################################################
resource "aws_db_subnet_group" "this" {
  name       = local.name
  subnet_ids = data.aws_subnets.all_in_vpc.ids
}

resource "aws_security_group" "db" {
  name        = "${local.name}-sg"
  description = "RDS: 5432 from within the VPC only"
  vpc_id      = data.aws_vpc.default.id

  ingress {
    description = "PostgreSQL from within the VPC"
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

  tags = { Name = "${local.name}-sg" }
}

##############################################################################
# The instance
##############################################################################
resource "aws_db_instance" "this" {
  identifier     = local.name
  engine         = "postgres"
  engine_version = var.engine_version
  instance_class = var.instance_class

  allocated_storage     = var.allocated_storage_gib
  storage_type          = "gp3"
  storage_encrypted     = true
  max_allocated_storage = var.allocated_storage_gib * 4 # storage autoscaling ceiling — grows under pressure, never shrinks back

  db_name  = var.db_name
  username = var.master_username
  password = random_password.master.result

  db_subnet_group_name   = aws_db_subnet_group.this.name
  vpc_security_group_ids = [aws_security_group.db.id]

  multi_az                = var.multi_az
  backup_retention_period = var.backup_retention_days
  backup_window           = "03:00-04:00" # UTC — pick a real low-traffic window in prod
  maintenance_window      = "mon:04:30-mon:05:30"

  skip_final_snapshot       = var.skip_final_snapshot
  final_snapshot_identifier = var.skip_final_snapshot ? null : "${local.name}-final"
  deletion_protection       = false # a lab default — set true once this holds anything real

  tags = local.tags
}
