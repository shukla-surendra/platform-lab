variable "region" {
  description = "AWS region. g5 (A10G) and g6 (L4) are both available in us-east-1 — check availability before switching regions."
  type        = string
  default     = "us-east-1"
}

variable "project" {
  description = "Name prefix / tag."
  type        = string
  default     = "aws-mastery-vllm"
}

##############################################################################
# Model + vLLM
##############################################################################
variable "model_id" {
  description = "Hugging Face model ID vLLM serves. Qwen2.5-7B-Instruct fits comfortably on a single 24GB L4/A10G in bf16 (~15GB weights)."
  type        = string
  default     = "Qwen/Qwen2.5-7B-Instruct"
}

variable "run_mode" {
  description = <<-EOT
    "docker" (default) runs the official vllm/vllm-openai image — reproducible,
    CUDA/PyTorch versions pinned by vLLM's own release, fast to iterate (no
    Python install step). "bare_metal" pip-installs vllm into a venv and runs
    it as a systemd service instead — no Docker layer at all, but first boot
    is SLOWER (compiling/downloading the CUDA-enabled torch wheel takes
    longer than pulling a prebuilt image) and you own matching CUDA/driver/
    torch versions yourself. See the GPU/LLM guide's "Docker vs bare metal"
    section before switching.
  EOT
  type        = string
  default     = "docker"

  validation {
    condition     = contains(["docker", "bare_metal"], var.run_mode)
    error_message = "run_mode must be \"docker\" or \"bare_metal\"."
  }
}

variable "vllm_image_tag" {
  description = "Tag of the vllm/vllm-openai Docker image. Only used when run_mode = \"docker\". \"latest\" drifts — pin a specific version (e.g. \"v0.6.3\") once you've validated it works for your model."
  type        = string
  default     = "latest"
}

variable "vllm_pip_version" {
  description = "Version pin for `pip install vllm==<this>`. Only used when run_mode = \"bare_metal\". Empty string installs whatever's latest on PyPI at boot time (drifts, same tradeoff as vllm_image_tag = \"latest\")."
  type        = string
  default     = ""
}

variable "max_model_len" {
  description = "Max context length (tokens) vLLM will accept. Directly trades off against KV-cache capacity (= max concurrent sequences) — see the GPU/LLM guide's VRAM math."
  type        = number
  default     = 8192
}

variable "gpu_memory_utilization" {
  description = "Fraction of GPU VRAM vLLM is allowed to claim for weights + KV cache (0.0-1.0). Leave headroom below 1.0 for CUDA overhead."
  type        = number
  default     = 0.90
}

variable "dtype" {
  description = "Weight/activation precision. \"auto\" uses the model config's native dtype (bfloat16 for Qwen2.5)."
  type        = string
  default     = "auto"
}

variable "quantization" {
  description = "vLLM quantization method (e.g. \"awq\", \"gptq\", \"fp8\") — only valid if model_id points at a pre-quantized checkpoint. Empty = unquantized."
  type        = string
  default     = ""
}

variable "shm_size_gb" {
  description = "Docker shared-memory size in GB. Docker's default (64MB) is too small for vLLM/NCCL and WILL crash the container — see the GPU/LLM guide's gotchas section."
  type        = number
  default     = 8
}

variable "hf_token" {
  description = "Hugging Face access token. Only needed for gated models (Qwen2.5 is not gated) — leave empty otherwise."
  type        = string
  default     = ""
  sensitive   = true
}

variable "vllm_api_key" {
  description = "If set, vLLM requires \"Authorization: Bearer <this>\" on every request. Empty = the API is open to anyone who can reach the port — see allowed_api_cidr."
  type        = string
  default     = ""
  sensitive   = true
}

##############################################################################
# GPU capacity — priority-ordered fallback list
##############################################################################
variable "gpu_instance_types" {
  description = <<-EOT
    Instance types in TRY-THIS-FIRST order. The ASG's mixed_instances_policy
    uses "prioritized" on-demand allocation: it attempts index 0 first, and
    only falls through to the next entry if THAT type has no capacity in the
    chosen subnets/AZs at launch time. Default order: L4 (g6) first, A10G
    (g5) as the fallback — exactly the "L4, else A10" behavior requested.
  EOT
  type        = list(string)
  default     = ["g6.2xlarge", "g6.xlarge", "g5.2xlarge", "g5.xlarge"]
}

variable "use_spot" {
  description = "Run on Spot capacity (up to ~70% cheaper) instead of On-Demand. AWS can reclaim a Spot GPU instance with a 2-minute warning — fine for experimentation, a bad fit for anything serving live traffic."
  type        = bool
  default     = false
}

variable "root_volume_size_gib" {
  description = "Root gp3 volume size — holds the OS, Docker image (~10GB), and the Hugging Face model cache. 150GB covers several 7B-class models cached side by side."
  type        = number
  default     = 150
}

##############################################################################
# Access — SSH key pair (PEM) + network exposure
##############################################################################
variable "create_key_pair" {
  description = "If true, Terraform generates a fresh SSH key pair (tls_private_key) and registers the public half with AWS. See the GPU/LLM guide's \"Managing the .pem file\" section before turning this off."
  type        = bool
  default     = true
}

variable "existing_key_pair_name" {
  description = "Name of an EC2 key pair ALREADY registered in this account/region. Only used if create_key_pair = false."
  type        = string
  default     = ""
}

variable "allowed_ssh_cidr" {
  description = "CIDR allowed to reach port 22 (SSH, using the generated .pem). Narrow this to your own IP/32 — see the GPU/LLM guide."
  type        = string
  default     = "0.0.0.0/0"
}

variable "allowed_api_cidr" {
  description = "CIDR allowed to reach port 8000 (the vLLM OpenAI-compatible API). 0.0.0.0/0 is convenient for a lab and WRONG for anything real — narrow it, or set vllm_api_key, or both."
  type        = string
  default     = "0.0.0.0/0"
}

variable "assign_public_ip" {
  description = "Give the instance a public IP directly. false = reach it only via SSM port-forwarding or from inside the VPC (see the GPU/LLM guide)."
  type        = bool
  default     = true
}

variable "extra_tags" {
  description = "Additional tags merged into the default tag set."
  type        = map(string)
  default     = {}
}
