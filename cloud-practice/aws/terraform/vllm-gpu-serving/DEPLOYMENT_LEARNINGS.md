# Deployment Learnings — Field Notes from a Real `apply`/`destroy` Cycle

Everything below happened on an actual deployment of this module
(2026-09-18, `us-east-1`, real AWS account), not in review. Kept
separate from `TEST_RESULTS.md` (which is "what the API returned") and
`GPU_AND_LLM_SERVING_GUIDE.md` (which is "the concepts") — this is
"what actually went wrong or was worth noticing while running it for
real," in the order it happened.

## 1. A real Terraform bug that `validate` never catches

`terraform validate` passed cleanly on this module every time it was
run during development. The FIRST real `terraform plan` against actual
AWS state failed:

```
Error: Invalid count argument
  on main.tf line 267, in data "aws_instance" "primary":
  267:   count = length(data.aws_instances.this.ids) > 0 ? 1 : 0
The "count" value depends on resource attributes that cannot be
determined until apply...
```

**Why `validate` missed it:** `validate` only checks syntax/types — it
never talks to AWS, so it never discovers that `data.aws_instances.this.ids`
is unknown until the ASG actually exists. **Why `plan` caught it:**
`plan` DOES evaluate against real state (or a real empty state on a
first run), so `count`'s dependency on a not-yet-created resource's
data-source output became a real, unresolvable question at plan time.

**Fix:** the module always expects exactly one instance (`desired_capacity
= 1`), so the conditional `count` was pure defensive scaffolding that
actively broke the common case. Removed it, kept `instance_id =
data.aws_instances.this.ids[0]` unconditional, and relied on `depends_on
= [aws_autoscaling_group.this]` to defer the READ itself until apply
time (after the ASG — and therefore the instance — exists). Lesson
generalizes: **`count`/`for_each` must never depend on a value that's
unknown until apply; `depends_on` on the data source is the right tool
for "wait until this resource exists," not a conditional count.**

## 2. "It's not accessible" ≠ "it's broken" — check the obvious layer first

When told the API URL wasn't reachable, the instinct was to suspect the
security group, the instance, or the Docker container. The actual
sequence of dead ends, in order:

1. Ran `aws ec2 describe-security-groups --group-ids sg-...` with no
   `--region` flag → `InvalidGroup.NotFound`. Same for the instance and
   the ASG. **This looked exactly like "everything got destroyed."**
2. Root cause: this shell's AWS CLI default region is `ap-south-1`
   (Mumbai); the deployment is in `us-east-1`. I was querying the wrong
   region entirely — nothing was destroyed. `terraform plan
   -refresh-only` (which correctly reads `region = var.region` from the
   provider block) confirmed everything still existed.
3. **Lesson: when a resource "disappears" right after a successful
   `apply`, check `--region` on your ad-hoc CLI commands before
   suspecting the infrastructure.** Terraform's own provider config is
   the source of truth for region; a bare `aws` CLI call falls back to
   whatever `~/.aws/config` or `$AWS_DEFAULT_REGION` says, which can
   silently differ.
4. Once region was fixed: instance `running`, security group correctly
   allowed port 8000 from the caller's IP, `curl` to `:8000` timed out
   anyway — but this was simply the model still loading (Docker image
   pull + 14GB HF download + `torch.compile` + CUDA graph capture, ~5
   minutes total). Confirmed via SSM (`docker logs -f vllm`) rather than
   guessing — watching the actual log is faster than re-running `curl`
   in a loop and wondering why it's still failing.
5. Once the server WAS up: a `curl` with an `Authorization` header still
   produced `"WARNING: Invalid HTTP request received."` server-side.
   Root cause: my own shell command extracted the API key with `grep
   vllm_api_key terraform.tfvars`, which matched BOTH the file's comment
   line (`# vllm_api_key -> generated, so...`) AND the real assignment
   line — the two grep matches got joined with an embedded newline in
   `$API_KEY`, and a newline inside an HTTP header value is exactly the
   kind of malformed request `h11`/uvicorn correctly rejects. Fixed by
   anchoring the extraction (`awk -F'"' '/^vllm_api_key/{print $2}'` —
   matches only a line that STARTS with the variable name, not a
   comment mentioning it). **Lesson: a "connection" failure and a
   "malformed request" failure look similar from the client side but
   have completely different causes — read the SERVER's log, not just
   the client's error, before assuming which one you're looking at.**

Net: zero of these were real infrastructure bugs. All three were
environment/tooling mismatches (region default, timing expectations,
shell extraction) — worth documenting precisely because they're the
kind of thing that wastes real debugging time by looking like
infrastructure failures.

## 3. What went right without any intervention

- **The L4→A10G fallback never had to activate** — `g6.2xlarge` had
  capacity on the first attempt, in this account, at this time. Worth
  remembering this is NOT proof the fallback logic works; it's proof
  the happy path works. The fallback itself is still only exercised by
  deliberately requesting an instance type with no capacity (see the
  GPU/LLM guide's mini-lab 1) — that wasn't tested this run.
- **SSM access worked with zero setup beyond the module's own IAM role**
  — no bastion, no VPN, no port 22 needed to debug the boot sequence.
- **The Docker path's version pinning paid off exactly as the guide
  argues**: `vllm/vllm-openai:latest` came up correctly against the
  DLAMI's driver on the first try, no CUDA/driver/torch mismatch to
  debug.
- **`--api-key` enforcement worked correctly out of the box** — every
  unauthenticated/wrong-key request was rejected before touching the
  model, confirmed in `TEST_RESULTS.md` §1.

## 4. Cost — the actual number, not the estimate

Instance ran from `2026-09-18T06:26:32Z` to teardown (`terraform
destroy` initiated shortly after the benchmark run in `TEST_RESULTS.md`
§5) — roughly 30-35 minutes total, entirely within a single hour of
`g6.2xlarge` on-demand billing (AWS bills per-second for EC2, with a
1-hour... actually no minimum beyond per-second billing for most
instance types, but check current billing terms). At the region's
on-demand rate for `g6.2xlarge` (check current AWS pricing — it moves),
this exercise cost a small fraction of one hour's rate — real, but
cheap for what it validated: a genuinely working GPU inference
deployment from a cold `apply`.

## 5. Process takeaway for next time

`terraform validate` is necessary but nowhere near sufficient for a
module using data sources that depend on resources created in the same
apply — **always run a real `plan` (and ideally a real `apply`) at
least once**, even when every file individually validates cleanly. The
`count`-argument bug in §1 would have shipped to anyone copying this
module otherwise.
