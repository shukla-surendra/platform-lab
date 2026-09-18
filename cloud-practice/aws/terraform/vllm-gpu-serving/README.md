# Terraform: vLLM GPU Serving — Qwen2.5-7B on L4, falling back to A10G

Stands up a single GPU instance running [vLLM](https://github.com/vllm-project/vllm)'s
OpenAI-compatible server, serving **Qwen/Qwen2.5-7B-Instruct** by default
(swap `model_id` for any Hugging Face model that fits). Tries an
**NVIDIA L4 (g6)** first; if that instance type has no On-Demand capacity
in the region, AWS EC2 Auto Scaling automatically falls back to an
**NVIDIA A10G (g5)** instead — see "How the L4→A10G fallback works" below.

For the concepts behind every decision this module makes (GPU sizing,
VRAM math, vLLM flags, and — since you asked specifically — **how the
.pem file is managed** end to end), read
**[`GPU_AND_LLM_SERVING_GUIDE.md`](GPU_AND_LLM_SERVING_GUIDE.md)**
alongside this README. This file is the "how to run it"; that one is the
"why it works this way."

This module has been deployed and torn down for real at least once —
**[`TEST_RESULTS.md`](TEST_RESULTS.md)** has the actual API responses and a
real continuous-batching benchmark (16.5 → 116.4 tok/s at concurrency 1 →
8, latency flat), and **[`DEPLOYMENT_LEARNINGS.md`](DEPLOYMENT_LEARNINGS.md)**
has the field notes — including a real Terraform bug `validate` couldn't
catch but `plan` did, and two "looked broken, wasn't" debugging dead
ends worth knowing before you hit them yourself.

> ⚠️⚠️ **The most expensive module in this entire repo, by far.**
> `g6.2xlarge` (L4) is roughly $0.98/hr on-demand; `g5.2xlarge` (A10G) is
> roughly $1.21/hr (check current pricing — these move). Unlike every
> other module here, there is no meaningful Free Tier for GPU instances.
> **`terraform destroy` the moment you're done experimenting.**

## What it creates

```
tls_private_key + aws_key_pair + local_sensitive_file  (generated .pem — see the guide)
Security Group (22 SSH + 8000 API, both CIDR-restricted by variable)
IAM Role + Instance Profile (SSM + S3 read-only + ECR read-only)
Launch Template (DLAMI GPU AMI, user_data runs vLLM — via Docker or bare-metal pip+systemd, see run_mode)
Auto Scaling Group (min=max=desired=1, mixed_instances_policy: try g6 (L4), fall back to g5 (A10G))
  └── data sources to surface the resulting instance's IP/ID as outputs
```

## Files
| File | Purpose |
|---|---|
| `versions.tf` | Provider pins (aws + tls + local) + default tags |
| `variables.tf` | Model/vLLM tuning, GPU fallback list, key pair, network exposure |
| `templates/user_data.sh.tpl` | The bootstrap script — branches on `run_mode` (docker `docker run vllm/vllm-openai` vs. bare-metal `pip install vllm` + a systemd unit) |
| `main.tf` | Key pair, SG, IAM, launch template, ASG, instance lookup |
| `outputs.tf` | API URL, SSH/SSM commands, PEM path, a `next_steps` runbook |
| `client/chat_client.py` | Python: single request + streaming, via the `openai` SDK |
| `client/benchmark.py` | Python: concurrent load test — makes continuous batching visible |
| `GPU_AND_LLM_SERVING_GUIDE.md` | GPU instance types, VRAM math, vLLM concepts, **PEM lifecycle** |

## How the L4 → A10G fallback works
`gpu_instance_types = ["g6.2xlarge", "g6.xlarge", "g5.2xlarge", "g5.xlarge"]`
(the default) is passed as **priority-ordered overrides** into the Auto
Scaling Group's `mixed_instances_policy`, with
`on_demand_allocation_strategy = "prioritized"`. EC2 Auto Scaling
attempts index 0 first; only if `g6.2xlarge` has zero capacity in every
subnet this ASG can use does it move to `g6.xlarge`, then `g5.2xlarge`,
then `g5.xlarge`. This is a real AWS capacity-management feature, not a
Terraform-side retry loop — see the guide for why GPU capacity is
constrained enough that this matters in practice.

## Usage
```bash
cd aws/terraform/vllm-gpu-serving
cp terraform.tfvars.example terraform.tfvars   # review allowed_ssh_cidr / allowed_api_cidr first
terraform init
terraform apply       # GPU instances + the DLAMI take several minutes to launch
terraform output next_steps
```

Then, from your machine (`pip install -r client/requirements.txt` first):
```bash
python client/chat_client.py --host "$(terraform output -raw public_ip)" --prompt "Explain vLLM in one sentence."
python client/chat_client.py --host "$(terraform output -raw public_ip)" --stream --prompt "Write a haiku about GPUs."
python client/benchmark.py   --host "$(terraform output -raw public_ip)" --concurrency 8 --requests 40
```

## Things to try (mini-labs)
0. `apply` once with `run_mode = "docker"`, `destroy`, then `apply` again with `run_mode = "bare_metal"` — time how much longer bare-metal's first boot takes (`docker logs -f vllm` vs. `journalctl -u vllm -f`), and compare `nvidia-smi` output over SSM once both are serving. Functionally identical API; see the guide's "Docker vs bare metal" section for why the module defaults to Docker anyway.
1. `apply`, then `terraform output instance_type` — see WHICH entry in `gpu_instance_types` actually got capacity. Most of the time it's `g6.2xlarge` (L4); if your account/region is capacity-constrained you'll see a `g5.*` fallback instead, live.
2. Watch the model load: `aws ssm start-session --target $(terraform output -raw instance_id)` then `sudo docker logs -f vllm` — first boot downloads ~15GB from Hugging Face, worth watching once.
3. Run `client/benchmark.py` at `--concurrency 1` and then `--concurrency 16` against the same server — compare aggregate tokens/sec, not per-request latency. See the guide's "continuous batching" section for why they diverge.
4. Try quantization: set `quantization = "awq"` with an AWQ-quantized model ID (e.g. a community `-AWQ` checkpoint) and re-`apply` — compare VRAM headroom (`nvidia-smi` over SSM) against the unquantized run.
5. Set `vllm_api_key` to a real secret, re-`apply`, then hit the API without a key (`401`) and with one (`chat_client.py --api-key ...`) — this is the difference between "anyone who can reach port 8000" and "anyone with the key."

## Deliberately minimal
- Single instance, no load balancer — this is a dev/test inference box,
  not a production serving tier. For that, you'd front several of these
  with `alb/`'s target group (swap `health_check_type = "ELB"`, same
  pattern as `autoscaling/`) and raise `max_size`.
- No persistent EFS-backed model cache — if the ASG ever replaces the
  instance (a crash, a manual terminate), the next boot re-downloads the
  model from Hugging Face. Mounting `efs/`'s filesystem at
  `/home/ec2-user/hf-cache` instead of using the local EBS volume would
  fix that; left out to keep this module's failure modes easy to reason
  about.
- No HTTPS/TLS termination on port 8000 — put `alb/` (with an ACM cert)
  or `cloudfront/` in front for anything beyond a lab.
