# Training journey: books corpus -> 50m on MPS -> 153m on an L4

A running log of one end-to-end pass through this project's from-scratch GPT stack:
building a books-only corpus, training the 50m model locally on Apple Silicon,
diagnosing why loss plateaus, then scaling to 153m on a rented GCP L4 GPU for a
direct size comparison at matched data exposure. Written in the order it actually
happened, mistakes included — see docs/BOOKS_CORPUS_INTEGRATION.md and
docs/MIGRATION.md for the mechanisms this log exercises.

## 1. Building a books-only corpus (custom-gpt-50m)

Source: `~/Downloads/books` — 665 real PDF/EPUB files (~4.4GB). Extracted with the
Rust `tools/corpus-extractor` (`cargo build --release`, ~2m29s):

```bash
corpus-extractor extract --input ~/Downloads/books --output data/books_staging \
  --extensions pdf,epub --chunk-tokens 1024 --chunk-overlap 100 --no-split
```

Result: 1,002/1,103 files extracted OK (101 failed — malformed PDFs, cleanly
skipped), 133,795 chunks kept after quality filtering and dedup. Chunk size
(1024 tokens, GPT-2 BPE, 100-token overlap) is chosen to match `context_length=1024`
so a single training window is likely to see one coherent chunk rather than
fragments of many.

The corpus was deliberately kept **books-only** — no chat/instruction datasets, no
Wikipedia, no code repos — to isolate what raw book prose alone teaches a
from-scratch model, and because `build_corpus()`'s normal path requires
downloading >=10 chat conversations even for a books-heavy run. Bypassed that with
a small one-off script (`scripts/build_books_profile.py`) that shuffles
(seed 42) and 90/10-splits the extracted chunks directly, joined by
`DOCUMENT_SEPARATOR`.

Tokenized result: **136.8M tokens** (123.1M train / 13.7M test).

```bash
uv run gpt-audit
# noise_line_rate=0.0007  ascii_ratio=0.9850  train/test overlap=0.0000
```

## 2. First 50m training run (Apple Silicon, MPS)

```
Model: 50m | 51,475,968 parameters | device=mps | attn_impl=sdpa
Budget: 1,000,000 steps x 1,024 tok = 1.02B tokens (19.9 tok/param, 8.32 epochs)
```

`19.9 tok/param` is right at the Chinchilla-optimal ~20 tokens/param rule of
thumb — but that budget requires cycling the 136.8M-token corpus **8.32 times**.
Repetition past ~3-4 epochs on a fixed small corpus gives diminishing (eventually
negative) returns rather than genuine new signal.

## 3. Duplicate-process incident

While this run was active, a second `gpt-train` was started manually from another
terminal against the same checkpoint. This project's own docs call out exactly this
failure mode: two processes resumed from the same checkpoint don't fail loudly,
they silently race to write `latest.pt`/`best.pt`, each getting roughly half the
GPU, and whichever saves last wins — discarding the other's progress. Caught via
`pgrep -f gpt-train` showing two PIDs; fixed with `make train-stop` (SIGINT, saves
`checkpoints/<label>/latest.pt`) on both before resuming once.

## 4. Precision experiment: does bf16 help on MPS?

`resolve_amp()`'s own code comment already predicts the answer: "MPS autocast is
not dependable, and without tensor cores there is nothing to win." Tested anyway,
resuming with `GPT_PRECISION=bf16`:

| | fp32 (early) | bf16 (resumed) |
|---|---|---|
| steps/sec | ~7.3 | ~6.5 |
| stability | — | no NaN, loss dropped normally |

No measurable speedup, confirming the code comment rather than contradicting it.
Reverted to fp32 (the tested default) and resumed training there.

## 5. Retargeting the step budget (`GPT_STEPS`)

At step ~132K (`est_epoch≈1.1`), eval loss had visibly plateaued (`best_test_loss`
crawling 3.619 -> 3.556 -> 3.550 -> 3.519 over 30K+ steps) while `lr=1.94e-04` was
still 97% of its `2.00e-04` peak — expected, since the cosine decay schedule is
computed against the *configured* `steps`, not against "epochs so far." Running the
full 1,000,000-step/8.32-epoch schedule as configured would mean ~5x more
repetition than this corpus size can usefully absorb.

Fix: since `train_cfg.steps` is read fresh from `GPT_STEPS` on every resume (not
stored in the checkpoint), the schedule can be retargeted without losing progress:

