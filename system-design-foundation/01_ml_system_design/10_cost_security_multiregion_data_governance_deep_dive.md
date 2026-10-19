# Data Governance in MLOps: What It Actually Means in Practice

A practical companion to the [Cost, Security & Multi-Region Governance tutorial](10_cost_security_multiregion.md#security-compliance-in-ml-pipelines)
— that tutorial's governance section is a summary; this is the concrete version. "Data
governance" gets said in almost every MLOps interview and almost never defined past the
buzzword. Said out loud with no more content behind it, it signals nothing. This document
is the content behind it: the actual artifacts, tags, policies, and logs a governed ML
pipeline produces — so you can describe what you've *actually built or would build*, not
recite the term.

## The Test for Whether "We Have Data Governance" Is True

If you can't point to a **concrete artifact** for each of the following, you don't have
governance for that dataset yet — you have an intention:

| Question | The artifact that answers it |
|---|---|
| What data exists, and where? | An entry in a data catalog |
| How sensitive is it? | A classification tag on the schema |
| Who's allowed to read it, and at what granularity? | An access-control policy (table/row/column-level grants) |
| Where did this specific value come from? | A lineage graph, queryable back to source |
| Is it still accurate/fresh? | A data-quality SLA with monitored metrics |
| How long do we keep it, and can we delete it on request? | A retention policy + a tested deletion procedure |
| Did the subject consent to this specific use? | A consent flag checked at query/feature-computation time, not just at collection |
| Who's accountable for it? | A named owner/steward, not "the platform team" generically |
| Who actually accessed it, when, and why? | An audit log, retained and queryable |

The rest of this document walks through each row concretely.

## 1. Data Cataloging: Making "What Data Exists" Answerable

A catalog entry isn't just a table name — for it to be useful, it needs, at minimum:

- **Schema** (columns, types) — kept in sync automatically, not manually maintained and
  therefore stale within a month.
- **A named owner** — a person or team, not a distribution list nobody monitors.
- **A plain-language description** — "what business process produces this, what it's
  used for" — the thing that lets someone *discover* it's relevant to their use case
  without already knowing it exists.
- **Classification tags** (see below) — attached at the catalog level so every consumer
  sees them before querying, not discovered after the fact.
- **Lineage links** — where this table's data came from, and what consumes it downstream.

**Tools that actually do this**: Unity Catalog (if already on Databricks — unifies
catalog, access control, and lineage in one system, which is exactly why it kept coming up
across the other tutorials in this section), AWS Glue Data Catalog, or open-source
options like DataHub/Amundsen if you need a catalog independent of any single compute
platform.

## 2. Classification: A Concrete Tagging Taxonomy

A workable, minimal taxonomy — this exact 4-tier structure (or one very like it) is what
most real governance programs converge on:

| Tag | Meaning | Example ML data |
|---|---|---|
| **Public** | No restriction if leaked | Aggregated, anonymized model metrics |
| **Internal** | Company-confidential, no regulatory sensitivity | Feature engineering intermediate tables with no PII |
| **Confidential** | Business-sensitive, restricted by role | Pricing model internals, unreleased model performance vs. competitors |
| **Restricted (PII/PHI/PCI)** | Regulated personal data | Names, emails, health records, payment data, and any feature *derived* from them |

**The detail that actually matters in practice**: classification must be applied at the
**column level**, not the table level, and it must **propagate through transformations**.
A table with 40 columns where only 3 are PII should have those 3 tagged individually — and
if a feature-engineering job derives a new column from a PII column (e.g. "days since
signup" derived from a signup-date + email-verification join), the derived column needs to
inherit the classification, not start untagged because it's technically "new." This
propagation is exactly where hand-rolled tagging systems break down and why catalog tools
with lineage-aware tagging exist.

## 3. Access Control: RBAC, ABAC, and Actual Grants

- **RBAC (role-based)**: access tied to a role ("data-scientist," "ml-platform-admin") —
  simple to reason about, but coarse; if a role can see a table, every member of that role
  sees the *whole* table.
- **ABAC (attribute-based)**: access computed from attributes of the requester and the
  data at query time ("this analyst can see rows where `region = their_assigned_region`")
  — finer-grained, more complex to implement and audit.
- **Column-level and row-level security in practice** (Unity Catalog syntax, illustrative):

```sql
-- Column-level: mask a PII column for anyone without the pii_reader role
CREATE FUNCTION mask_email(email STRING)
RETURNS STRING
RETURN CASE
  WHEN is_member('pii_reader') THEN email
  ELSE '***MASKED***'
END;

ALTER TABLE users ALTER COLUMN email SET MASK mask_email;

-- Row-level: restrict a regional analyst to only their region's rows
CREATE FUNCTION region_filter(region STRING)
RETURNS BOOLEAN
RETURN region = current_user_region();

ALTER TABLE transactions SET ROW FILTER region_filter ON (region);
```

- **The ML-specific extension of this**: access control needs to apply at the **feature
  store** layer too, not just the raw-data warehouse layer — a feature derived from PII is
  itself sensitive, and "the raw table is locked down" doesn't help if the derived feature
  in the online store isn't independently access-controlled. This is the direct
  extension of the feature-store access-control point in the
  [feature store tutorial](03_feature_store_model_promotion.md#model-registry-mlflow-unity-catalog).

## 4. Lineage: Why "Column-Level" Is the Detail That Matters

Table-level lineage ("model X was trained from table Y") answers *some* audit questions.
It does **not** answer "was any PII used to train this model," because a table can be
90% non-sensitive columns and 10% PII — table-level lineage can't distinguish "trained on
this table" from "trained on the PII columns within this table."

**Column-level lineage** tracks provenance per column, through every transformation —
this is what actually answers the compliance-critical question, and it's what makes the
[audit-lineage tricky scenario](12_tricky_scenarios_10_audit_lineage_reconstruction.md)
answerable in minutes instead of days. Tools: Unity Catalog's built-in column-level
lineage graph (if on Databricks), or OpenLineage/Marquez as an open-source, platform-
agnostic alternative that instruments pipeline frameworks (Spark, Airflow, dbt) directly.

## 5. Retention & Deletion: The Part That's Genuinely Hard for ML

Standard data retention (delete raw records after N days per policy) is straightforward.
**Deletion requests against data already used to train a model are not** — this is the
governance problem most teams under-prepare for:

- A "right to be forgotten" request (GDPR Article 17) can require deleting a user's raw
  data easily — but that user's data may already be baked into a trained model's weights,
  and you generally **cannot surgically remove one user's influence from a trained model**
  after the fact.
- **Practical approaches, in order of how commonly they're actually implemented**:
  1. **Delete from raw/feature stores immediately**, and **exclude from the next
     scheduled retrain** — the model remains influenced by that user's data until the
     next retrain cycle. This requires an explicit, documented retention policy stating
     the maximum time a deleted user's influence can remain in a production model — a
     real number ("no more than 90 days, bounded by our retraining cadence"), not an
     open-ended gap.
  2. **Machine unlearning techniques** (retraining only affected model components, or
     using algorithms designed for efficient removal) — more rigorous, meaningfully more
     engineering investment, typically reserved for the highest-sensitivity use cases.
  3. **Differential privacy at training time** — bounds any single record's influence on
     the model mathematically from the start, sidestepping the deletion problem partially
     by design, at some accuracy cost.
- **The artifact this produces**: a documented, board/legal-approved statement of *"our
  maximum data-influence retention window is X, because Y"* — this is what an auditor or
  a legal team actually wants, not a vague "we take privacy seriously."

## 6. Consent: Checked at Use-Time, Not Just Collection-Time

The common gap: consent is captured correctly at signup (a checkbox, a policy version
accepted), but never checked again at the point where a *specific* ML use of that data
happens. Practical implementation:

- A `consent_flags` field (or table) per user, per *purpose* (e.g.
  `{personalization: true, third_party_sharing: false, marketing_ml: true}`) — not a
  single blanket consent boolean, since real consent frameworks (and GDPR specifically)
  require purpose-specific consent.
- **The feature-computation job checks the relevant consent flag before including a
  user's data** for that specific purpose — this means consent isn't just an ingestion-
  time filter, it's a runtime check wired into the feature pipeline, re-evaluated as
  consent can change (a user can withdraw consent after having previously granted it).

## 7. ML-Specific Governance Artifacts

Beyond the general data-governance components above, ML systems have their own
governance-specific documents worth naming concretely:

- **Model Cards**: a short, structured document per model version — intended use,
  training data summary, evaluation results **broken out by relevant subgroups** (not
  just aggregate), known limitations, and out-of-scope uses. This is the artifact that
  makes "we evaluated for bias" a checkable claim instead of an assertion.
- **Datasheets for Datasets**: the same idea applied to a training dataset — how it was
  collected, what population it represents (and doesn't), known gaps.
- **Training data provenance record**: which data versions (tying to the
  [DVC hands-on guide](09_gitops_ml_cicd_dvc_hands_on.md) or Delta Lake time-travel)
  went into a specific model version — this is column-level lineage's output, formalized
  into a retrievable record per model version in the registry.

## A Concrete Walkthrough: Onboarding a New Dataset Into Governance

1. **Register it in the catalog** with schema, owner, and a plain-language description —
   before any pipeline reads from it in production.
2. **Classify every column** — even "obviously fine" columns, since the default should be
   explicit classification, not "untagged means safe."
3. **Define access grants** at the appropriate granularity (table/row/column) based on
   classification — restricted columns get the narrowest grant by default (explicit
   role membership required), not broad access with an intention to narrow it later.
4. **Wire lineage tracking** into whatever pipeline framework touches it, so downstream
   tables/features automatically inherit traceable provenance.
5. **Set a retention policy** and, if the data includes PII, document the deletion
   procedure and its actual latency (how long until a deletion request is fully
   reflected, including any downstream trained models).
6. **If it feeds an ML pipeline**, confirm the feature-computation step checks relevant
   consent flags before use, and that the resulting model version's provenance record
   will capture this data's version.
7. **Enable audit logging** on the table (who queried it, when) with a retention period
   matching your compliance requirement, not the default operational-log retention.

## Practical Checklist

- [ ] Every production table has a named owner and a catalog entry
- [ ] Every column is explicitly classified (not "untagged = assumed safe")
- [ ] Classification propagates to derived/feature-engineered columns automatically
- [ ] Access grants exist at column/row granularity where classification demands it, not
      just table-level all-or-nothing
- [ ] Feature-store access control mirrors raw-data access control for derived sensitive
      features
- [ ] Column-level (not just table-level) lineage is queryable
- [ ] A documented, specific maximum data-influence retention window exists for deletion
      requests against already-trained models
- [ ] Consent is checked at feature-computation time, per purpose, not only at collection
- [ ] Model Cards exist for production models, with subgroup-broken-out evaluation results
- [ ] Audit logs are retained for the compliance-required period and are actually
      queryable (tested, not just assumed to work)

## Make It Yours

- Pick one dataset you've actually worked with and walk through the checklist above
  against it, honestly — where are the real gaps?
- Has your team ever had to handle a deletion request against data already used in a
  trained model? What actually happened, and what would the documented policy above have
  changed?
- Where does consent actually get checked in a pipeline you've built — at collection only,
  or also at the point of ML use?

## Practice Questions

- Design the data-governance layer for a feature store shared across five ML teams, with
  varying data sensitivity per team.
- A user submits a GDPR deletion request for data already used to train a production
  model three retraining cycles ago — walk through your actual response.
- An auditor asks you to prove no restricted-classification column was used, even
  indirectly via a derived feature, to train a specific model — describe exactly how your
  system would answer this.

## Articulate It: Interview Framing & Vocabulary

### Three Ways to Explain This

- **Test-first (the default when 'data governance' comes up as a buzzword):** "I'd refuse to
  answer in the abstract — governance means being able to point to a concrete artifact for
  each question: a catalog entry, a classification tag, an access grant, a lineage graph. If
  I can't point to the artifact, it's an intention, not governance."
- **Hardest-problem framing (good for a deletion/GDPR follow-up):** "The genuinely hard part
  isn't deleting a raw record, it's that a user's data may already be baked into a trained
  model's weights, and you generally can't surgically remove one person's influence after
  the fact. The artifact that actually satisfies an auditor is a documented maximum
  data-influence retention window, not a promise."
- **Granularity-first (good when asked why table-level isn't enough):** "Table-level lineage
  can't answer 'was any PII used to train this,' because a table can be 90% clean and 10%
  PII. Only column-level lineage, propagated through every transformation, actually answers
  the compliance-critical question."

### Vocabulary Builder

**Technical shorthand — use these instead of over-explaining the concept every time:**

- **column-level lineage** (n. phrase) — tracing provenance per column through every
  transformation, as opposed to only tracking which table fed which table.
- **RBAC / ABAC** (n.) — role-based access control (access tied to a role) versus
  attribute-based access control (access computed from requester and data attributes at
  query time); the second is finer-grained and harder to audit.
- **machine unlearning** (n. phrase) — techniques for removing a specific record's
  influence from an already-trained model, short of full retraining.
- **data-influence retention window** (n. phrase) — the documented maximum time a deleted
  user's data can still be influencing a live model, bounded by the retraining cadence.
- **datasheet** (n.) — a structured document describing a dataset's collection method,
  represented population, and known gaps — the dataset-level analogue of a model card.

**Expressive phrases — for stating a trade-off fluently instead of listing pros/cons:**

- **"…is an intention, not governance"** — a sharp, quotable line for distinguishing stated
  policy from a verifiable artifact.
- **propagate** (v.) — to automatically extend a property through downstream
  transformations. *"Classification has to propagate to derived columns, not reset to
  untagged because the column is technically new."*
- **"…said out loud with no more content behind it, signals nothing"** — a direct way to
  preempt a buzzword-only answer by naming the trap before falling into it.
- **surgically** (adv.) — precisely, affecting only the intended target. *"You can't
  surgically remove one user's influence from a trained model after the fact."*
- **"…not the default operational-log retention"** — a precise phrasing habit: stating that
  a compliance requirement must override a generic system default, rather than assuming
  they align.

---

**See also:** [Cost, Security & Multi-Region Governance tutorial](10_cost_security_multiregion.md) · [Reconstructing Model Lineage for an Audit](12_tricky_scenarios_10_audit_lineage_reconstruction.md)
