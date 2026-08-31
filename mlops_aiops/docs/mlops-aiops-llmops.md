# MLOps, AIOps, and LLMOps: definitions, origins, and where they actually diverge

Three terms that get used almost interchangeably in job titles and tool marketing, despite
solving genuinely different problems. This doc exists because this repo's own name
(`mlops_aiops_toolkits`) uses two of them side by side — worth being precise about what
each one actually is, who defines it, and where the boundaries blur in practice.

## The shared root problem, and why three separate terms exist

Whenever something built by one group (data scientists training models, engineers writing
code, IT teams running infrastructure) has to run reliably in production without someone
babysitting it, a gap opens between "it works once" and "it keeps working, unattended, at
scale." Each discipline below is a different answer to *which* gap it closes — same DNA
(apply operational discipline + automation to a domain that didn't traditionally have it),
different domain.

## MLOps

**The problem without it**: a data scientist trains a good model in a notebook. Months
later, nobody can reproduce it, nobody's certain which version is actually serving
production traffic, and it's quietly degraded because the input data shifted — none of
which looks like a crash, so nothing pages anyone.

**Origin.** No single clean "coiner" exists, verified rather than assumed — a commonly
repeated claim traces the term to Sculley et al.'s 2015 NeurIPS paper "Hidden Technical
Debt in Machine Learning Systems," but that paper documents the *operational problems* ML
systems have, not the term "MLOps" itself, and Wikipedia's own MLOps article doesn't credit
it as the coinage either. The closest thing to a canonical reference is **Google's 2020
whitepaper**, ["MLOps: Continuous Delivery and Automation Pipelines in Machine
Learning"](https://docs.cloud.google.com/architecture/mlops-continuous-delivery-and-automation-pipelines-in-machine-learning),
which defines MLOps as:

> "an ML engineering culture and practice that aims at unifying ML system development (Dev)
> and ML system operation (Ops)"

and lays out the most-cited maturity framework in the space:

| Level | Name | What it means |
|---|---|---|
| **0** | Manual process | Every step — data analysis, prep, training, validation — is manual and disconnected. Deployment is a human copying a model artifact somewhere. |
| **1** | ML pipeline automation | The training pipeline itself is automated, enabling **continuous training** as new data arrives — the goal shifts from "ship one model" to "keep retraining automatically." |
| **2** | CI/CD pipeline automation | A full CI/CD system automates build, test, and deployment of the *pipeline itself*, so data scientists can rapidly iterate on new ideas without manually re-wiring infrastructure each time. |

**Responsibilities**: data/feature versioning, experiment tracking, model registry,
training-pipeline automation, deployment/serving infrastructure, drift and performance
monitoring, retraining triggers.

**Tools already documented in this repo**:

- [Feast](tools/feast/README.md) — feature versioning/serving, the piece that keeps
  training and serving from silently drifting apart.
- [MLflow](tools/mlflow/README.md) — experiment tracking, model registry, model
  packaging/serving.
- [Evidently](tools/evidently/README.md) — drift detection and model-quality monitoring,
  the thing that catches the "quietly degraded" failure mode from the problem statement
  above.
- [KServe](../../k8s/k8s_explorer/practice/kserve-inference/README.md) — Kubernetes-native model
  serving with rollout safety (canary/shadow), covered conceptually in
  [`04_model_serving_deployment`](../../engineering_fundamentals/system_design_foundation/04_model_serving_deployment/tutorial.md).

## AIOps

**The problem without it**: a large distributed system throws thousands of log lines and
metric alerts during an incident, and a human has to manually correlate which of them are
the actual root cause versus noise — too slow to work at real scale, and exhausting even
when it does.

**Origin, verified against primary and analyst sources.** **Gartner coined the term in
2016**, specifically analyst **Colin Fletcher**, originally as "**Algorithmic** IT
Operations" — Gartner itself later shifted the expansion to "**Artificial Intelligence
for** IT Operations." Gartner's own current definition:

> "AIOps combines big data and machine learning to automate IT operations processes,
> including event correlation, anomaly detection, and causality determination."

Two things worth knowing that most casual explanations of AIOps skip:

- **Gartner retired the "AIOps Platforms" category in 2025**, folding it into "Event
  Intelligence Solutions" — reportedly because vendor overuse had diluted the term to the
  point of losing analytical usefulness as its own category.
- **Other analyst firms don't share Gartner's framing at all.** Forrester splits AIOps
  vendors into "process-centric" (Generation 1) vs. "technology-centric" (Generation 2)
  categories — a maturity/approach axis, not Gartner's platform-capability one. IDC's more
  recent material talks about "outcome-driven, agent-oriented architectures" and metrics
  like "mean time to known good" — yet another distinct lens. **Three analyst firms, three
  different definitions of the same word.** This is the single most practically important
  fact about AIOps: never assume shared scope when someone uses the term — ask what
  telemetry and what outcome they actually mean.

**Responsibilities**: log/metric/trace ingestion at scale, anomaly detection on
operational telemetry, event correlation across services, alert-noise reduction,
automated or human-assisted root-cause analysis, sometimes automated remediation.

**Tools already documented in this repo**: the entire
[`observability-on-eks.md`](observability-on-eks.md) stack — Prometheus, Grafana, Loki,
ELK/EFK, CloudWatch — is the **telemetry substrate** AIOps sits on top of, not an AIOps
platform itself. Commercial AIOps-branded platforms ([Splunk](tools/splunk/README.md) ITSI,
Moogsoft, [Dynatrace](tools/dynatrace/README.md) Davis AI, [Datadog](tools/datadog/README.md)
Watchdog, BigPanda) add the ML-driven correlation/anomaly-detection layer on top of exactly
that kind of telemetry data — this repo documents the substrate layer and, for Dynatrace,
Datadog, and Splunk, has dedicated tool docs; the rest aren't (yet) covered in depth.

## LLMOps

**The problem without it**: with a classic ML model, the deliverable *is* the model —
version it, monitor it, done. With an LLM-based system, the deliverable is usually a
**prompt template + a retrieval pipeline + a model API call**, and any of those three can
silently break independently of the others — an edited prompt, a stale vector index, a
provider's model version changing underneath you with no warning. Classic MLOps tooling
was never built to version or monitor any of that.

**Origin.** Genuinely no single credited source — verified this rather than assumed;
unlike AIOps (Gartner) or MLOps (Google's whitepaper as the closest canonical reference),
LLMOps emerged organically alongside the 2022-2023 wave of LLM adoption, with no analyst
report or paper identified as "the" origin. The most-cited working definitions:

- **Databricks**: "the practices, techniques and tools used for the operational management
  of large language models in production environments... extends MLOps practices to large
  language models" — framed explicitly as MLOps's specialization, not a separate
  discipline.
- **Weights & Biases**: substantially overlapping scope, but with explicit added emphasis
  on prompt engineering and dataset curation as first-class lifecycle stages in their own
  right, not just an extension of existing MLOps steps.
- **a16z**: never formally defines "LLMOps" as a term at all — their widely-cited
  "Emerging Architectures for LLM Applications" post frames the same territory
  architecturally (the LLM app stack) rather than as an operational discipline with a
  name.

**Responsibilities**: prompt versioning/management, RAG/retrieval pipeline health, vector
DB operations, generative-output evaluation (harder than classic ML metrics — hallucination,
toxicity, LLM-as-judge scoring), fine-tuning/RLHF pipeline management, token-cost
monitoring, guardrails.

**Tools already documented in this repo**:

- [vLLM](tools/vllm/README.md) — high-throughput LLM serving.
- The vector DBs in `genai_lab/` — FAISS, Qdrant, pgvector — the RAG-pipeline half of
  LLMOps.
- [`11_llmops`](../../engineering_fundamentals/system_design_foundation/11_llmops/tutorial.md)
  — this repo's existing tutorial on the practice mechanics (prompting, evals, guardrails,
  fine-tuning) that this doc's *definition* sits above; read that one for how, this one for
  what/who-says-so.

## No formal standard exists for any of the three

**ISO, IEEE, and NIST have no formal standardized definition of MLOps, AIOps, or LLMOps.**
All three remain industry/vendor/analyst-driven terms, not standards-body terms — the
closest adjacent formal standards (ISO/IEC 23053 for AI-system frameworks generally, IEEE
P2941.3 for pretrained-model APIs) address neighboring ground, not these specific terms.
Practical implication: there is no authoritative dictionary to settle a scope disagreement
— when two people disagree about what "AIOps" or "LLMOps" covers, both can be citing a real
source and still mean different things.

## Distinctions, side by side

| | MLOps | AIOps | LLMOps |
|---|---|---|---|
| **Deliverable** | A versioned, monitored model in production | Correlated signal / reduced noise from IT telemetry | A working prompt+retrieval+model pipeline |
| **Primary input** | Training data, features, model artifacts | Logs, metrics, traces, events | Prompts, retrieved context, model outputs |
| **Primary failure mode guarded against** | Silent model degradation (drift) | Alert fatigue / slow root-cause identification | Silent pipeline breakage (prompt/index/model-version drift) |
| **Who defined the term** | No clean coiner; closest canonical reference is Google's 2020 whitepaper | Gartner, 2016 (Colin Fletcher) | No credited origin; organic, vendor-driven (~2022-2023) |
| **Formal standard?** | No | No | No |
| **Tools in this repo** | Feast, MLflow, Evidently, KServe | Prometheus, Grafana, Loki, ELK/EFK, CloudWatch | vLLM, FAISS/Qdrant/pgvector |

## Where they compose rather than compete

These aren't mutually exclusive disciplines fighting over the same territory — real
systems combine them:

- **An LLM-powered AIOps tool** uses LLMOps techniques (prompting, RAG over runbooks,
  eval) to build a product whose actual job is AIOps (summarizing an incident, suggesting
  a root cause) — LLMOps as the *how*, AIOps as the *what for*.
- **An LLM serving pipeline still needs classic MLOps infrastructure** — a model registry,
  a serving layer with rollout safety, drift monitoring on the outputs — LLMOps adds a
  layer on top of MLOps foundations, it doesn't replace them. This is exactly why
  Databricks' and W&B's definitions both frame LLMOps as an *extension* of MLOps rather
  than a sibling discipline starting from zero.
- **AIOps telemetry can itself become MLOps's monitoring input** — the same
  Prometheus/Loki data an AIOps correlation layer consumes is also what an Evidently-style
  drift check or a model-serving dashboard reads from, just asked a different question of
  it.

## Practical guidance for who owns what in an org

- If the question is "is this model still accurate, and can I roll back safely" — that's
  **MLOps**, regardless of whether the model happens to be an LLM.
- If the question is "why did fourteen services page at once, and which alert is the real
  cause" — that's **AIOps**, regardless of whether ML is involved in answering it.
- If the question is "why did the chatbot start giving wrong answers after someone edited
  a prompt template" — that's **LLMOps**, and generic MLOps drift monitoring won't catch it
  because the model itself didn't change.
- When someone says "we need AIOps" or "we're doing LLMOps," ask what telemetry/outcome or
  what pipeline they actually mean before assuming shared scope — the verified analyst
  disagreement above (Gartner vs. Forrester vs. IDC on AIOps alone) means the term
  genuinely doesn't have one settled meaning even among the people paid to define it.

## Ground-level roles, coding, and the handoff (where most real conflict actually lives)

The definitions above explain *what* each discipline is; they don't explain why data
scientists, ML engineers, and platform/ops people end up in conflict on real teams. That
conflict has a specific root cause, and a specific fix — worth documenting on its own since
it's the part that actually determines whether these disciplines work together or fight.

### Why the conflict happens

In research, "my code is the product" — a data scientist's notebook or an ML engineer's
training script *is* the deliverable, and they own it end-to-end. Nothing structurally
stops that ownership from creeping forward into production once the same person thinks
"I'll just also write the Dockerfile," "I'll just also tune the autoscaler," "I'll just SSH
in and fix it." There's no natural boundary unless someone deliberately draws one. The fix
isn't "convince people to stay in their lane" — it's **defining the artifact each role
hands off, with a contract, so the boundary is something you can point at, not a
personality negotiation.** This is the same root problem DevOps was invented to solve
between Dev and Ops; it's just recurring here in ML/LLM form.

### What each role actually does, day to day, and what they code

| Role | Day-to-day work | What they actually code | Handoff artifact (their job ends here) |
|---|---|---|---|
| **Data Scientist** | EDA, feature experiments, model/architecture selection, hyperparameter tuning, offline eval | Python, notebooks, pandas/sklearn/PyTorch, SQL — exploratory, not held to software-engineering rigor | A **reproducible training script** (not a notebook) + a model that clears an agreed offline-metric bar |
| **ML Engineer** | Hardens the DS's script into a real pipeline, integrates the feature store, writes the serving wrapper, sets up training orchestration | Production-grade Python (tested, typed), Docker, sometimes Spark/Ray, CI config | A **versioned, registered model in a container** exposing a defined API contract (schema-validated input/output, standard metrics exposed) |
| **MLOps / Platform Engineer** | Owns the platform the container runs on — CI/CD promotion mechanics (canary/shadow), registry infra, serving infra, drift monitoring, cost/access governance | Terraform/Helm/K8s YAML, CI/CD pipeline code, Python glue for monitoring (e.g. wiring up Evidently), sometimes Go for internal tooling | A **self-service paved road** — anyone who pushes a compliant container gets automatic CI/CD + monitoring + safe rollout, with no manual per-model work from this person |
| **AIOps / SRE** | Production reliability broadly (not ML-specific) — on-call, capacity planning, the observability stack itself, alert correlation, runbooks | Go (a lot of SRE tooling is Go), Python for automation, PromQL, Terraform, bash | **SLOs + the alerting that enforces them**, and an incident process — not "is this model's business logic right," that's drift monitoring's job |
| **LLMOps Engineer** (often ML Eng wearing another hat in smaller orgs) | Prompt versioning, RAG pipeline health, vector DB ops, eval harness for generative output, guardrails | Python, LangChain/LangGraph glue, vector DB clients, eval framework code (Ragas etc.) | A **versioned prompt+retrieval config that passes an eval gate** before promotion — same contract pattern as the row above |

### Where "trying to do everything" actually causes damage

When a data scientist or ML engineer writes their own Terraform/K8s manifests/autoscaling
policy instead of handing off at the contract boundary:

- It's usually not their strongest skill, so it tends to be non-standard, under-secured, or
  hard for anyone else to maintain.
- It bypasses the platform team's guardrails — cost controls, security review, standardized
  monitoring — that exist precisely so nobody has to reinvent them per model.
- When it breaks at 2am, the on-call platform/SRE person gets paged for code they've never
  seen and don't own. That's the actual moment resentment comes from — not "they stepped on
  my task," but "I'm now accountable for a 2am incident in code I had no say in."
- Multiply this across many data scientists each doing their own thing, and the platform
  team ends up supporting many snowflake deployment patterns instead of one road — which is
  *why* they push back, and it can look like turf-guarding when it's actually a real
  operational cost they're absorbing.

The reverse failure mode exists too, worth naming symmetrically: a platform team that
blocks on model/framework choices that aren't actually operational concerns is overstepping
the same boundary from the other direction, and becomes an unhelpful gatekeeper instead of
a paved road.

### How the handoff should actually work, concretely

1. **Standardize the artifact shape before it's built, not after.** A shared project
   template (cookiecutter-style repo) that already has the Dockerfile, CI config, and
   standard logging/metrics hooks wired in — the DS/MLE fills in `train.py`/`predict.py`,
   they don't invent the container shape themselves.
2. **The model registry + CI gate *is* the literal handoff point.** DS/MLE pushes to the
   registry; automated CI runs the test/eval suite; only on passing does it become the
   platform team's responsibility to deploy through the established canary/shadow pipeline
   (see [`04_model_serving_deployment`](../../engineering_fundamentals/system_design_foundation/04_model_serving_deployment/tutorial.md)
   for that mechanism in depth). Before the gate, it's not production's concern. After the
   gate, the DS/MLE shouldn't be manually touching the running system.
3. **Write the ownership boundary down, per stage, explicitly.** Most of this conflict
   exists because nobody wrote down who's responsible at each artifact stage — so ambiguity
   gets filled by whoever's loudest or most anxious that week, not by a decision anyone
   agreed to.
4. **Give the escalation valve a real path, not a wall.** If a data scientist genuinely
   needs an 80GB-VRAM GPU instead of the platform default, that should be a config
   parameter or a ticket into the paved road — not a reason to let them write their own
   Terraform. This is what keeps the platform team from becoming the blocker in the reverse
   failure mode above.

### When DevOps and MLOps coexist as separate teams: who owns Terraform and CI/CD

The table above treats "MLOps / Platform Engineer" as one row, but once an org is big
enough to have a **separate DevOps team**, a specific version of the same conflict shows
up: both teams touch CI/CD, both touch Terraform, both touch Kubernetes — so it looks like
overlap, and DevOps often defaults to "we own all infra-as-code, full stop," since DevOps
usually predates MLOps in most orgs and that assumption never gets re-examined.

**Why they're not actually competing for the same territory**: DevOps's CI/CD treats
*code* as the unit of change — compile, test, deploy, done. MLOps needs everything DevOps
has, plus handling for the fact that the same code can behave differently depending on
what data trained it, so the validation gate isn't just green/red tests, it's statistical
quality thresholds on a model. MLOps isn't a competing discipline to DevOps — it's a
**layer built on top of** DevOps's layer, the same way an application team builds on top of
a platform team, three layers deep once both teams exist:

1. **DevOps layer** — the cloud account, network, the Kubernetes cluster itself, generic
   CI/CD runners, base IAM/security, and the shared/root Terraform modules and review
   standards.
2. **MLOps layer**, built using DevOps's layer — model registry, feature store, training
   orchestration, ML-specific CI/CD pipeline *definitions* (which stages run, the eval-gate
   threshold, canary/shadow promotion logic), model-serving manifests, drift monitoring,
   and ML-specific Terraform modules (a GPU node pool, a SageMaker endpoint, a KServe
   namespace).
3. **DS/ML Engineer layer**, built using MLOps's layer — training scripts, model code,
   feature definitions, pushed into the paved road MLOps built; no infra code of their own.

**The actual ownership split — both own it, at different layers, through a review gate, not
a turf line:**

| | DevOps owns | MLOps owns |
|---|---|---|
| **Terraform** | Root/shared modules, VPC/networking, IAM, cost/security policy, the module registry and its review standards | ML-specific modules (GPU node groups, SageMaker/KServe resources, feature-store infra) — authored by MLOps, submitted through DevOps's same review gate for security/cost/standards compliance |
| **CI/CD** | The platform itself — runners, secrets injection, base pipeline templates, the deployment-gating mechanism | The pipeline *definition* for ML repos — which stages run, the eval-gate threshold, canary/shadow promotion logic — built on DevOps's runners/templates, not a separate homegrown system |
| **Kubernetes** | The cluster, node provisioning, cluster-wide policy | Namespaces/CRDs/Helm charts specific to model serving (KServe `InferenceService`, GPU-workload autoscaling policy) |

**"DevOps owns all Terraform/CI-CD, full stop" is an overreach, not a correct default.**
The fix isn't for MLOps to simply accept it — it's carving out explicit *authorship* of the
ML-specific modules and pipeline definitions for MLOps, while DevOps keeps the platform and
the review gate. DevOps doesn't lose control (nothing bypasses their security/cost review);
MLOps doesn't lose the ability to actually author the pieces they're accountable for at
2am.

**In small orgs this whole split is moot** — MLOps and DevOps are frequently the same
people, so the question doesn't arise. It only matters once an org is large enough to run
them as genuinely separate teams.

### ML Platform Engineer, specifically

The "MLOps / Platform Engineer" row above collapses two roles that are worth separating
once an org is big enough to run them as distinct teams — the same way DevOps and MLOps
themselves only need separating past a certain scale.

**Definition, with real grounding** (unlike LLMOps, this one traces to actual sources, not
vendor marketing): **Platform Engineering** as a discipline comes from Skelton & Pais's
*Team Topologies* (2019), which named "platform team" one of four fundamental team types —
a team that reduces cognitive load for other teams by exposing capabilities through
**self-service**, treating those teams as customers, running the platform "as a product."
Gartner named Platform Engineering a top strategic technology trend for 2024, predicting
*"by 2026, 80% of large software engineering organizations will establish platform
engineering teams"* (up from 45% in 2022). CNCF's definition: *"the art of building tools
and processes that empower software developers... like creating a self-service station
specifically designed to meet developers' needs."* **ML Platform Engineer is that
discipline scoped to the ML lifecycle** — no distinct coining moment of its own, but
evidenced by real named products from dedicated teams: **Uber's Michelangelo**
("a machine-learning-as-a-service system that enables teams to easily build, deploy, and
operate ML solutions at scale") and **Netflix's Metaflow** (built by Netflix's ML Platform
team, "a human-friendly API for building data and ML applications and deploying them...
frictionlessly").

**Ground-level responsibilities**: building and maintaining the feature store, model
registry, training orchestration, and serving framework **as internal products with
APIs/SDKs**, not one-off configs for one team's model; designing the golden path (the
standard project template, the standard CI/CD pipeline definition ML teams plug into, the
standard way to request GPU resources); building self-service tooling (CLIs, SDKs —
Metaflow is literally this, internal developer portals) so a DS/MLE goes from code to
deployed model without filing a ticket; capacity planning for shared GPU/compute pools
across many ML teams at once; the build-vs-buy call on vendor platforms (SageMaker/
Databricks) vs. building in-house.

**Coding**: heavier software engineering than an operations-focused role — Python for
SDK/API design (not just scripts), often Go for platform services, Kubernetes
operators/CRDs if building custom serving infra, Terraform/Helm for the platform's *own*
infra, sometimes Rust for performance-critical pieces. This is the role literally
*authoring* the ML-specific Terraform modules described in the DevOps/MLOps split above.

**Overlap with DevOps** — same tools, different customer and domain-awareness:

| | DevOps | ML Platform Engineer |
|---|---|---|
| Customer | Any engineering team | Specifically ML/DS teams |
| What the platform understands | Generic services/containers | Models, features, training runs as first-class concepts |
| Terraform ownership | Root/shared modules, network, IAM, the review gate | Authors ML-specific modules (GPU pools, feature-store infra), submitted through DevOps's gate |

**Overlap with MLOps Engineer** — the clearest pattern across sources: **one builds the
road, the other drives on it and keeps traffic flowing.** ML Platform Engineer *builds*
the registry/feature-store/serving framework as a product; MLOps Engineer *operates* it
for specific models — configuring a specific team's pipeline, watching dashboards,
responding to a specific model's drift alert, tuning a specific deployment's canary
threshold.

**In practice, at most companies, these are the same job title.** The distinctions above
are real *once an org is big enough to staff them separately* — but that threshold is
high. Team Topologies' own logic is that a platform team only splits off once the
cognitive load of building shared infrastructure justifies a dedicated team separate from
the people operating specific models; Gartner's own cited stat backs this up — even by
2026 they project 80% of **large** software engineering orgs having platform engineering
teams, meaning a large share of companies simply never cross that threshold. Below it, one
person or one small team does the feature-store-building *and* the drift-dashboard-watching
*and* the prompt-versioning, because no single one of those has enough volume to justify
splitting it off. **LLMOps is even less likely to get its own title than MLOps-vs-Platform
is** — outside AI-native companies (OpenAI, Anthropic, Databricks, big-tech AI labs),
LLMOps responsibilities usually get absorbed into whichever team already exists, MLOps or
ML Platform, rather than spinning up a third team for it.

Since none of "MLOps," "AIOps," "LLMOps," or "Platform Engineering" have a formal
standards-body definition (verified earlier in this doc), a job title alone tells you very
little about what someone actually does. The useful question when meeting someone with any
of these titles is **what do you build vs. what do you operate day to day**, not which of
the words is on their badge.

## Related docs in this repo

- [`ml-genai-lifecycle-and-governance.md`](ml-genai-lifecycle-and-governance.md) — the
  lifecycle stages and governance layer these roles actually manage day to day.
- [`observability-on-eks.md`](observability-on-eks.md) — the AIOps telemetry substrate in
  depth.
- [`tools-and-technologies.md`](tools-and-technologies.md) — index of every MLOps/LLMOps
  tool documented here.
- [`11_llmops` tutorial](../../engineering_fundamentals/system_design_foundation/11_llmops/tutorial.md)
  — LLMOps practice mechanics (prompting, evals, guardrails, fine-tuning).
- [`deepseek_ocr_aws_hosting.md`](../../engineering_fundamentals/system_design_foundation/04_model_serving_deployment/deepseek_ocr_aws_hosting.md)
  — a worked MLOps/LLMOps-boundary case study (hosting a real vision-language model).