```bash
GPT_STEPS=400000 caffeinate -i uv run gpt-train   # ~3.33 epochs, schedule now
                                                    # actually completes there
```

`123,128,903 train tokens / 1024 tok/step ≈ 120,243 steps/epoch`, so
`400,000 steps ≈ 3.33 epochs` — a target the LR schedule can actually anneal
into instead of being cut off 87% before its decay curve finishes.

## 6. `make test` was never actually runnable

`gpt-qa-report` (`make test`) failed on a fresh checkout: `data/prompt.jsonl` — the
file the whole QA prompt set loads from — was never committed to git (not
gitignored, just never added). Fixed by authoring it directly: 7 chat-source
"mirror" categories (each gated on `data/raw/<slug>` existing, so they
self-skip correctly on a books-only checkpoint with no chat data downloaded), one
real "Books" mirror category, 8 capability-probe categories (reasoning, coding,
agentic planning, safety, self-knowledge, ...), and a parameter-sweep pool.
Verified with `gpt-qa-report --cpu --per-category-limit 1` while training held the
GPU.

## 7. Standing up custom-gpt-153m with the same data

Goal: train 153m on the *same* books corpus at the *same* epoch level (3.33
epochs) for a direct 50m-vs-153m comparison.

**Real gotcha caught before it caused silent corruption**: `custom-gpt-153m` uses a
different document-separator convention than 50m. 50m joins documents with GPT-2's
real `<|endoftext|>` special token; 153m's `prepare.py` docstring explains it
*tried* that and deliberately reverted to a plain `"\n\n"` — and its `dataset.py`
does not pass `allowed_special` for `<|endoftext|>`. Naively copying 50m's
`train.txt` into 153m would have left every one of ~120K document boundaries as 7
stray subword tokens (`<`, `|`, `end`, `of`, `text`, `|`, `>`) instead of a real
boundary signal. Fixed by reusing the same underlying extracted JSONL (extraction
is deterministic — same tool, same input, same chunk settings) but rebuilding
`train.txt`/`test.txt` with 153m's own `DOCUMENT_SEPARATOR`.

Second real gotcha: 153m's `TrainConfig` defaults (`batch_size=16`,
`precision="fp16"`) are explicitly tuned for **a rented 24GB GPU**, not a laptop —
its own `config.py` docstring says so and suggests `GPT_BATCH_SIZE=1` for local
smoke tests.

## 8. First 153m attempt on the Mac: OOM

Ran without the batch-size override:

```
Precision: torch.float16 | batch 16 x accum 4 = 64 seqs/update
RuntimeError: MPS backend out of memory (MPS allocated: 29.12 GiB, ... max allowed: 30.19 GiB)
```

