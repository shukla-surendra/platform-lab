# GPU Instances + LLM Serving — Concepts Behind the `vllm-gpu-serving/` Module

This is the "why," paired with that module's `README.md` ("how to run
it"). Read top to bottom the first time; it's ordered so each section
only depends on the ones before it.

## 1. AWS GPU instance families, and why L4/A10G for a 7B model

| Family | GPU | VRAM | Typical use | Roughly |
|---|---|---|---|---|
| `g4dn` | NVIDIA T4 | 16GB | Cheapest GPU inference, older architecture | $ |
| `g5` | NVIDIA A10G | 24GB | This module's fallback — solid general inference | $$ |
| `g6` | NVIDIA L4 | 24GB | This module's default — newer (Ada Lovelace), better perf/$ than A10G at the same VRAM, native FP8 support | $$ |
| `g6e` | NVIDIA L40S | 48GB | Bigger models (13B-34B class) on one GPU | $$$ |
| `p4d` | NVIDIA A100 | 40/80GB ×8 | Training, very large model inference, multi-GPU | $$$$ |
| `p5` | NVIDIA H100 | 80GB ×8 | Frontier-scale training/inference | $$$$$ |

For a **7B-parameter instruct model**, both L4 and A10G's 24GB is
comfortably enough (see the VRAM math below) — the choice between them
is price/performance, not capability. L4 (Ada Lovelace architecture) is
generally the better $/token choice for inference-only workloads and
supports FP8 natively; A10G (Ampere) is a very close second and often
has different capacity availability, which is exactly why it's this
module's fallback rather than a downgrade.

## 2. VRAM math — will a model actually fit?

The rule of thumb:

```
VRAM needed ≈ (params × bytes_per_param) + KV_cache_overhead + activation_overhead
```

