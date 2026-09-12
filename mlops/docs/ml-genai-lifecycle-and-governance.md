# ML & GenAI Lifecycle, and Governance

What MLOps, LLMOps, and ML Platform Engineers actually spend their time managing, at the
level below role definitions: the **lifecycle** a model or GenAI pipeline moves through,
and the **governance** layer that sits on top of it. See
[`mlops-aiops-llmops.md`](mlops-aiops-llmops.md) for the role/discipline definitions this
doc assumes.

## Why lifecycle management exists at all

A model isn't a single artifact made once — it moves through phases (data → training →
evaluation → deployment → monitoring → retraining/retirement), and at every handoff
between phases, without a formal process, things break **silently**: nobody can reproduce
which exact data+code+hyperparameters produced the model serving traffic right now; a
model drifts and nobody notices until a customer complains; a regulator asks "why did the
model reject this application" and no one can answer. This is the same "artifact contract
between phases" principle already established for role handoffs in
[`mlops-aiops-llmops.md`](mlops-aiops-llmops.md#how-the-handoff-should-actually-work-concretely)
— applied one level up, to the *stages* a model passes through, not just the people
passing it along.

## Why governance is a genuinely different concern from lifecycle management

**Lifecycle management is an engineering/process question**: how do we do this repeatably
and reliably. **Governance is a risk/accountability question**: who is allowed to do
this, under what policy, and can we prove afterward what actually happened. A team can
have an excellent, fully-automated lifecycle pipeline and still have zero governance —
automation without an audit trail or approval gate is exactly the scenario regulators
worry about. Governance sits *on top of* the lifecycle, checking it at specific gates; it
doesn't replace it.

## The classic ML lifecycle

1. **Problem framing** — define the business question and success metric before touching
   data.
2. **Data collection / ingestion.**
3. **Data preparation & validation** — cleaning, labeling, schema checks.
4. **Feature engineering** — often via a feature store; see [Feast](tools/feast/README.md).
5. **Training / experimentation** — tracked; see [MLflow](tools/mlflow/README.md).
6. **Evaluation / validation** — offline metrics against a held-out set.
7. **Model registration / versioning** — the model becomes an addressable, versioned
   artifact.
8. **Deployment / serving** — with rollout safety (canary/shadow); see
   [`04_model_serving_deployment`](../../engineering_fundamentals/system_design_foundation/04_model_serving_deployment/tutorial.md).
9. **Monitoring** — performance and drift; see [Evidently](tools/evidently/README.md).
10. **Retraining or retirement.**

## Where the GenAI/LLM lifecycle genuinely differs

- **A new upstream step: build vs. fine-tune vs. prompt an API.** Classic ML almost always
  trains from scratch on your own data. GenAI usually starts from someone else's
  foundation model — meaning step 2 (data collection) for the *base* model isn't something
  you did, saw, or control at all. You inherit a black box's data governance, or the lack
  of it.
- **RAG data is a second, separate data-governance surface.** Unlike pretraining data, the
  documents you retrieve at inference time (your knowledge base) *are* fully yours to
  govern — the same PII/access-control concerns as classic training data, just injected at
  inference time instead of training time.
- **Prompt engineering becomes a first-class, versioned artifact**, replacing/augmenting
  feature engineering as the thing that needs the rigor training code used to get.
- **Evaluation is qualitatively harder.** Classic ML has clean metrics (accuracy, AUC,
  RMSE). GenAI evaluation includes subjective generative quality — hallucination,
  toxicity, tone — often requiring human eval or LLM-as-judge, which introduces its own
  governance question: is the judge model itself biased or reproducible?
- **A new runtime lifecycle stage that doesn't exist in classic ML: guardrails** — content
  filtering/safety enforcement happening live, not just at training/eval time.
- **Retirement risk you don't control.** A vendor can deprecate a model version out from
  under you (an API provider retiring a model) — a lifecycle risk classic ML, where you
  own the artifact outright, never has.

## Data governance, from first principles

Predates ML entirely — it's a general data-management discipline. **DAMA-DMBOK** (DAMA
International's Data Management Body of Knowledge — verified real, currently 2nd edition
with a 3.0 revision underway) is the widely-cited reference body covering it. Core
components as they apply to ML:

- **Lineage** — where did this data come from, what transformations happened — the only
  way to answer "was this data legally allowed to be used for this purpose."
- **Classification / sensitivity tagging** — PII, PHI, financial data — determines who can
  even access it.
- **Access control** — **RBAC** (Role-Based Access Control: permissions attached to
  roles, e.g. "data scientist," "auditor," and users get access by being assigned a role;
  origin is Ferraiolo & Kuhn's 1992 NIST paper "Role-Based Access Controls," later
  formalized as NIST/ANSI standard INCITS 359-2004; simple and easy to audit, but
  coarse-grained — can't naturally express "only during business hours" or "only if data
  and user are in the same region") or **ABAC** (Attribute-Based Access Control: access is
  evaluated at request time against attributes of the subject, object, action, and
  sometimes environment conditions, per NIST SP 800-162 (2014); more expressive — e.g. "PII
  accessible only to EU-based staff during business hours" — but harder to audit since
  policy logic, not a role list, decides access).
