locals {
  name = var.project
  tags = merge(
    {
      Project   = var.project
      ManagedBy = "terraform"
      Module    = "aws/terraform/vllm-gpu-serving"
    },
    var.extra_tags,
  )

  key_pair_name = var.create_key_pair ? aws_key_pair.this[0].key_name : var.existing_key_pair_name

  # docker: an "-e KEY=value" flag. bare_metal: a systemd unit "Environment="
  # line. Same secret, two syntaxes — precomputed here so the template itself
  # never has to do string manipulation on a value containing a secret.
  docker_env_args      = var.hf_token != "" ? "-e HUGGING_FACE_HUB_TOKEN=${var.hf_token}" : ""
  systemd_hf_token_env = var.hf_token != "" ? "Environment=HUGGING_FACE_HUB_TOKEN=${var.hf_token}" : ""

  vllm_extra_args = trimspace(join(" ", compact([
    var.quantization != "" ? "--quantization ${var.quantization}" : "",
    var.vllm_api_key != "" ? "--api-key ${var.vllm_api_key}" : "",
  ])))

  pip_install_target = var.vllm_pip_version != "" ? "vllm==${var.vllm_pip_version}" : "vllm"
}

data "aws_vpc" "default" {
  default = true
}

# Every subnet in the default VPC, not just one AZ — the ASG can attempt
# capacity for a given instance type across ALL of these, which meaningfully
# improves the odds of landing an L4 (g6) rather than falling all the way
# through to A10G (g5).
data "aws_subnets" "all_in_vpc" {
  filter {
    name   = "vpc-id"
    values = [data.aws_vpc.default.id]
  }
}

# The "Base OSS Nvidia Driver" DLAMI ships the NVIDIA driver, Docker, and the
# NVIDIA Container Toolkit already installed and configured — user_data only
# has to `docker run --gpus all`, nothing to compile or install first boot.
data "aws_ami" "dlami_gpu" {
  most_recent = true
  owners      = ["amazon"]

  filter {
    name   = "name"
    values = ["Deep Learning Base OSS Nvidia Driver GPU AMI (Amazon Linux 2023)*"]
  }
  filter {
    name   = "state"
    values = ["available"]
  }
  filter {
    name   = "architecture"
    values = ["x86_64"]
  }
}

##############################################################################
# SSH key pair — generated + downloaded as a local .pem, or bring your own.
# See the GPU/LLM guide's "Managing the .pem file" section for the full
# lifecycle (rotation, loss, why SSM is the safer DEFAULT access path).
##############################################################################
resource "tls_private_key" "this" {
  count     = var.create_key_pair ? 1 : 0
  algorithm = "RSA"
  rsa_bits  = 4096
}

resource "aws_key_pair" "this" {
  count      = var.create_key_pair ? 1 : 0
  key_name   = "${local.name}-key"
  public_key = tls_private_key.this[0].public_key_openssh
}

# file_permission = "0400" — matches what `ssh` itself requires (refuses to
# use a key that's group/world-readable). Written NEXT TO this module, and
# *.pem is in the repo's root .gitignore — never commit this file.
resource "local_sensitive_file" "pem" {
  count           = var.create_key_pair ? 1 : 0
  content         = tls_private_key.this[0].private_key_pem
  filename        = "${path.module}/${local.name}-key.pem"
  file_permission = "0400"
}

##############################################################################
# Security group — 22 (SSH, PEM) + 8000 (vLLM API), both from variables you
# should narrow before this holds anything real.
##############################################################################
resource "aws_security_group" "this" {
  name        = "${local.name}-sg"
  description = "vLLM GPU box: SSH + API port, both CIDR-restricted by variable"
  vpc_id      = data.aws_vpc.default.id

  ingress {
    description = "SSH"
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = [var.allowed_ssh_cidr]
  }

  ingress {
    description = "vLLM OpenAI-compatible API"
    from_port   = 8000
    to_port     = 8000
    protocol    = "tcp"
    cidr_blocks = [var.allowed_api_cidr]
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
# IAM — SSM (console-free, PEM-free shell access), S3 read-only (optional:
# pull model weights from your own bucket instead of the HF Hub), ECR
# read-only (optional: run your own image instead of vllm/vllm-openai).
##############################################################################
resource "aws_iam_role" "instance" {
  name = "${local.name}-instance-role"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "ec2.amazonaws.com" }
      Action    = "sts:AssumeRole"
    }]
  })
}

