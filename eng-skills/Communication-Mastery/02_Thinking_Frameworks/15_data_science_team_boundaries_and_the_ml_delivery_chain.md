# Data Science Team Boundaries and the ML Delivery Chain — Who Owns What Between Notebook and Production

The exact **remit** of a data science team varies by company, but in a mature organization it converges on one thing: turning data into reliable business decisions and AI capability, not owning the entire software platform that eventually serves that capability. The boundary is frequently drawn poorly in practice — a data scientist inherits on-call for a Kubernetes deployment nobody trained them for, or a platform engineer gets handed a research notebook and is expected to divine the modeling intent behind it. This chapter maps the boundary precisely — what data science owns outright, what it hands off and to whom, and why the division exists at all — as the domain-specific companion to `11_role_clarity_and_expectation_contracts.md`, which covers the MLOps engineer/architect boundary one layer downstream of this one.

## Index

1. [The Responsibility Matrix](#1-the-responsibility-matrix)
2. [Why the Boundary Exists (The Mechanism)](#2-why-the-boundary-exists-the-mechanism)
3. [Core Responsibilities of a Data Science Team](#3-core-responsibilities-of-a-data-science-team)
4. [What Data Science Does Not Own](#4-what-data-science-does-not-own)
5. [The Delivery Chain in AI Product Companies](#5-the-delivery-chain-in-ai-product-companies)
6. [How the Boundary Compresses by Company Size](#6-how-the-boundary-compresses-by-company-size)
7. [Navigating the Boundary as an Engineer/Architect](#7-navigating-the-boundary-as-an-engineerarchitect)
8. [Glossary — Vocabulary Used in This Chapter](#8-glossary--vocabulary-used-in-this-chapter)

---

## 1. The Responsibility Matrix

The single highest-leverage artifact for this whole chapter — one table, worth pinning to the top of any onboarding doc for a data/ML org, adapted to the actual team structure in play.

| Area | Data Science | ML Engineering | Data Engineering | Platform/MLOps |
|---|---|---|---|---|
| Business problem understanding | ✅ Own | Assist | – | – |
| Data exploration & analysis | ✅ Own | Assist | Assist | – |
| Feature engineering | ✅ Own | Assist | Support | – |
| Model selection & training | ✅ Own | Support | – | – |
| Experimentation | ✅ Own | Assist | – | – |
| Model evaluation | ✅ Own | Support | – | – |
| Data labeling strategy | ✅ Own | – | – | – |
| Production inference service | Review | ✅ Own | – | Support |
| Model deployment | Support | ✅ Own | – | ✅ Platform |
| Infrastructure | – | Assist | Assist | ✅ Own |
| Monitoring model quality | ✅ Own | Support | – | Support |
| Monitoring infrastructure | – | – | – | ✅ Own |

Three usage notes on reading this table correctly:

- **"Own" means end-to-end accountability, not sole execution.** Data science owning model evaluation doesn't mean nobody else ever looks at a confusion matrix — it means when evaluation is wrong, that team answers for it, full stop.
- **The row that flips is the tell for where the real boundary sits.** Data science goes from `✅ Own` (model evaluation) to `Review` (production inference service) in the space of two rows — that inversion, not any single row, is the actual shape of the handoff, covered in depth in §5.
- **"Assist" and "Support" are not interchangeable**, even though the table uses both loosely. In practice, "Assist" tends to mean *contributes expertise the owning team lacks* (a data engineer assisting with data exploration because they know where the schema landmines are), while "Support" tends to mean *is on the hook if things break, without holding the primary design decision* (ML engineering supporting model evaluation by building the eval harness the data scientist's metrics run inside). Naming which one a given "assist" actually is prevents the two teams from silently assuming different things about who gets paged.

[↑ Back to index](#index)

## 2. Why the Boundary Exists (The Mechanism)

The temptation, especially from outside the discipline, is to see this division as bureaucratic turf-drawing. It isn't — it tracks three real forces:

| Force | Mechanism | Consequence if ignored |
|---|---|---|
| **Skill divergence** | Statistical/modeling judgment (is this feature leaking the label? is this lift significant?) and production-systems judgment (will this endpoint survive a traffic spike? is this Terraform module idempotent?) are different disciplines that take years to build independently. Few people are excellent at both simultaneously at scale. | Forcing one role to own both produces mediocrity at one end — usually a data scientist writing infrastructure that a platform engineer would flag in code review, or a platform engineer making modeling calls with no statistical grounding. |
| **Blast radius containment** | A bad notebook cell fails privately, on one person's machine, with no user-facing consequence. A bad production deployment can take down a live service used by paying customers. | Collapsing the boundary means research-grade code — written for exploration speed, not resilience — reaches production paths without ever passing through the review a system with real **blast radius** deserves. |
| **Specialization compounding** | A platform engineer who deploys 50 models a quarter gets systematically better at deployment than a data scientist who deploys 2. A data scientist who runs 100 experiments a quarter gets systematically better at experimental design than a platform engineer who runs 2. | Splitting the work lets each side's competence compound in its own lane; merging the work resets both to generalist speed, and generalist speed is slower than either specialist's, not the average of the two. |

The rule of thumb this yields: **a decision requires the discipline whose repeated practice produces good judgment about it.** Modeling decisions belong wherever repeated modeling judgment is being built; production-systems decisions belong wherever repeated systems judgment is being built. Whenever a task doesn't obviously map to one side, that's usually a sign the task should be *reviewed by both* rather than unilaterally claimed by either — see §7.

[↑ Back to index](#index)

## 3. Core Responsibilities of a Data Science Team

### 3.1 Understand the business problem

The starting point of everything downstream, and the row most likely to be skipped under delivery pressure — skipping it doesn't remove the ambiguity, it just defers the reckoning to model-review time, when it is far more expensive to correct.

- **Examples**: fraud detection, receipt-extraction accuracy, customer churn prediction, recommendation systems.
- **Deliverables**: a written problem definition, success metrics, and KPIs — artifacts, not conversations, for the same reason an [expectation contract](11_role_clarity_and_expectation_contracts.md#1-the-failure-pattern-operating-without-a-charter) needs to be written down: an unwritten definition of "success" silently drifts as stakeholders' private versions of it diverge.

### 3.2 Data analysis

The team answers, with evidence rather than intuition: is enough data available? Is it clean? Which features matter? Are there biases? Are there missing values?

- **Deliverables**: EDA notebooks, statistical analysis, data quality reports.

### 3.3 Feature engineering

- **Receipt extraction example**: OCR confidence, image brightness, merchant frequency, text density.
- **Fraud example**: transaction velocity, device history, country mismatch.

Feature engineering sits squarely inside data science's remit because it requires the same statistical judgment as modeling itself — a feature is a hypothesis about what the label depends on, and evaluating that hypothesis is modeling work, not plumbing work, even when data engineering builds the pipeline that computes it at scale (§4).

### 3.4 Model development

Choosing among algorithms — XGBoost, random forest, logistic regression, CNNs, transformers, LLMs — and the surrounding craft: hyperparameter tuning, cross-validation, feature selection, ablation studies.

### 3.5 Model evaluation

Metrics: precision, recall, F1, ROC-AUC, RMSE, MAE. Also error analysis, confusion matrices, and bias/fairness analysis — the last of which is frequently under-resourced relative to its downstream cost, since a fairness failure discovered in production is a reputational and sometimes regulatory event, not a metric footnote.

### 3.6 Experimentation

- **Examples**: "Does OCR preprocessing improve accuracy?" "Is GPT-4 better than OCR model X?" "Should we use embeddings?"
- **Deliverables**: experiment reports, statistical significance analysis, recommendations.

### 3.7 Data annotation strategy

Especially load-bearing for AI systems trained on labeled data: defining labeling guidelines, reviewing label quality, and measuring inter-annotator agreement. A model is only as trustworthy as the labels it was trained to imitate, which makes this a modeling responsibility, not an outsourced clerical task — even when the physical labeling is contracted out.

### 3.8 Model improvement

When accuracy drops: analyze failures, collect new training data, retrain, introduce new features. This responsibility is easy to lose track of once a model ships, because it has no natural trigger the way a deployment does — it requires the monitoring ownership named in the matrix's "Monitoring model quality" row to actually surface the drop in the first place.

### 3.9 Explain results to stakeholders

Why accuracy dropped, why false positives increased, whether a new model should replace the old one. This is the translation layer between statistical results and business decisions, and it is arguably the responsibility most likely to be underinvested in relative to its impact — a correct model recommendation delivered illegibly gets overridden by a wrong one delivered persuasively. The frameworks for doing this well live throughout `../03_Explanation_Frameworks/` and `../06_Project_Presentation/`.

[↑ Back to index](#index)

## 4. What Data Science Does Not Own

These are, in a mature organization, engineering responsibilities — and the boundary is not a demotion of data science's importance, it is a **division of labor** that lets each side specialize (§2).

| Domain | Examples | Typical owner |
|---|---|---|
| Infrastructure | Kubernetes, EKS, Docker, Terraform, networking | Platform/MLOps |
| CI/CD | GitHub Actions, Azure DevOps, Jenkins | Platform/MLOps |
| Cloud infrastructure | AWS, Azure, GCP, IAM, VPCs | Platform/MLOps |
| Production APIs | FastAPI, Flask, gRPC, authentication, rate limiting | ML Engineering |
| Production monitoring | Prometheus, Grafana, CloudWatch, OpenTelemetry | Platform/MLOps |
| Scalability | Autoscaling, load balancing, queue management | Platform/MLOps |

The distinction to hold onto: data science owns **monitoring model quality** (is the model still statistically sound?) while platform owns **monitoring infrastructure** (is the service that serves the model still up?) — two different failure classes that happen to show up in the same dashboard and are easy to conflate until an outage forces the distinction into the open. A model can be perfectly healthy on infrastructure that's on fire, and an infrastructure can be perfectly healthy serving a model that's silently drifted into uselessness; each needs its own owner because neither owner's tooling reliably catches the other's failure.

[↑ Back to index](#index)

## 5. The Delivery Chain in AI Product Companies

In a company organized around shipping AI as a product, work flows through a chain, and each stage has both a primary output and a **handoff artifact** — the thing that crosses to the next stage, which is where ambiguity tends to concentrate if it isn't made explicit.

```
Business Problem
       │
       ▼
Data Science
  - Data analysis
  - Feature engineering
  - Model training
  - Evaluation
  - Experimentation
       │  (handoff: a trained model + eval report + reproducible training code)
       ▼
ML Engineering
  - Convert notebook to production code
  - Build inference pipelines
  - Optimize latency
  - Package models
       │  (handoff: a packaged, versioned, latency-tested service artifact)
       ▼
Platform / MLOps
  - CI/CD
  - Kubernetes
  - Monitoring
  - Deployment
  - Infrastructure
  - Model registry
       │
       ▼
Production
```

The most consequential handoff in the whole chain is the first one — data science to ML engineering — commonly described as the **notebook-to-production chasm**: exploratory code optimized for iteration speed (global state, hardcoded paths, no tests) meeting a production standard optimized for reliability (idempotency, observability, graceful degradation). Two failure modes recur on either side of that handoff:

- **Throwing it over the wall**: data science treats "the notebook runs and the metric looks good" as the finish line, leaving ML engineering to reverse-engineer intent from code that was never meant to be read by anyone else. The fix is a handoff artifact with teeth — a written model card (problem, features, known limitations, expected input distribution) alongside the code, not just the code.
- **Silent rewrite drift**: ML engineering, translating notebook to production, quietly changes feature computation logic to make it performant, and the resulting **training/serving skew** — the model behaving differently in production than it did in evaluation, because a feature is computed slightly differently in each path — surfaces weeks later as an unexplained accuracy drop, expensive to root-cause because nobody flagged the translation as a decision at the time it was made. The fix is treating the rewrite as a change requiring data science sign-off on the eval metrics *after* the rewrite, not just before it.

[↑ Back to index](#index)

## 6. How the Boundary Compresses by Company Size

The matrix in §1 assumes specialized teams. Real organizations compress it in predictable, size-correlated ways:

| Organization | Typical structure | Consequence for role clarity |
|---|---|---|
| **Startup** | One person (or a very small team) covers data science, ML engineering, backend, MLOps, cloud, and DevOps | The boundary in this chapter still exists *conceptually* — it just lives inside one person's head instead of across a team roster. The main risk is skipping the discipline the boundary enforces (e.g., shipping a notebook straight to prod without the translation step) simply because there's no second team to catch it. |
| **Mid-size / scaling company** | Roles start splitting — a dedicated ML engineer appears first, then a platform team, then dedicated data engineering | This is the highest-friction stage: titles exist before charters do, which is exactly the **title–charter gap** described in `11_role_clarity_and_expectation_contracts.md` §2 — two people can hold the same title while picturing different scopes. |
| **Large enterprise (e.g., many Fortune 500 companies)** | Fully specialized: data scientists (research, modeling, experimentation, business insights); ML engineers (productionize, inference services, performance, integration); data engineers (pipelines, ETL/ELT, feature stores, warehouses); MLOps/platform engineers (CI/CD, deployment, infrastructure, observability, scaling, security, governance); software engineers (applications and APIs that consume the models) | Specialization lets each team's judgment compound (§2), but multiplies the number of handoffs — which multiplies the number of places a `Support` or `Assist` cell in §1 can be silently interpreted two different ways by the two teams touching it. |

The pattern across all three: **the underlying division of labor is constant; only its packaging changes.** A startup engineer wearing every hat in this chapter benefits from knowing which hat is currently on, for the same reason argued in `11_role_clarity_and_expectation_contracts.md` §3 — naming the hat clarifies which standard of judgment currently applies, even when one person is doing the naming for themself.

[↑ Back to index](#index)

## 7. Navigating the Boundary as an Engineer/Architect

For someone operating at the ML engineering / MLOps / cloud-architect layer of this chain — the audience `11_role_clarity_and_expectation_contracts.md` is written for — this chapter's matrix is the missing upstream half of that chapter's picture. Three practical implications:

1. **The `Review` and `Support` cells are where to invest expectation-setting effort, not the `Own` cells.** Nobody argues about who owns Kubernetes. People argue about what "Review" means for a production inference service — does data science sign off before every deploy, or only for models crossing a risk threshold? Make that explicit the same way `11_role_clarity_and_expectation_contracts.md` §5 recommends making any expectation explicit, in writing, early.
2. **Treat the notebook-to-production handoff (§5) as a formal interface, not a hallway conversation.** A short, standing checklist — model card present, eval metrics reproducible from the handed-off code, known limitations stated — converts a chronically ambiguous handoff into a routine one, the same structural move as the operating cadence in `11_role_clarity_and_expectation_contracts.md` §8.
3. **When a task doesn't map cleanly onto any row in §1, that's a signal to negotiate scope explicitly rather than quietly absorb or quietly decline it** — precisely the scope-negotiation script in `11_role_clarity_and_expectation_contracts.md` §5.2, applied here to data/ML team boundaries instead of individual role boundaries.

[↑ Back to index](#index)

## 8. Glossary — Vocabulary Used in This Chapter

| Term/Phrase | Meaning |
|---|---|
| Remit | The area of authority and responsibility officially assigned to a team or role |
| Converges | Comes together toward a single point or shared form, from different starting positions |
| Divine (verb) | To work out or guess something by inference rather than being told directly |
| Blast radius | The extent of damage or disruption a failure can cause, borrowed from explosives, used in engineering for failure containment |
| Idempotent | Producing the same result no matter how many times an operation is repeated |
| Compounding | Growing on itself, where each increment builds on and enlarges the previous one |
| Unilaterally | Done by one party alone, without agreement from the others involved |
| Load-bearing | Carrying essential structural weight; something whose absence causes collapse |
| Illegibly | In a way that is hard for others to read, interpret, or make sense of |
| Division of labor | The splitting of a larger task among specialized parties so each can focus on their area of skill |
| Handoff artifact | A concrete deliverable (document, code, report) that transfers responsibility from one party to the next |
| Notebook-to-production chasm | The gap between exploratory research code and the reliability standard production code requires |
| Throwing it over the wall | Passing work to the next team without adequate context, leaving them to reconstruct intent |
| Training/serving skew | A model behaving differently in production than in evaluation because a feature is computed differently in each path |
| Title–charter gap | The mismatch between what a job title implies and what the role actually owns in a given organization |
| Turf-drawing | Establishing or defending boundaries of authority, often used pejoratively to suggest territorial motive over substance |
| Reckoning | A moment of consequence or accounting for something previously deferred |

[↑ Back to index](#index)