Root cause was straightforward once the log was read carefully: the
`GPT_BATCH_SIZE=1` override had been dropped on that particular invocation, so it
silently fell back to the 24GB-GPU default on a 24GB *total-system-RAM* Mac already
running a second training process. Also silently changed the actual target: at
`batch_size=16`, "400,000 steps" means `400,000 x 16,384 tok = 6.55B tokens`
(**53.21 epochs**, not 3.33) — the same class of silent-rescale the project's own
`GPU_TRAINING.md` warns about ("changing `batch_size` without changing `steps`
silently rescales the entire run").

Fixed by passing all three overrides together every time:

```bash
GPT_BATCH_SIZE=1 GPT_PRECISION=fp32 GPT_STEPS=400000 caffeinate -i uv run gpt-train
```

This ran cleanly: `batch 1 x accum 4`, `Precision: fp32`,
`Budget: 400,000 microsteps x 1,024 tok = 0.41B tokens (3.33 epochs)` — matching
50m's target exactly.

## 9. Moving to a real GPU: GCP L4

~2.7 steps/sec on MPS for a 152.8M-param model was going to take a long time for a
meaningful comparison. Decision: rent an L4 for a few hours.

**Pre-flight checks before spending anything:**

```bash
gcloud compute instances list          # 0 running — nothing to reuse
gcloud compute accelerator-types list --filter="name~l4"   # available in us-central1-{a,b,c}
gcloud compute regions describe us-central1 --format=json  # NVIDIA_L4_GPUS quota: 1.0 limit, 0.0 used
```

Quota confirmed available before provisioning anything billable.

**VM created:**

```bash
gcloud compute instances create gpt153m-l4-train \
  --zone=us-central1-a --machine-type=g2-standard-8 \
  --image-family=pytorch-2-9-cu129-ubuntu-2204-nvidia-580 \
  --image-project=deeplearning-platform-release \
  --boot-disk-size=150GB --boot-disk-type=pd-balanced \
  --maintenance-policy=TERMINATE
```

`g2-standard-8` ties to exactly 1x L4 (GCP's G2 family has the GPU count baked
into the machine-type shape, no separate `--accelerator` flag needed). The
Deep Learning VM image family comes with the NVIDIA driver and CUDA toolkit
pre-installed — confirmed post-boot:

```
NVIDIA L4, 23034 MiB, driver 580.178.04
torch 2.9.1+cu129, cuda available: True, bf16 supported: True
```

## 10. Migration friction (and fixes)

- **Checkpoint transfer was too slow to be worth it.** `scp`'ing the 1.83GB
  `checkpoints/153m/latest.pt` was crawling at ~1.3 Mbps (~40MB in 4 minutes,
  projecting 3+ hours) — this Mac's upload bandwidth, not the VM's. Since the local
  153m checkpoint only had ~235 steps of progress (well under 1% of the 25,024-step
  GPU target), cancelled the transfer and started fresh on the GPU instead of
  waiting out a multi-hour transfer for negligible carried-over progress. The
  much smaller `.bin` corpus files (246MB + 27MB) had already synced fine.
- **`uv sync` failed on the VM**: `pyproject.toml` declares `readme = "README.md"`,
  which hadn't been synced (only `src/`, `pyproject.toml`, `uv.lock`, `Makefile`
  were). One more `gcloud compute scp` fixed it.
- **Backgrounding over a single non-interactive `gcloud compute ssh --command`
  hung** rather than detaching (the local wrapper never returned, even though
  `nohup ... &` was used remotely). Verified independently with a second, fresh SSH
  connection — `gpt-train` (PID 2462) was in fact running and progressing
  normally; the hang was cosmetic on the client side, not a training failure.

**Batch size / step count for the GPU run**, matching the same 0.41B-token /
3.33-epoch target as 50m and the (aborted) local 153m attempt, but at this
project's GPU-tuned `batch_size=16` instead of `batch_size=1`:

```
steps = 0.41B tokens / (16 x 1024 tok/step) = 25,024
```

```bash
GPT_BATCH_SIZE=16 GPT_STEPS=25024 GPT_PRECISION=bf16 nohup uv run gpt-train \
  > logs/train_stdout.log 2>&1 &
```

`bf16` chosen explicitly over 153m's hardcoded `fp16` default: bf16 keeps fp32's
exponent range (no `GradScaler` needed, no silent underflow) and the L4's Ada
Lovelace architecture supports it natively — the same reasoning `resolve_amp()`
already encodes for CUDA's `"auto"` path, just made explicit here since 153m's
default field is `"fp16"`, not `"auto"`.

## 11. `nvidia-smi` on the running job, explained

```
+-----------------------------------------------------------------------------------------+
| NVIDIA-SMI 580.178.04             Driver Version: 580.178.04     CUDA Version: 13.0     |
+-----------------------------------------+------------------------+----------------------+
| GPU  Name                 Persistence-M | Bus-Id          Disp.A | Volatile Uncorr. ECC |
| Fan  Temp   Perf          Pwr:Usage/Cap |           Memory-Usage | GPU-Util  Compute M. |
|=========================================+========================+======================|
|   0  NVIDIA L4                      Off |   00000000:00:03.0 Off |                    0 |
| N/A   77C    P0             70W /   72W |   21260MiB /  23034MiB |    100%      Default |
+-----------------------------------------+------------------------+----------------------+
| Processes:                                                                              |
|    0   N/A  N/A            2462      C   ...tom-gpt-153m/.venv/bin/python      21252MiB |
+-----------------------------------------------------------------------------------------+
```

Field-by-field, what this confirms about the run:

- **Driver 580.178.04 / CUDA 13.0** — matches what the Deep Learning VM image
  shipped with; nothing installed manually.
- **Persistence-M: Off** — the driver isn't kept resident between processes on
  this VM; irrelevant for a single long-running job like this one.
- **Temp 77C** — hot but within the L4's normal operating range under sustained
  100% load; not throttling.
