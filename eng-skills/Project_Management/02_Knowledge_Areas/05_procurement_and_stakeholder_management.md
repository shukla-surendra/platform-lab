# Procurement and Stakeholder Management

The two remaining PMBOK knowledge areas, grouped together because both govern relationships that cross the project team's own boundary — procurement outward to vendors and contract structures, stakeholder management outward to everyone with an interest in the outcome. For a contractor specifically, procurement is not abstract vocabulary — it is the legal skeleton of one's own engagement, covered practically in `../../Communication-Mastery/02_Thinking_Frameworks/11_role_clarity_and_expectation_contracts.md` §7; this chapter supplies the PMI terminology underneath that practical guidance.

## Index

1. [Procurement Management](#1-procurement-management)
2. [Contract Types](#2-contract-types)
3. [The Procurement Life Cycle](#3-the-procurement-life-cycle)
4. [Stakeholder Management](#4-stakeholder-management)
5. [Stakeholder Analysis Tools](#5-stakeholder-analysis-tools)
6. [Glossary — Vocabulary Used in This Chapter](#6-glossary--vocabulary-used-in-this-chapter)

---

## 1. Procurement Management

### Definition

The processes necessary to purchase or acquire products, services, or results needed from outside the project team.

### Key artifacts and concepts

| Term | Definition |
|---|---|
| **Procurement management plan** | How procurement will be handled, from solicitation through contract closure |
| **Statement of Work (SOW)** | Describes the products/services to be procured in enough detail for prospective sellers to determine if they can provide them — the document a contractor's own engagement is built on (`../../Communication-Mastery/02_Thinking_Frameworks/11_role_clarity_and_expectation_contracts.md` §7) |
| **Make-or-buy analysis** | Determining whether particular work can best be accomplished by the project team or should be purchased from outside — the formal name for the "build it ourselves or hire a contractor / use a managed service" decision |
| **Bid documents** | Used to solicit proposals from prospective sellers — RFI (Request for Information), RFQ (Request for Quotation), RFP (Request for Proposal), roughly in increasing order of formality and specificity |
| **Source selection criteria** | The criteria used to rate or score proposals — price, technical approach, management approach, past performance |
| **Contract** | A mutually binding agreement that obligates the seller to provide value and the buyer to provide compensation |
| **Procurement Statement of Work (procurement SOW)** | The specific version of scope included in an actual contract, distinct from the general SOW concept above |
| **Claims administration** | The process of documenting, processing, monitoring, and managing contested changes where buyer and seller cannot reach agreement — the formal channel for a contract dispute |

[↑ Back to index](#index)

## 2. Contract Types

The contract type determines who bears cost risk — reading it correctly explains a great deal about how a vendor or client will behave during the engagement:

| Type | Structure | Who bears cost risk | Typical use |
|---|---|---|---|
| **Fixed-Price (FP)** | A set total price regardless of actual cost | Seller (contractor/vendor) bears the risk — they lose money if costs exceed the price | Well-defined, low-uncertainty scope |
| **Fixed-Price Incentive Fee (FPIF)** | Fixed price plus a financial incentive tied to performance metrics | Mostly seller, with upside for exceeding targets | Scope is defined but performance quality varies meaningfully |
| **Cost-Reimbursable (CR)** | Buyer reimburses actual allowable costs, plus a fee | Buyer (client) bears the risk — cost overruns are the client's problem | High-uncertainty, evolving-scope work — most R&D-flavored engagements, including much ML work |
| **Cost Plus Fixed Fee (CPFF)** | Costs reimbursed, plus a fixed fee regardless of final cost | Buyer | Similar to CR, with a stable seller margin |
| **Cost Plus Incentive Fee (CPIF)** | Costs reimbursed, plus a fee that varies with performance against targets | Buyer, with a shared-upside mechanism | Long engagements where quality/schedule performance should be incentivized |
| **Time and Materials (T&M)** | Payment based on hours worked at agreed rates, plus materials — a hybrid, capped or uncapped | Shared, or largely buyer if uncapped | Short engagements, unclear scope, staff-augmentation contracting — the structure most individual contractor engagements actually use |

The single most consequential piece of vocabulary here for a contractor: **T&M contracts put schedule risk on the client, not the contractor** — which is precisely why scope creep is a *legitimate, expected renegotiation point* under T&M (unlike fixed-price, where the contractor absorbs it), and why the change-order framing in `../../Communication-Mastery/02_Thinking_Frameworks/11_role_clarity_and_expectation_contracts.md` §7 point 4 is not aggressive, it is simply how a T&M engagement is supposed to work.

[↑ Back to index](#index)

## 3. The Procurement Life Cycle

```
Plan Procurement → Conduct Procurement (solicit, select, award)
    → Control Procurement (monitor performance, manage changes)
        → Close Procurement (formal acceptance, contract closure)
```

For a contractor, this maps directly onto the engagement's own arc: the SOW and contract type are set during "Plan/Conduct," performance is reviewed continuously during "Control" (this is where renewal or extension decisions actually get made, informally, long before the formal date), and "Close Procurement" is the formal handover — matching the exit-engineering guidance in `../../Communication-Mastery/02_Thinking_Frameworks/11_role_clarity_and_expectation_contracts.md` §7 point 5.

[↑ Back to index](#index)

## 4. Stakeholder Management

### Definition

The processes required to identify the people, groups, or organizations that could impact or be impacted by the project, analyze their expectations, and develop strategies to effectively engage them.

### Key artifacts and concepts

| Term | Definition |
|---|---|
| **Stakeholder register** | Identifies all project stakeholders, with assessment information (interests, involvement, impact) and classification |
| **Stakeholder engagement plan** | Strategies for engaging stakeholders effectively, based on their needs, interests, and potential impact |
| **Stakeholder engagement assessment matrix** | Tracks each stakeholder's *current* engagement level against their *desired* engagement level, revealing exactly where effort needs to be spent |
| **Engagement levels** | **Unaware** → **Resistant** → **Neutral** → **Supportive** → **Leading** — a stakeholder's position can be plotted at any point along this spectrum, and moving them is the explicit goal of engagement activities |

[↑ Back to index](#index)

## 5. Stakeholder Analysis Tools

| Tool | What it does |
|---|---|
| **Power/Interest grid** | Plots stakeholders on two axes — power (ability to influence outcomes) and interest (degree of concern about outcomes) — into four quadrants: **manage closely** (high power, high interest), **keep satisfied** (high power, low interest), **keep informed** (low power, high interest), **monitor** (low power, low interest) |
| **Power/Influence grid** | A variant plotting power against active involvement/influence, rather than interest |
| **Impact/Influence grid** | Plots stakeholder ability to affect changes to planning/execution (influence) against their ability to cause change to the project's outcome (impact) |
| **Salience model** | Classifies stakeholders by three attributes — **power** (ability to impose will), **urgency** (need for immediate attention), **legitimacy** (appropriateness of involvement) — useful for the more complex case of many stakeholders with overlapping, non-obvious claims |

Worked example using the power/interest grid: a **CFO reviewing an MLOps platform's budget** is high power, and interest that spikes specifically around cost-review cycles — squarely in "manage closely" during those windows, and "keep satisfied" otherwise. A **data scientist consuming the platform daily** is typically lower power but very high interest — "keep informed," with a strong bias toward *frequent, detailed* communication even though they can't unilaterally change the project's direction. Misreading a "keep informed" stakeholder as "manage closely" (over-investing scarce relationship-building time) or vice versa (under-investing in someone whose day-to-day satisfaction actually determines whether the platform gets adopted) is a common and avoidable stakeholder-management error — and this grid is precisely the formal version of the stakeholder expectation map already built for engineering roles in `../../Communication-Mastery/02_Thinking_Frameworks/11_role_clarity_and_expectation_contracts.md` §4.

[↑ Back to index](#index)

## 6. Glossary — Vocabulary Used in This Chapter

| Term/Phrase | Meaning |
|---|---|
| Statement of Work (SOW) | The document describing the scope of products/services being procured or delivered |
| Make-or-buy analysis | Deciding whether to perform work internally or procure it externally |
| RFI / RFQ / RFP | Request for Information / Quotation / Proposal — bid solicitation documents of increasing formality |
| Source selection criteria | The criteria used to score and choose among competing proposals |
| Claims administration | The formal process for managing contested, unresolved contract changes |
| Fixed-Price (FP) contract | A contract with a set total price; the seller bears cost-overrun risk |
| Cost-Reimbursable (CR) contract | A contract reimbursing actual costs plus a fee; the buyer bears cost-overrun risk |
| Time and Materials (T&M) | A contract paying for hours worked plus materials, common in staff-augmentation contracting |
| Stakeholder register | The document listing and classifying all identified project stakeholders |
| Engagement level | A stakeholder's current disposition toward a project, from unaware to leading |
| Power/Interest grid | A tool plotting stakeholders by influence and concern to prioritize engagement effort |
| Salience model | A stakeholder classification model based on power, urgency, and legitimacy |
| Squarely | Directly and unambiguously (here: falling clearly within a category) |

[↑ Back to index](#index)