resource "aws_iam_role_policy_attachment" "ssm_core" {
  role       = aws_iam_role.instance.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore"
}

resource "aws_iam_role_policy_attachment" "s3_read_only" {
  role       = aws_iam_role.instance.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonS3ReadOnlyAccess"
}

resource "aws_iam_role_policy_attachment" "ecr_read_only" {
  role       = aws_iam_role.instance.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonEC2ContainerRegistryReadOnly"
}

resource "aws_iam_instance_profile" "instance" {
  name = "${local.name}-instance-profile"
  role = aws_iam_role.instance.name
}

##############################################################################
# Launch template
##############################################################################
resource "aws_launch_template" "this" {
  name_prefix = "${local.name}-"
  image_id    = data.aws_ami.dlami_gpu.id
  key_name    = local.key_pair_name != "" ? local.key_pair_name : null

  iam_instance_profile {
    name = aws_iam_instance_profile.instance.name
  }

  network_interfaces {
    associate_public_ip_address = var.assign_public_ip
    security_groups             = [aws_security_group.this.id]
  }

  block_device_mappings {
    device_name = "/dev/xvda"
    ebs {
      volume_size = var.root_volume_size_gib
      volume_type = "gp3"
      encrypted   = true
    }
  }

  user_data = base64encode(templatefile("${path.module}/templates/user_data.sh.tpl", {
    run_mode               = var.run_mode
    model_id               = var.model_id
    vllm_image_tag         = var.vllm_image_tag
    pip_install_target     = local.pip_install_target
    max_model_len          = var.max_model_len
    gpu_memory_utilization = var.gpu_memory_utilization
    dtype                  = var.dtype
    shm_size_gb            = var.shm_size_gb
    docker_env_args        = local.docker_env_args
    systemd_hf_token_env   = local.systemd_hf_token_env
    vllm_extra_args        = local.vllm_extra_args
  }))

  tag_specifications {
    resource_type = "instance"
    tags          = merge(local.tags, { Name = local.name })
  }
}

##############################################################################
# Auto Scaling Group — desired = 1. NOT here for horizontal scaling; here for
# (a) self-healing (a crashed/terminated instance is replaced automatically)
# and (b) the mixed_instances_policy "prioritized" allocation strategy, which
# is what actually implements "try L4 (g6), fall back to A10G (g5)":  AWS
# attempts gpu_instance_types[0] first and only tries the next entry if that
# type has no capacity in the available subnets/AZs at launch time.
##############################################################################
resource "aws_autoscaling_group" "this" {
  name                = local.name
  min_size            = 1
  max_size            = 1
  desired_capacity    = 1
  vpc_zone_identifier = data.aws_subnets.all_in_vpc.ids
  health_check_type   = "EC2"

  mixed_instances_policy {
    launch_template {
      launch_template_specification {
        launch_template_id = aws_launch_template.this.id
        version            = "$Latest"
      }

      dynamic "override" {
        for_each = var.gpu_instance_types
        content {
          instance_type = override.value
        }
      }
    }

    instances_distribution {
      on_demand_allocation_strategy            = "prioritized"
      on_demand_base_capacity                  = var.use_spot ? 0 : 1
      on_demand_percentage_above_base_capacity = var.use_spot ? 0 : 100
      spot_allocation_strategy                 = "capacity-optimized-prioritized"
    }
  }

  tag {
    key                 = "Name"
    value               = local.name
    propagate_at_launch = true
  }
}

# The ASG doesn't expose "the instance's IP" directly — look it up by the
# tag EC2 Auto Scaling puts on every instance it launches.
data "aws_instances" "this" {
  filter {
    name   = "tag:aws:autoscaling:groupName"
    values = [aws_autoscaling_group.this.name]
  }
  instance_state_names = ["pending", "running"]
  depends_on           = [aws_autoscaling_group.this]
}

# No count/for_each here on purpose: gating this on
# length(data.aws_instances.this.ids) would make Terraform need to know
# that length AT PLAN TIME, which it can't on a first apply (the ASG's
# instances don't exist yet) — Terraform errors with "Invalid count
# argument" instead of just deferring, unlike a plain attribute reference.
# depends_on defers the READ itself until apply time, after the ASG is up,
# so ids[0] is safe by the time this actually runs.
data "aws_instance" "primary" {
  instance_id = data.aws_instances.this.ids[0]
  depends_on  = [aws_autoscaling_group.this]
}