- **Retention / deletion policy** — including a genuinely unsettled ML-specific version:
  if a user exercises a deletion right, does that obligate you to delete or retrain any
  model *trained on* their data, not just the raw record? This is an actively debated, not
  fully settled, regulatory question — worth knowing it's open, not assuming a clean
  answer exists.
- **Consent scope** — was data collected with consent for *this* downstream use; ML
  training is frequently a new use beyond the original collection purpose.

## Model governance, grounded in real regulatory precedent

**The discipline predates modern AI governance discourse entirely.** **SR 11-7** —
"Supervisory Guidance on Model Risk Management," issued jointly by the **Federal Reserve**
and the **OCC** in **2011** for banks — is the real foundational framework (verified
directly against the Fed's own published document,
[federalreserve.gov/boarddocs/srletters/2011/sr1107.pdf](https://www.federalreserve.gov/boarddocs/srletters/2011/sr1107.pdf)).
It defines model risk as *"the potential for adverse consequences from decisions based on
incorrect or misused model outputs and reports,"* and structures governance around three
elements:

1. **Model development, implementation, and use.**
2. **Model validation.**
3. **Governance, policies, and controls.**

This was written for credit and valuation models nearly a decade before "AI governance"
became a phrase — the ML/AI governance conversation is largely re-deriving what banking
regulators already formalized.

**Applied to ML/AI specifically, model governance covers:**

- **Model registry as the system of record** ([MLflow](tools/mlflow/README.md)) — the
  literal implementation of SR 11-7's element 1.
- **Model lineage** — which data, code version, and hyperparameters produced this exact
  model, for audit reproducibility.
- **Approval workflows** — sign-off from legal/risk/ethics before promoting a high-stakes
  model (credit, hiring, healthcare) to production.
- **Bias/fairness testing and documentation**, increasingly a *legal* requirement, not just
  best practice. **NYC Local Law 144** (verified: took effect January 2023, enforcement
  from July 2023) requires annual independent bias audits of automated employment decision
  tools used in hiring, published audit summaries, and 10-business-day candidate notice
  before use.
- **Explainability** — commonly assumed to be a hard GDPR requirement; **this is
  overstated**, verified directly against the actual legal text. GDPR **Article 22**
  grants a right *not to be subject to* a decision based solely on automated processing
  with legal/significant effects, plus safeguards where exceptions apply (human
  intervention, the right to express a view, the right to contest) — not an explicit
  textual "right to explanation." That's inferred from a non-binding recital and remains
  legally contested, not settled law. Don't repeat "GDPR grants a right to explanation" as
  fact — it doesn't, cleanly.
- **Model cards** — structured model documentation, from Mitchell et al.'s **"Model Cards
  for Model Reporting"** (ACM FAT\* '19, 2019) — the real, citable origin of a standard
  doc format describing a model's intended use, limitations, and benchmarked performance
  across subgroups.
- **The EU AI Act** — the closest thing to a binding, formal governance standard that
  exists for AI specifically. Verified as **Regulation (EU) 2024/1689**, in force since
  August 2024, with four risk tiers: unacceptable, high-risk, limited-risk, minimal-risk.
  High-risk systems face specific obligations under **Articles 8-15**: a risk management
  system, data governance requirements, technical documentation, logging, human oversight,
  and accuracy/robustness/cybersecurity requirements.
  - **Current as of writing, and easy to get stale on**: the original compliance
    deadlines were pushed back via the **"Digital Omnibus"** (Regulation (EU) 2026/1744,
    adopted mid-2026). High-risk obligations now land **2 December 2027** for standalone
    (Annex III) systems and **2 August 2028** for product-embedded (Annex I) systems —
    not the earlier 2026/2027 dates most existing commentary still cites. Re-verify this
    date if it matters for a real compliance decision; regulatory deadlines are exactly
    the kind of fact that goes stale.

## GenAI-specific governance additions

- **Copyright/IP risk** on both training data and generated output — an active,
  unresolved legal area (ongoing publisher-vs-AI-company litigation as of writing), not
  settled precedent.
- **Prompt injection / jailbreak risk** — a genuinely new security-governance concern that
  doesn't exist for classic ML models.
- **Third-party model risk** — calling an external API means inheriting *part* of that
  vendor's governance posture while still being accountable yourself for how you use it —
  a vendor-risk-management question distinct from governing a model you trained.

## Related docs in this repo

- [`mlops-aiops-llmops.md`](mlops-aiops-llmops.md) — role/discipline definitions this
  lifecycle-and-governance layer sits underneath.
- [Feast](tools/feast/README.md) — feature-store lineage.
- [MLflow](tools/mlflow/README.md) — model registry, the system of record for governance.
- [Evidently](tools/evidently/README.md) — drift/quality monitoring, the ongoing half of
  the lifecycle after deployment.
- [`04_model_serving_deployment`](../../engineering_fundamentals/system_design_foundation/04_model_serving_deployment/tutorial.md)
  — rollout-safety mechanics (canary/shadow) that sit at the deployment stage.