- **Weights**: a 7B model in `bfloat16`/`float16` (2 bytes/param) is
  `7,000,000,000 × 2 bytes ≈ 14GB`. In `fp32` that doubles to ~28GB
  (won't fit on a 24GB card at all — this is WHY `dtype` matters).
  Quantized to 4-bit (AWQ/GPTQ), the same model's weights shrink to
  ~4-5GB.
- **KV cache**: grows with `max_model_len × concurrent_sequences ×
  num_layers × hidden_size × 2 (K and V) × bytes_per_param`. This is
  the part that's easy to forget — it's not a fixed cost, it scales with
  BOTH how long a context you allow (`max_model_len`) and how many
  requests vLLM is serving at once. Doubling `max_model_len` roughly
  doubles KV cache memory for the same concurrency.
- **Activations + CUDA overhead**: a few GB, roughly fixed regardless of
  model size.

Concretely for `Qwen/Qwen2.5-7B-Instruct` in `bfloat16` on a 24GB card:
~14GB weights leaves ~8-9GB (after `gpu_memory_utilization = 0.90`
headroom and CUDA overhead) for KV cache + activations — enough for
`max_model_len = 8192` (this module's default) at a handful of
concurrent requests. Push `max_model_len` to 32768 and you'll have room
for far fewer concurrent sequences before vLLM starts queueing.

## 3. vLLM concepts this module's flags map to

- **Continuous batching** — the core reason vLLM (or any serious
  inference server) beats "just call `model.generate()` in a loop."
  Instead of processing one request start-to-finish before starting the
  next, vLLM packs many in-flight sequences onto the GPU together, at
  the TOKEN level, not the request level: as soon as one sequence
  finishes, a queued one takes its slot immediately, without waiting for
  every other in-flight sequence to also finish. This is why
  `client/benchmark.py`'s throughput at concurrency 16 is nowhere close
  to 16× the concurrency-1 latency.
- **PagedAttention** — vLLM's memory manager for the KV cache. Instead
  of allocating one contiguous memory block per sequence (wasteful —
  you must reserve for the WORST-CASE length up front), it pages KV
  cache like an OS pages virtual memory: fixed-size blocks, allocated as
  a sequence actually grows, freed the instant it finishes. This is what
  lets vLLM pack meaningfully more concurrent sequences into the same
  VRAM than a naive implementation.
- **`--gpu-memory-utilization`** (`var.gpu_memory_utilization`) — the
  fraction of VRAM vLLM is allowed to claim total (weights + KV cache
  pool). Too high and you risk an out-of-memory crash under load; too
  low and you're leaving KV cache capacity (= concurrency) on the table.
- **`--max-model-len`** (`var.max_model_len`) — the hard ceiling on
  context length vLLM will accept per request. Set from the VRAM math
  above, not just "however long the model theoretically supports."
- **`--dtype`** (`var.dtype`) — `auto` uses the checkpoint's native
  dtype (`bfloat16` for Qwen2.5). Forcing `float16` can be faster on
  older GPUs that lack good `bfloat16` throughput; forcing `float32` is
  almost never what you want for inference (2× the memory, rarely
  meaningfully more accurate for serving).
- **`--quantization`** (`var.quantization`) — trades a small amount of
  output quality for either fitting a BIGGER model in the same VRAM, or
  freeing VRAM for MORE concurrent requests at the same model size.
  `awq` and `gptq` need a pre-quantized checkpoint (a different
  `model_id`, not a flag that quantizes an arbitrary model on the fly);
  `fp8` is natively supported by this module's default L4 GPU's Ada
  Lovelace architecture and is often the easiest first thing to try.
- **Tensor parallelism** (`--tensor-parallel-size`, not exposed as a
  variable here since this module is single-GPU) — splits ONE model
  across multiple GPUs, each holding a shard of every layer, needed once
  a model's weights alone exceed one GPU's VRAM (e.g. a 70B model). A
  future extension of this module toward `g6.12xlarge`/`p4d` with
  `tensor-parallel-size = 4` would be the natural next step past a
  single 7B-on-one-GPU setup.

## 4. Managing the `.pem` file

This is the part you asked about specifically — the full lifecycle, not
just "here's a key."

### What actually happens when `create_key_pair = true`

1. `tls_private_key` (Terraform, no AWS call) generates a 4096-bit RSA
   keypair **locally**, inside the Terraform run.
2. `aws_key_pair` registers only the **public** half with AWS — AWS
   never sees or stores your private key at all, by design (this is how
   EC2 key pairs have always worked, not specific to Terraform).
3. `local_sensitive_file` writes the **private** half to
   `vllm-gpu-serving/<project>-key.pem` on YOUR machine, with
   `file_permission = "0400"` (owner read-only — `ssh` itself refuses to
   use a key that's group- or world-readable, so this isn't optional
   politeness, it's a hard requirement).
4. The launch template's `key_name` references the registered public
   key, so EC2 injects it into the instance's `~ec2-user/.ssh/authorized_keys`
   at boot — standard cloud-init behavior, nothing this module does
   specially.

### Where it lives, and why it's safe to `apply` repeatedly
The file lands **next to this module**, and the repo's root
`.gitignore` has a blanket `*.pem` rule — `git status` will never show
it as untracked-and-ignorable-by-mistake. Re-running `terraform apply`
does NOT regenerate it (Terraform only recreates a resource whose inputs
changed); the same key persists across applies until you explicitly
force a new one.

### The real limitation: it's also in Terraform state, in plaintext
`terraform.tfstate` (also gitignored — see the root `.gitignore`'s
Terraform section) contains the full private key in plaintext, because
Terraform has to track what it created. For a solo lab this is fine —
your state file is local and gitignored either way. The moment you
introduce a **shared** remote state backend (S3 + DynamoDB locking, a
Terraform Cloud workspace, etc.) for a team, that plaintext key is now
readable by everyone with read access to that state. At that point,
either:
- Set `create_key_pair = false` and pass `existing_key_pair_name` — a
  key pair you generated and stored in a proper secret manager
  (`aws ec2 create-key-pair` writes the private half once, at creation,
  and AWS itself never stores it either — same trust model, just not
  Terraform-managed), or
- Prefer SSM entirely (next section) and skip key pairs altogether.

### If you lose the `.pem` file
AWS has no "recover my private key" — it was never stored server-side.
Your options, in order of how much you actually need SSH specifically:
1. **You don't actually need SSH** — use SSM (below) instead; nothing
   is lost.
2. **You need SSH and can tolerate a new key** — delete the local
   `.pem`, `terraform taint tls_private_key.this` (or
   `aws_key_pair.this`), `terraform apply` — a fresh key pair is
   generated and re-attached... except `key_name` changes only take
   effect on a NEW instance, not an already-running one (EC2 doesn't
   let you swap the key pair on a running box). Since this module's
   instance lives in an ASG, the practical fix is to also terminate the
   current instance (`aws autoscaling terminate-instance-in-auto-scaling-group
   --should-decrement-desired-capacity false`) so the ASG launches a
   replacement with the new key baked in.
3. **You specifically need the SAME instance without SSH** — use
   **EC2 Instance Connect** (console-based, temporary key injection, a
   separate AWS feature from key pairs) or SSM (below) to get in and
   append a new public key to `~/.ssh/authorized_keys` by hand.

### The recommended default: skip the PEM entirely with SSM
This module's IAM role already includes `AmazonSSMManagedInstanceCore`
(same pattern as `ec2/` and `autoscaling/`), so **you don't need the
`.pem` file for ordinary shell access at all**:
```bash
aws ssm start-session --target $(terraform output -raw instance_id)
```
No key to lose, no port 22 to expose, every session is IAM-authenticated
and logged in CloudTrail. This is why `ssm_command` is a dedicated
output — it's the path this module actually recommends day to day.

**SSM even replaces SSH for the one thing you might think needs it —
privately reaching the vLLM API without opening port 8000 to the
internet:**
```bash
aws ssm start-session \
  --target $(terraform output -raw instance_id) \
  --document-name AWS-StartPortForwardingSession \
  --parameters '{"portNumber":["8000"],"localPortNumber":["8000"]}'
# now http://localhost:8000/v1 on YOUR machine reaches the instance's vLLM server
```
With that running, you can set `allowed_api_cidr` to something narrow
(or even remove the 8000 ingress rule entirely) and still develop
against the API from your laptop — this is the actual production-safe
access pattern, not `0.0.0.0/0`.

### PEM vs. SSM — when each one actually wins
| | PEM / SSH | SSM |
|---|---|---|
| Setup | A key to generate, download, protect, and eventually lose | Already wired in — zero extra setup |
| Exposure | Needs port 22 open to *something* | Needs no inbound port open at all |
| Auditability | Whoever has the file can connect, forever, unlogged | Every session is IAM + CloudTrail logged |
| Revocation | Rotate the key pair (see above — annoying) | Revoke IAM permission — instant |
| `scp` a file to the box | Native, one command | Needs S3 as a hop, or SSM's own file transfer plugin |
| Tools that assume plain SSH (some IDEs' remote-dev, `rsync -e ssh`) | Just works | Needs an SSM-aware SSH ProxyCommand wrapper |

Keep the generated `.pem` (`create_key_pair = true`, this module's
default) if you'll use `rsync`/`scp`/an IDE's remote-SSH feature.
Set `create_key_pair = false` if you're comfortable with SSM alone —
one fewer credential to manage.

## 5. Cost control — a GPU-specific gotcha

Because this instance lives in an **Auto Scaling Group** (needed for the
L4→A10G fallback), you can't just `aws ec2 stop-instances` it to pause
billing the way you could with the standalone `ec2/` module — the ASG
will notice the "missing" instance and launch a replacement to get back
to `desired_capacity = 1`. To actually pause spending without destroying
everything:
```bash
aws autoscaling update-auto-scaling-group --auto-scaling-group-name <name> --desired-capacity 0 --min-size 0
# ...later, resume (re-downloads the model unless you added a persistent cache — see README's "Deliberately minimal"):
aws autoscaling update-auto-scaling-group --auto-scaling-group-name <name> --desired-capacity 1 --min-size 1
```
Or just `terraform destroy` and re-`apply` later — for a lab, that's
often simpler than remembering to scale back up.

## 6. Docker vs. bare metal — and why `vllm/vllm-openai` specifically

vLLM does **not** require a container. It's a normal `pip install vllm`
package with a CLI entrypoint (`vllm serve <model>`); `run_mode =
"bare_metal"` (this module's alternative to the `docker` default) does
exactly that inside a venv, run as a systemd service instead of a
container.

**Why the module defaults to Docker anyway.** vLLM is unusually
sensitive to its CUDA/driver/PyTorch versions all matching — install a
`torch` build compiled for a different CUDA version than the one the
NVIDIA driver on the box provides, and you get anything from a confusing
import error to silent GPU-detection failure. `vllm/vllm-openai` is the
**official image vLLM itself publishes**, with a known-good combination
of those three pinned per release, and its entrypoint is already the
OpenAI-compatible API server (`vllm.entrypoints.openai.api_server`) —
which is *why* it's `vllm/vllm-openai` and not a generic `vllm/vllm`:
the image is purpose-built for serving, not just "vLLM installed
somewhere." `docker run vllm/vllm-openai --model ... --max-model-len
...` passes flags straight through to that entrypoint — the image is a
thin, version-pinned wrapper, not a different interface.

**What each `run_mode` actually costs/gains you:**

| | `docker` (default) | `bare_metal` |
|---|---|---|
| First-boot time | Pulls a large prebuilt image (still several GB, but one layer-cached download) | `pip install vllm` resolves and downloads a CUDA-enabled `torch` wheel — often slower than the image pull, and network-flaky installs are the #1 bare-metal failure mode |
| Version matching | Guaranteed by vLLM's own release — you get exactly what they tested | Your responsibility — the DLAMI's driver version and PyPI's latest `vllm`/`torch` MUST be compatible, which isn't guaranteed forever |
| Iterating on the server itself | Edit `docker run` flags, `docker rm -f vllm && docker run ...` again | Edit `/etc/systemd/system/vllm.service`, `systemctl daemon-reload && systemctl restart vllm` |
| `--shm-size` gotcha (section 3) | Applies — Docker's default 64MB `/dev/shm` WILL crash vLLM/NCCL unless set | Doesn't apply at all — bare metal uses the host's own `/dev/shm`, normally sized generously |
| Debugging | `docker logs -f vllm`, `docker exec -it vllm bash` | `journalctl -u vllm -f`, or just `sudo -u ec2-user /home/ec2-user/vllm-venv/bin/python` directly |
| Disk footprint | Image layers (~10GB) + model cache | Venv + wheels (smaller than the image) + model cache |

**When to actually reach for `bare_metal`:** you're patching vLLM's own
source and need to `pip install -e .` against a git checkout, you want
to attach a Python debugger directly to the serving process, or you're
specifically trying to minimize what's installed on the box. For
"just serve a model reliably," Docker's version pinning is worth the
extra image size — which is why it's the default.
