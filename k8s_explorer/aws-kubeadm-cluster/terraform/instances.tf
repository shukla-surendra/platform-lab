data "aws_ami" "ubuntu" {
  most_recent = true
  owners      = ["099720109477"] # Canonical

  filter {
    name   = "name"
    values = ["ubuntu/images/hvm-ssd-gp3/ubuntu-noble-24.04-amd64-server-*"]
  }
  filter {
    name   = "virtualization-type"
    values = ["hvm"]
  }
}

# Deliberately does NOT install containerd/kubeadm/kubelet/kubectl via user_data. Those
# steps are identical across all three nodes and easy to script, but they're also exactly
# where the interesting concepts live for a first pass — see docs/CONCEPTS.md and
# README.md's SOP. Automating them is a reasonable follow-up exercise once you've typed
# them by hand at least once.
locals {
  common_tags = {
    Project = var.project
  }
}

resource "aws_instance" "control_plane" {
  ami                    = data.aws_ami.ubuntu.id
  instance_type          = var.instance_type
  subnet_id              = aws_subnet.public.id
  vpc_security_group_ids = [aws_security_group.cluster.id]
  key_name               = aws_key_pair.this.key_name

  root_block_device {
    volume_type = "gp3"
    volume_size = var.root_volume_gb
  }

  tags = merge(local.common_tags, {
    Name = "${var.project}-control-plane"
    Role = "control-plane"
  })
}

resource "aws_instance" "worker" {
  count = var.worker_count

  ami                    = data.aws_ami.ubuntu.id
  instance_type          = var.instance_type
  subnet_id              = aws_subnet.public.id
  vpc_security_group_ids = [aws_security_group.cluster.id]
  key_name               = aws_key_pair.this.key_name

  root_block_device {
    volume_type = "gp3"
    volume_size = var.root_volume_gb
  }

  tags = merge(local.common_tags, {
    Name = "${var.project}-worker-${count.index + 1}"
    Role = "worker"
  })
}
