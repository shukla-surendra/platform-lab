# AWS Mastery — Master Progress & Resume Tracker

> **This file is the single source of truth for the whole journey.**
> To resume in any new session, read this file first. It says exactly where we are,
> what's next, and how the learning contract works. Everything else is detail.

**Owner:** xxx xxxxxxxxxxx · **Started:** 2026-07-12 · **Mode:** one service at a time, architecture/internals depth (NOT cert-oriented).

---

**Repo layout:** three cloud tracks — `aws/` (active), `azure/` (active, kicked off
2026-08-08), and `gcp/` (planned, now sequenced *after* Azure — see reasoning in the
Changelog). Each holds `docs/`, `quizzes/`, `terraform/`, `labs/`, etc. Shared docs tooling
lives in `scripts/` + `Makefile` at the root (`make docs` renders all Markdown to a themed
HTML site; `make check` validates links). Also at the root:
[`aws-to-azure-transition-guide.md`](aws-to-azure-transition-guide.md) — a standalone
(non-gated) service-mapping + mental-model bridge doc for Azure, written *before* the
`azure/` track existed and still useful as a fast reference — and
[`aws-to-azure-migration-strategy.md`](aws-to-azure-migration-strategy.md), a 200-service
migration plan built on top of it.

## 0. How to resume (read this first every session)

1. Open this file → find **Current Position** (§3).
2. Open the current service's docs under `<cloud>/docs/<service>/` and the open gate under `<cloud>/quizzes/<service>/`.
3. If a gate is **OPEN**, the learner answers the gate questions; the mentor grades, patches gaps, then advances.
4. Mentor updates §3 (Current Position) and §4 (Changelog) after every module/gate.

**Learning contract (do not violate):**
- One service at a time. **Do NOT advance to the next module until the current gate is cleared.**
- Each service is delivered as ~4–6 **progressive gated modules** (the 21-section spec below, chunked for retention — never a single 20k-word dump).
- Tag every internal claim **[Documented]** (docs / re:Invent / patents / whitepapers) vs **[Inferred]** (reconstruction from behavior). The learner must never mistake reconstruction for fact.
- Relate every AWS internal back to **Linux, Kubernetes, networking, and distributed-systems** primitives the learner already knows.
- **Why before How**, always. Never oversimplify, never skip internals.
- Scaffold the repo **incrementally** — create folders/files as each service/module is covered, not empty placeholders upfront.
- After each module: stop, quiz (conceptual + scenario + predict-behavior), wait for answers, grade, then continue.

---

## 1. The 21-section teaching spec (applied to every service)

Every service is taught to this depth, distributed across its modules:

1. Why the service exists (problem, history, prior solutions, why insufficient, why AWS built it, what if it didn't exist)
2. Internal architecture (request flow, networking, storage, metadata, control/data plane, replication, scaling, availability, consistency, failure recovery, multi-region, HA, fault tolerance)
3. How AWS built it (internal services, distributed-systems concepts, databases, storage engines, consensus, queues, networking, scheduling, caching, load balancing, security)
4. Deep networking (packet flow, DNS, routing, TCP, TLS, NAT, IGW, private networking, ENI, SGs, NACLs)
5. Storage architecture (physical/logical, placement, replication, partitioning, sharding, compression, encryption, perf)
6. Security (IAM, authN, authZ, encryption, KMS, secrets, certs, least privilege, cross-account, threat models)
7. Performance (throughput, latency, limits, bottlenecks, scaling, benchmarking, cost vs perf)
8. Real production architecture (Netflix/Uber/Airbnb/Amazon/Spotify/Databricks/banks/healthcare/e-commerce)
9. Best practices (prod configs, mistakes, anti-patterns, design/security recs, operational excellence)
10. Cost optimization (billing, pricing, hidden costs, monitoring, savings, reserved, spot, lifecycle)
11. Monitoring (CloudWatch, logs, metrics, tracing, dashboards, alarms, EventBridge, Config, CloudTrail)
12. Hands-on labs (beginner→expert + architecture/production/failure/perf/cost/security; each: objectives, architecture, implementation, validation, cleanup)
13. Coding (Python/Boto3 preferred, Terraform, AWS CLI, CloudFormation, CDK-Python, Shell)
14. Debugging (common failures, diagnosis, CloudWatch/logs/metrics, CLI, networking, IAM, perf)
15. Interview prep (junior/senior/principal, architecture, scenario, incident)
16. Comparison (Azure, GCP, Kubernetes, traditional infra, open-source alternatives)
17. Internal implementation (CAP, Paxos/Raft, leader election, consistent hashing, quorum, caching, distributed locking, eventual consistency, vector clocks, LSM/B-trees, bloom filters, WAL, object storage, network/virtualization, hypervisors, Firecracker, Nitro)
18. Sources (AWS docs, GitHub, blogs, whitepapers, research papers, eng blogs, OSS, RFCs, books)
19. Visual learning (architecture/flow/sequence/network/storage diagrams, comparison tables, mind maps)
20. Knowledge check (conceptual + scenario + debugging; gate — don't continue until correct)
21. Repo structure (docs / diagrams / terraform / cloudformation / cdk / boto3 / python / labs / quizzes / cheatsheets / notes)

---

## 2. Curriculum roadmap (service order)

Order is chosen for dependency + distributed-systems richness. Adjustable anytime.
**AWS is the primary track. Azure (`azure/`) is the second active track, taught by contrast
with AWS, sequenced ahead of GCP** — Microsoft is a Phase 1 target company in
`private_profile` (ready 2026-09-06) while Google is Phase 3 (ready 2026-11-01), so Azure is
the more time-urgent of the two. **GCP (`gcp/`) now starts after Azure**, still taught by
contrast with AWS once it begins.

### AWS track (`aws/`)

| # | Service | Status | Notes |
|---|---------|--------|-------|
| 1 | **VPC / Networking** | ⏸ Paused (docs complete) | Full doc set written; learner returning later with Q&A. |
| 2 | **EBS** | ✅ Docs complete | Block storage. Full 7-doc set + cheatsheet + Terraform + boto3 + labs. |
| 3 | **EFS** | ✅ Docs complete | File storage (NFS); full 6-doc set + cheatsheet + Terraform + boto3 + labs. |
| 4 | IAM | ⬜ Planned | Security substrate under every service. |
| 5 | S3 | ⬜ Planned | Object storage, durability math, erasure coding, consistency. |
| 6 | EC2 / Nitro | ⬜ Planned | Compute, Nitro cards, Firecracker, virtualization. |
| 7 | **Route 53** | 🟡 M1 delivered, gate OPEN | Started out of order (learner's explicit choice — see §3/§4). DNS internals, health checks, routing policies. |
| 7 | ELB (ALB/NLB) | ⬜ Planned | Load balancing internals, Hyperplane. |
| 8 | RDS / Aurora | ⬜ Planned | Aurora storage-compute separation. |
| 9 | DynamoDB | ⬜ Planned | Consistent hashing, quorum, streams. |
| 10 | Lambda | ⬜ Planned | Firecracker microVMs, cold starts. |
| … | (KMS, SQS/SNS, CloudFront, ECS/EKS, Kinesis, CloudWatch, Step Functions, …) | ⬜ Backlog | Sequenced later. |

### Azure track (`azure/`)

| # | Service | AWS contrast pair | Status | Notes |
|---|---------|--------------------|--------|-------|
| 1 | **Virtual Network (VNet)** | VPC | 🟡 M1 delivered, gate OPEN | `azure/docs/vnet/architecture.md` |
| 2 | Managed Disks | EBS | ⬜ Planned | Built on Blob Storage's Page Blobs (see #5) |
| 3 | Azure Files | EFS | ⬜ Planned | |
| 4 | **Microsoft Entra ID + Azure RBAC** | IAM (not yet written on AWS side) | 🟡 M1 delivered, gate OPEN | `azure/docs/entra-id/architecture.md` |
| 5 | **Blob Storage** | S3 | 🟡 M1 delivered, gate not yet written | `azure/docs/blob-storage/architecture.md` |
| 6 | Virtual Machines / Hyper-V | EC2 / Nitro | ⬜ Planned | |
| 7 | Azure DNS | Route 53 | ⬜ Planned | |
| 7 | Load Balancer / Application Gateway | ELB (ALB/NLB) | ⬜ Planned | |
| 8 | Azure SQL Database / Cosmos DB | RDS/Aurora / DynamoDB | ⬜ Planned | |
| 9 | Azure Functions | Lambda | ⬜ Planned | |
| … | Key Vault, Service Bus/Event Grid, Front Door/CDN, AKS, Azure Monitor | KMS, SQS/SNS, CloudFront, EKS, CloudWatch | ⬜ Backlog | Sequenced later. |

### GCP track (`gcp/`)

| # | Service | Status | Notes |
|---|---------|--------|-------|
| — | Starts after AWS **and Azure** core tracks | ⬜ Planned | Taught by contrast: GCP VPC (global) vs AWS VPC, GCP IAM (resource hierarchy) vs AWS IAM, GCS vs S3, GCE vs EC2. See `gcp/README.md`. |

Legend: ⬜ Planned · 🟡 In progress · ✅ Complete

---

## 3. CURRENT POSITION  ← resume here

- **Cloud / Service:** AWS · **EBS (#2) + EFS (#3) — both DOCS COMPLETE** (learner chose full doc set + hands-on). VPC (#1) paused, docs complete.
- **EBS deliverables:** `aws/docs/ebs/` = README + architecture, performance, snapshots-durability, security, best-practices, troubleshooting, interview · `aws/cheatsheets/ebs.md` · `aws/terraform/ebs/` (KMS + gp3/io2 + attach + DLM) · `aws/boto3/ebs/ebs_operations.py` · `aws/labs/ebs/README.md` (8 labs).
- **EFS deliverables:** `aws/docs/efs/` = README + architecture, performance, security, best-practices, troubleshooting, interview · `aws/cheatsheets/efs.md` · `aws/terraform/efs/` (encrypted FS + per-AZ mount targets + Access Point + TLS policy) · `aws/boto3/efs/efs_operations.py` · `aws/labs/efs/README.md` (8 labs).
- **Key framing used:** EBS = "network disk impersonating a local disk" (single-AZ, block, Physalia control plane, 2011 outage); EFS = "managed multi-AZ NFS" (mount targets = per-AZ ENIs, Access Points, Elastic throughput). Studied as a pair for the block-vs-file contrast.
- **Next (AWS):** await learner's Q&A on EBS/EFS. Candidates after: return to VPC Q&A, or service #4 (**IAM**) / **S3** (natural next storage). Terraform still not `validate`-d locally (no CLI); boto3 files compile.
- **Cloud / Service:** AWS · **Route 53 (#7) — M1 delivered, gate OPEN.** Started
  2026-08-22, **explicitly out of order** — learner asked to document Route 53 directly;
  flagged the conflict with "one service at a time" (IAM #4/S3 #5/EC2 #6 still Planned,
  untouched) and the gated-module contract, learner chose "start the real gated module"
  over a non-gated reference doc or sticking to the tracked order. Recorded here, same
  as the VNet precedent below — not silently reordered.
- **Route 53 deliverables so far:** `aws/docs/route53/architecture.md` (M1 — why Route 53
  exists vs. self-hosted/registrar/specialist DNS, the "DNS as a live control plane, not a
  static phone book" mental model, core terminology table, control/data-plane split, the
  100% SLA explained via that split, anycast + four-independent-TLD name-server redundancy,
  quorum-based health-checker consensus, Alias records and the zone-apex problem they
  solve) · `aws/quizzes/route53/module-1-gate.md` (4-question gate).
- **Key framing used:** DNS resolution chain and anycast are reused, not re-derived, from
  `fundamentals/system_design_foundation/00_prerequisite_concepts/09_dns_bgp_and_the_edge.md`
  (Route 53 = the authoritative link in that chain); the 100% SLA is tied to
  `13_cap_theorem_and_pacelc.md`'s framing (DNS answers differing by resolver is
  availability-favoring by design, not a consistency bug); health-check quorum is mapped
  against a Kubernetes liveness probe's `failureThreshold`, generalized from repeated
  observations by one observer to one observation each from many independent locations.
- **Next (Route 53):** learner clears the M1 gate; M2 covers deep routing-policy mechanics
  (Weighted/Latency/Failover/Geolocation/Geoproximity/Multivalue), DNSSEC, private hosted
  zones, and packet-level query flow.
- **Cloud / Service:** Azure · **VNet (#1) — M1 delivered, gate OPEN.** Kicked off
  2026-08-08, taught by contrast against the already-complete AWS VPC doc set.
- **VNet deliverables so far:** `azure/README.md` (track overview + planned service order)
  · `azure/docs/vnet/architecture.md` (M1 — why VNet exists, two-networks mental model, VFP +
  SmartNIC internals, NSG dual-attachment, subnet-not-AZ-pinned contrast) ·
  `azure/quizzes/vnet/module-1-gate.md` (5-question gate).
- **Key framing used:** VNet ≈ VPC's overlay/substrate model, but enforced via Microsoft's
  **VFP (Virtual Filtering Platform)** — a programmable match-action pipeline, not a
  separately-branded Mapping Service — hardware-offloaded via **SmartNIC/FPGA**
  (Azure's Nitro-equivalent). Two deliberate divergence points flagged for the gate: (1)
  **NSGs attach at subnet AND/OR NIC level**, both stateful, both must pass — genuinely
  different from AWS's stateless-NACL/stateful-SG split; (2) **Azure subnets are NOT
  AZ-pinned** — a VNet is regional like a VPC, but a single subnet can span every AZ in the
  region, inverting the "one subnet per AZ" AWS default.
- **2026-08-08, later same session — explicit deviation from "one service at a time":**
  learner asked to add IAM/storage/data docs while VNet's gate was still open. Flagged the
  conflict with the learning contract; learner chose to answer the VNet gate live in chat,
  then instead said "follow plan, and implement" without answering it. Read as: proceed
  breadth-first, VNet M1 gate stays **deliberately open** (not silently dropped — recorded
  here). Delivered **Entra ID + Azure RBAC (#4)** M1 (`azure/docs/entra-id/architecture.md`,
  gate `azure/quizzes/entra-id/module-1-gate.md` — Actions/DataActions split, Managed
  Identity types, App Registration vs. Service Principal, Conditional Access) and **Blob
  Storage (#5)** M1 (`azure/docs/blob-storage/architecture.md` — Storage Account as the
  shared home for Blob/Table/Queue/File, the SOSP 2011 Front-End/Partition/Stream
  architecture, strong-consistency-vs-S3 history, redundancy-vs-access-tier axes; gate not
  yet written). **Three Azure gates now open/pending simultaneously** — VNet, Entra ID, and
  Blob Storage's still-unwritten one. This is tracked debt, not an oversight; clear
  opportunistically or in a batch when the learner is ready.
- **Next (Azure):** clear the backlog of open gates (VNet M1, Entra ID M1) whenever the
  learner is ready — batching all outstanding gates in one sitting is a reasonable option
  given three are now open at once. Write Blob Storage's M1 gate. Then continue either
  deeper (VNet M2 — Effective Routes, peering, Private Link) or wider (Azure Files #3,
  Managed Disks #2 — note the Page Blob connection to Blob Storage already documented).

### VPC per-module plan

| Module | Topic | Target file(s) | Status |
|--------|-------|----------------|--------|
| M1 | Why VPC exists · two-networks mental model · internal architecture (Mapping Service, Nitro data plane, Blackfoot edge, distributed stateful SGs) | `aws/docs/vpc/architecture.md` | ✅ Delivered · gate OPEN |
| M2 | Deep packet flow · DNS · routing · IGW/NAT · peering/TGW/endpoints/PrivateLink · **Terraform 3-tier VPC** | `aws/docs/vpc/networking.md`, `aws/terraform/vpc/` | ✅ Written · gate OPEN (`module-2-gate.md`) |
| M3 | Security Groups vs NACLs internals · ENI deep-dive · Nitro enforcement · VPC Flow Logs · threat models | `aws/docs/vpc/security.md`, `aws/docs/vpc/internals.md` | ✅ Written |
| M4 | Advanced connectivity · multi-account/HA · real production architectures · cost · monitoring | `aws/docs/vpc/best-practices.md` | ✅ Written |
| M5 | Debugging (connectivity chain, Reachability Analyzer, Flow Logs) · Terraform | `aws/docs/vpc/troubleshooting.md`, `aws/terraform/vpc/` | ✅ Written (labs/boto3 TODO) |
| M6 | Interview drills (junior→principal, scenarios, incidents) · cheatsheet | `aws/docs/vpc/interview.md`, `aws/cheatsheets/vpc.md` | ✅ Written (Azure/GCP/K8s comparison TODO) |

---

## 4. Changelog

- **2026-07-12** — Project kicked off. Chose VPC as service #1, progressive gated modules, scaffold-as-we-go. Delivered VPC M1 (`aws/docs/vpc/architecture.md`); opened M1 gate.
- **2026-07-12** — Reorganized into `aws/` + `gcp/` tracks (moved docs under `aws/`). Copied docs tooling from the `python-debugging` repo — `scripts/build_docs.py`, `scripts/check_links.py`, `Makefile`, `.gitignore` — and rebranded the generated site to "AWS & GCP Mastery". Added `requirements.txt`.
- **2026-07-12** — Expanded AWS docs: wrote VPC **M2** (`networking.md` — building blocks, routing, IGW/NAT/endpoints/peering/TGW/DNS packet flows) + a runnable **Terraform 3-tier VPC** (`aws/terraform/vpc/`, 8 files). Added M2 gate (6 Q). Added Terraform ignores to `.gitignore`. Links validated (8 files), site builds. Terraform not installed locally → not `validate`-d yet.
- **2026-07-12** — Overhauled the docs-site UI (`scripts/build_docs.py`): persistent collapsible left-nav sidebar (grouped by track/service, with live filter + `/` shortcut), breadcrumbs, prev/next pager, reading-progress bar, mobile drawer, no-flash theme boot, and auto-styled [Documented]/[Inferred] badges. Verified: 131 internal HTML links resolve, markdown link-check passes.
- **2026-07-12** — **Completed the full VPC documentation set** so the learner can study end-to-end: added `internals.md`, `security.md`, `best-practices.md`, `troubleshooting.md`, `interview.md`, a `docs/vpc/README.md` index (study order), and `cheatsheets/vpc.md`. Every doc has an inline Self-check. Learner will review then ask questions.
- **2026-07-12** — Pivoted to storage (VPC paused). Built **EBS (#2)** and **EFS (#3)** as a pair, each with the **full doc set + hands-on** (learner's choice): 7 EBS docs + 6 EFS docs, two cheatsheets, Terraform modules (`terraform/ebs`, `terraform/efs`), boto3 scripts (`boto3/ebs`, `boto3/efs`), and lab guides (`labs/ebs`, `labs/efs`, 8 labs each). Framing: EBS = network-disk/single-AZ/Physalia; EFS = managed multi-AZ NFS/mount-targets/Access-Points. Links validated; boto3 compiles; site builds.
- **2026-08-08** — **Started the Azure track (`azure/`)**, full gated rigor matching `aws/` (learner's explicit choice over a lighter standalone-doc option). Re-sequenced the roadmap: Azure now runs *ahead of* the previously-planned GCP track, because Microsoft (Phase 1, ready 2026-09-06) is more time-urgent than Google (Phase 3, ready 2026-11-01) per `private_profile`'s dated plan — GCP still starts after AWS+Azure, unchanged in kind, just pushed later in order. Chose **VNet as Azure service #1**, mirroring VPC's role as AWS service #1, specifically so the module can teach *by contrast* against the already-complete `aws/docs/vpc/` set rather than from zero. Delivered VNet **M1** (`azure/docs/vnet/architecture.md`) — sourced from Microsoft Research's VFP (NSDI 2017) and SmartNIC/Accelerated-Networking (SIGCOMM 2015) papers for the internals, plus Microsoft Learn for the NSG dual-attachment and subnet/AZ behavior — and opened the M1 gate (`azure/quizzes/vnet/module-1-gate.md`, 5 questions). Added `azure/README.md` (track overview, planned 10-service order mirrored against AWS's own order). Updated `gcp/README.md` and root `README.md` to reflect three tracks instead of two.
- **2026-08-22** — **Started Route 53 (#7) out of order**, learner's explicit choice after the conflict with "one service at a time" (IAM #4/S3 #5/EC2 #6 still untouched) and the "never a single dump" rule was flagged — offered a non-gated quick-reference doc or sticking to the tracked order as alternatives; learner chose the real gated module. Delivered **M1** (`aws/docs/route53/architecture.md`) — why Route 53 exists (pre-2010 self-hosted/registrar/specialist-DNS landscape, the zone-apex CNAME problem), the "DNS as a live control plane" mental model, a core-terminology table (hosted zone, record set, routing policy, TTL, Alias, NS/SOA, health check, Traffic Flow), control/data-plane split explaining the 100% SLA, anycast + four-independent-TLD name-server redundancy, health-checker quorum, and Alias records — and opened the M1 gate (`aws/quizzes/route53/module-1-gate.md`, 4 questions). Cross-referenced rather than re-derived: anycast and the DNS resolution chain from `fundamentals/.../09_dns_bgp_and_the_edge.md`, the availability-over-consistency framing from `fundamentals/.../13_cap_theorem_and_pacelc.md`. Updated the AWS roadmap table (§2) and Current Position (§3) to reflect the jump, same pattern as the VNet precedent above.
- **2026-09-04** — **Real Azure account opened, $200 free credit.** Learner's stated goal: understand Azure permissions first, then host a web application on Kubernetes (AKS). No new module written — `private_profile`'s doc freeze (reps over documentation, through 2026-10-05) is in effect, and Entra ID/VNet already have unanswered M1 gates, so this logs a **session plan** rather than new curriculum:
  1. **Clear the open gates before touching real resources** — `azure/quizzes/entra-id/module-1-gate.md` (RBAC/permissions mental model, directly serves the stated goal) and `azure/quizzes/vnet/module-1-gate.md` (needed before AKS, since a cluster's networking sits on a VNet). Neither answered yet.
  2. **Cost guardrail, before any billable deployment** — install `az` CLI, `az login`, then set an Azure Cost Management budget alert (80%/100% of the $200 credit) on the subscription. Not yet done.
  3. **AKS itself is unwritten** — currently just a backlog line in the Azure service-order table (§2), no doc/gate/terraform. Stays that way unless explicitly requested as a written module (freeze applies); the working plan is to build it hands-on (Terraform + `kubectl`, no prose doc), taught by contrast against the general Kubernetes fundamentals already in `../k8s/` rather than re-deriving K8s from zero.
  4. **Then**: AKS cluster (Terraform) → container registry (ACR) → deploy a web app → tie back to Entra ID's Managed Identity / workload-identity content (§3c of the Entra ID doc) for how the app authenticates to other Azure services without stored credentials.

---

## 5. Repo structure (filled incrementally)

```
cloud-practice/
├── PROGRESS.md                 # THIS FILE — master tracker / resume anchor
├── README.md                   # overview + how to use
├── requirements.txt            # docs tooling deps (markdown-it-py)
├── Makefile                    # `make docs` (render+serve), `make check` (link-check+build)
├── scripts/
│   ├── build_docs.py           # renders every *.md in repo → themed HTML in docs_html/
│   └── check_links.py          # validates relative Markdown links (CI-friendly)
├── aws/                        # ── AWS track (active) ──
│   ├── docs/<service>/
│   │   ├── architecture.md     # why + mental model + internal architecture
│   │   ├── internals.md        # distributed-systems internals / algorithms
│   │   ├── networking.md       # deep packet flow, DNS, routing
│   │   ├── security.md         # IAM, SG/NACL, encryption, threat models
│   │   ├── best-practices.md   # prod configs, anti-patterns, cost, prod architectures
│   │   ├── troubleshooting.md  # debugging, common failures, diagnosis
│   │   └── interview.md        # junior→principal Q&A, scenarios
│   ├── diagrams/<service>/     terraform/<service>/   cloudformation/<service>/
│   ├── cdk/<service>/          boto3/<service>/        python/<service>/
│   ├── labs/<service>/         quizzes/<service>/      cheatsheets/   notes/
├── azure/                      # ── Azure track (active) — mirrors aws/, taught by contrast ──
│   ├── docs/<service>/         # same 7-doc shape as aws/docs/<service>/
│   ├── terraform/<service>/    # azurerm provider
│   ├── python/<service>/       # Azure SDK for Python — the azure/ analogue of aws/boto3/
│   ├── labs/<service>/         quizzes/<service>/      cheatsheets/
│   └── README.md
└── gcp/                        # ── GCP track (planned, after AWS + Azure) — mirrors aws/ ──
    └── README.md
```
Folders are created only when a service/module needs them (scaffold-as-we-go).
`docs_html/`, `.venv/`, and `__pycache__/` are git-ignored (generated / local).

**Cross-cutting references** (tool-general, not service-scoped) live at the repo root:
- [`Terraform-Complete-Reference/`](Terraform-Complete-Reference/README.md) — fundamentals, state/backends, project structure, variables + CI/CD (incl. variable-precedence and a pipeline YAML), internals & tool comparison. See its [README](Terraform-Complete-Reference/README.md) for the index.
