#!/bin/bash
# Bootstraps the vLLM OpenAI-compatible server on first boot.
# Everything here is logged to /var/log/vllm-setup.log (readable over SSM —
# no SSH needed just to check on this).
set -euo pipefail
exec > >(tee /var/log/vllm-setup.log) 2>&1

echo "=== vLLM bootstrap starting (run_mode=${run_mode}): $(date -u) ==="

mkdir -p /home/ec2-user/hf-cache
chown -R ec2-user:ec2-user /home/ec2-user/hf-cache

nvidia-smi || echo "WARNING: nvidia-smi failed — GPU driver may not be ready yet"

%{ if run_mode == "docker" }
# --- docker path: the official vllm/vllm-openai image, CUDA/torch versions
# pinned by vLLM's own release — see GPU_AND_LLM_SERVING_GUIDE.md #6. The
# DLAMI this instance boots from already ships Docker + the NVIDIA Container
# Toolkit configured, so no driver/toolkit install is needed here.
until docker info >/dev/null 2>&1; do
  echo "waiting for docker..."
  sleep 5
done

docker rm -f vllm 2>/dev/null || true

docker run -d \
  --name vllm \
  --restart unless-stopped \
  --gpus all \
  --shm-size=${shm_size_gb}g \
  -p 8000:8000 \
  -v /home/ec2-user/hf-cache:/root/.cache/huggingface \
  ${docker_env_args} \
  vllm/vllm-openai:${vllm_image_tag} \
  --model ${model_id} \
  --max-model-len ${max_model_len} \
  --gpu-memory-utilization ${gpu_memory_utilization} \
  --dtype ${dtype} \
  ${vllm_extra_args} \
  --host 0.0.0.0 \
  --port 8000

echo "=== vLLM container launched: $(date -u) ==="
echo "=== First launch downloads the model from Hugging Face — this can take several minutes for a 7B model. ==="
echo "=== Check progress with: docker logs -f vllm ==="

%{ else }
# --- bare_metal path: pip-installed into a venv, run as a systemd service.
# No container layer at all — but slower on first boot (installing vllm
# pulls a multi-GB CUDA-enabled torch wheel from PyPI) and YOU own matching
# CUDA/driver/torch versions, not vLLM's pinned image. See
# GPU_AND_LLM_SERVING_GUIDE.md #6 for the full tradeoff.
dnf -y install python3 python3-pip git

sudo -u ec2-user python3 -m venv /home/ec2-user/vllm-venv
sudo -u ec2-user /home/ec2-user/vllm-venv/bin/pip install --upgrade pip
sudo -u ec2-user /home/ec2-user/vllm-venv/bin/pip install ${pip_install_target}

cat > /etc/systemd/system/vllm.service <<UNIT
[Unit]
Description=vLLM OpenAI-compatible server
After=network.target

[Service]
Type=simple
User=ec2-user
Environment=HF_HOME=/home/ec2-user/hf-cache
${systemd_hf_token_env}
ExecStart=/home/ec2-user/vllm-venv/bin/vllm serve ${model_id} \
  --max-model-len ${max_model_len} \
  --gpu-memory-utilization ${gpu_memory_utilization} \
  --dtype ${dtype} \
  ${vllm_extra_args} \
  --host 0.0.0.0 \
  --port 8000
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
UNIT

systemctl daemon-reload
systemctl enable --now vllm

echo "=== vLLM systemd service started: $(date -u) ==="
echo "=== First launch downloads the model from Hugging Face — this can take several minutes for a 7B model. ==="
echo "=== Check progress with: journalctl -u vllm -f ==="
%{ endif }

echo "=== Ready when the log shows: 'Uvicorn running on http://0.0.0.0:8000' ==="