- **Perf: P0** — the GPU's highest performance state (P-states run P0 = max
  performance down to P8 = idle). Confirms it's actually working, not idling
  between kernel launches.
- **Pwr: 70W / 72W cap** — drawing essentially its full power budget. The L4 is a
  72W-TDP card (deliberately low-power for its performance class, unlike a
  300W+ A100), and this run is using essentially all of it — a good sign there's
  no host-side bottleneck (data loading, Python overhead) starving the GPU between
  steps.
- **Memory-Usage: 21260MiB / 23034MiB (~92%)** — model weights + optimizer state
  (Adam: 2x moment buffers) + activations for `batch_size=16 x context=1024` are
  using nearly the whole 24GB card. Confirms `batch_size=16` was a good fit for
  this GPU (the project's own tuned default, for exactly this reason) —
  meaningfully larger would risk OOM, smaller would leave VRAM (and throughput)
  on the table.
- **GPU-Util: 100%** — the single most important field for "is this a good use of
  rented time": the GPU's compute pipeline is saturated, not waiting on the CPU or
  disk. If this were sitting at, say, 40%, it'd mean the host-side data pipeline
  (memmapped `.bin` reads, batch assembly) was the bottleneck, not the GPU — not
  the case here.
- **Process table**: exactly one process (PID 2462, this project's own venv
  Python) owns essentially all GPU memory — confirms no duplicate-process race
  like the one caught locally in step 3.

## 12. Status at time of writing

```
step 716/25,024  (~3%, est_epoch=0.095)
~1.45-1.49 steps/sec
test_loss: 10.99 (step 0) -> 6.01 (step 500)
lr at peak: 4.00e-04
```

At this pace the full 25,024-step/3.33-epoch target projects to **~5 hours**, not
the originally planned 2. Plan: let it run for the ~2-hour rented window, sync back
whatever checkpoint state exists at that point (`docs/MIGRATION.md`'s
cloud-GPU-to-Mac rsync/scp flow), and decide from there whether to extend the
rental or call the comparison at partial epoch coverage.

Progress continued past the initial snapshot above: by step 5,414 (~1h09m in,
`est_epoch=0.72`), `test_loss` had dropped cleanly through every eval —
10.99 -> 4.40 -> 4.29 -> 4.06 -> 3.95 -> 3.79 -> 3.73 (`improved=1` on every row,
no plateau yet), `lr` past its `4.00e-04` peak and into cosine decay.

## 13. Beyond manual `nvidia-smi`: Cloud Ops Agent / DCGM metrics

Every GPU check in this log so far was a manual `gcloud compute ssh --command
"nvidia-smi"` — a point-in-time snapshot, not a history. **Not installed on this
VM** (`systemctl is-active google-cloud-ops-agent` -> `inactive`, no `dcgmi`
present) — documented here as the reference for what a real always-on setup would
add, worth doing before a multi-hour+ rental rather than after.

Installing the [Ops Agent](https://cloud.google.com/monitoring/agent/ops-agent)
with its NVIDIA DCGM (Data Center GPU Manager) integration turns each `nvidia-smi`
field checked by hand into a continuous **time series in Cloud Monitoring** —
graphable, alertable, and queryable after the fact instead of only "whatever it
said the moment you happened to SSH in."

### v1 metrics

| Metric | Kind | Value | Labels |
|---|---|---|---|
| `dcgm.gpu.profiling.sm_utilization` | GAUGE | DOUBLE | gpu_number, model, uuid |
| `dcgm.gpu.profiling.sm_occupancy` | GAUGE | DOUBLE | gpu_number, model, uuid |
| `dcgm.gpu.profiling.pipe_utilization` | GAUGE | DOUBLE | gpu_number, model, pipe, uuid |
| `dcgm.gpu.profiling.dram_utilization` | GAUGE | DOUBLE | gpu_number, model, uuid |
| `dcgm.gpu.profiling.pcie_traffic_rate` | GAUGE | INT64 | direction, gpu_number, model, uuid |
| `dcgm.gpu.profiling.nvlink_traffic_rate` | GAUGE | INT64 | direction, gpu_number, model, uuid |

(prefixed `workload.googleapis.com/` in Cloud Monitoring.)

### v2 metrics

| Metric | Kind | Value | Labels |
|---|---|---|---|
| `gpu.dcgm.utilization` | GAUGE | DOUBLE | gpu_number, model, uuid |
| `gpu.dcgm.sm.utilization` | GAUGE | DOUBLE | gpu_number, model, uuid |
| `gpu.dcgm.pipe.utilization` | GAUGE | DOUBLE | gpu_number, model, pipe, uuid |
| `gpu.dcgm.codec.encoder.utilization` | GAUGE | DOUBLE | gpu_number, model, uuid |
| `gpu.dcgm.codec.decoder.utilization` | GAUGE | DOUBLE | gpu_number, model, uuid |
| `gpu.dcgm.memory.bytes_used` | GAUGE | INT64 | gpu_number, model, state, uuid |
| `gpu.dcgm.memory.bandwidth_utilization` | GAUGE | DOUBLE | gpu_number, model, uuid |
| `gpu.dcgm.pcie.io` | CUMULATIVE | INT64 | direction, gpu_number, model, uuid |
| `gpu.dcgm.nvlink.io` | CUMULATIVE | INT64 | direction, gpu_number, model, uuid |
| `gpu.dcgm.energy_consumption` | CUMULATIVE | DOUBLE | gpu_number, model, uuid |
| `gpu.dcgm.temperature` | GAUGE | DOUBLE | gpu_number, model, uuid |
| `gpu.dcgm.clock.frequency` | GAUGE | DOUBLE | gpu_number, model, uuid |
| `gpu.dcgm.clock.throttle_duration.time` | CUMULATIVE | DOUBLE | gpu_number, model, uuid, violation |
| `gpu.dcgm.ecc_errors` | CUMULATIVE | INT64 | error_type, gpu_number, model, uuid |

(prefixed `workload.googleapis.com/` in Cloud Monitoring; v2 is the current schema —
prefer it over v1 for new setups.)

### How these map to what section 11's manual check already showed

| Manual `nvidia-smi` field | Closest DCGM metric | What the metric adds over the manual snapshot |
|---|---|---|
| `GPU-Util: 100%` | `gpu.dcgm.utilization` / `sm_utilization` | Continuous graph, not one instant — catches a mid-run stall (e.g. a data-loading hiccup) that a single SSH check would miss entirely. |
| `Memory-Usage: 21260/23034MiB` | `gpu.dcgm.memory.bytes_used` (labeled by `state`) | Time series over the run, so a slow memory-growth leak (e.g. `past_kv` accumulating somewhere it shouldn't) shows as a trend, not just "currently fine." |
| `Temp: 77C` | `gpu.dcgm.temperature` | Same data, graphed — useful for spotting thermal throttling onset before it visibly slows `steps/sec`. |
| `Pwr: 70W/72W` | *(no direct instantaneous-power metric in this list)* | `gpu.dcgm.energy_consumption` is cumulative joules, not instantaneous watts — integrate over a time window to reconstruct average power draw. |
| *(not visible in `nvidia-smi` at all)* | `gpu.dcgm.sm_occupancy` | **Warp occupancy**, not just "GPU busy" — distinguishes "100% util, but each SM is mostly idle waveslots" from genuinely saturated compute. More diagnostic than `GPU-Util` alone for judging if `batch_size` could go higher. |
| *(not visible in `nvidia-smi` at all)* | `gpu.dcgm.pipe_utilization` (per `pipe` label: fp32/fp64/tensor/...) | Breaks utilization down by execution pipe — would directly show whether bf16 training is actually hitting the L4's tensor cores (Ada) rather than falling back to a slower path, something section 11's plain `GPU-Util` can't distinguish. |
| *(not visible in `nvidia-smi` at all)* | `gpu.dcgm.clock.throttle_duration.time` (per `violation` label) | Cumulative time spent throttled, broken out by *why* (power/thermal/reliability limit) — turns "is it throttling?" from a guess into a number. |
| *(not visible in `nvidia-smi` at all)* | `gpu.dcgm.ecc_errors` (per `error_type`) | Correctable/uncorrectable memory errors — silent data corruption risk that a plain `nvidia-smi` snapshot never surfaces at all. |

**Worth setting up if**: a rental stretches past a few hours, runs unattended
overnight, or this becomes a repeated (not one-off) workflow — the always-on
history and alerting pay for the setup time. **Not worth it** for a rental this
short and actively watched, which is why it wasn't installed for this run.
