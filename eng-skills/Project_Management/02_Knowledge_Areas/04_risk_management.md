# Risk Management

The knowledge area governing how uncertainty is identified, analyzed, and acted on before it becomes an incident. This is the PMI discipline with the most direct overlap with an MLOps/Cloud engineer's own instincts — risk management is, at its core, the project-management version of the same threat modeling and failure-mode thinking already native to production engineering — which makes it the fastest knowledge area for an engineer to become genuinely fluent in.

## Index

1. [Definitions](#1-definitions)
2. [The Risk Management Process](#2-the-risk-management-process)
3. [Qualitative Risk Analysis: The Probability–Impact Matrix](#3-qualitative-risk-analysis-the-probabilityimpact-matrix)
4. [Quantitative Risk Analysis](#4-quantitative-risk-analysis)
5. [Risk Response Strategies](#5-risk-response-strategies)
6. [The RAID Log in Detail](#6-the-raid-log-in-detail)
7. [Glossary — Vocabulary Used in This Chapter](#7-glossary--vocabulary-used-in-this-chapter)

---

## 1. Definitions

| Term | Definition |
|---|---|
| **Risk** | An uncertain event or condition that, if it occurs, has a positive or negative effect on one or more project objectives. Note the two-sided definition — PMI explicitly includes **opportunities** (positive risk), not just threats |
| **Individual risk** | A specific uncertain event affecting one or more objectives |
| **Overall project risk** | The effect of uncertainty on the project as a whole, arising from all sources combined, including individual risks |
| **Risk appetite** | The degree of uncertainty an organization or stakeholder is willing to accept, in anticipation of a reward |
| **Risk tolerance** | The degree, amount, or volume of risk an organization or individual will withstand |
| **Risk threshold** | The measure of acceptable variation around an objective, beyond which risk becomes unacceptable |
| **Risk owner** | The person assigned responsibility for monitoring a risk and executing the response plan if it triggers — a risk without a named owner is, functionally, not being managed at all |
| **Trigger condition** | An event or set of circumstances that indicates a risk is about to occur or has occurred |
| **Risk register** | The document containing the results of risk analysis and planning — the master list |

[↑ Back to index](#index)

## 2. The Risk Management Process

```
Plan Risk Management → Identify Risks → Qualitative Analysis → Quantitative Analysis
      → Plan Risk Responses → Implement Risk Responses → Monitor Risks
```

| Step | What happens |
|---|---|
| **Identify Risks** | Determine which risks might affect the project and document their characteristics — techniques include brainstorming, checklists, SWOT analysis, assumption/constraint analysis, and expert judgment |
| **Qualitative Risk Analysis** | Prioritize risks for further analysis by assessing probability and impact (§3) |
| **Quantitative Risk Analysis** | Numerically analyze the combined effect of identified risks on overall project objectives (§4) — often skipped on smaller projects, standard on large or high-stakes ones |
| **Plan Risk Responses** | Develop options and actions to reduce threats and enhance opportunities (§5) |
| **Implement Risk Responses** | Execute the agreed response plans |
| **Monitor Risks** | Track identified risks, identify new ones, evaluate risk process effectiveness throughout the project |

The step most often skipped informally by engineering teams — **Identify Risks as a deliberate, scheduled activity** rather than something that only happens reactively when a risk has already half-materialized. A dedicated risk identification session at project start (and revisited at each phase gate) surfaces risks while they're still cheap to plan around, the same "influence is cheapest early" principle from `../01_Foundations/01_what_is_project_management.md` §3.

[↑ Back to index](#index)

## 3. Qualitative Risk Analysis: The Probability–Impact Matrix

The standard technique for prioritizing risks quickly, without needing numeric modeling. Each risk is scored on two axes — likelihood of occurring, and severity if it does — typically on a 1–5 scale, multiplied to produce a risk score:

```
                          IMPACT
              1(Very Low) 2(Low) 3(Med) 4(High) 5(Very High)
PROBABILITY
5 (Very High)      5        10     15      20        25
4 (High)           4         8     12      16        20
3 (Medium)         3         6      9      12        15
2 (Low)            2         4      6       8        10
1 (Very Low)       1         2      3       4         5

  Score 1–6:   Low priority (monitor)
  Score 8–12:  Medium priority (active response plan)
  Score 15–25: High priority (immediate, senior-visible response)
```

Worked example, MLOps-flavored: "Upstream schema change breaks the feature pipeline" — probability rated 4 (High, given it's happened twice this year), impact rated 4 (High, silent stale-feature serving) → score 16 → high priority, warranting an active mitigation (schema validation at ingestion) rather than passive monitoring. This is the same worked example already used in `../../Communication-Mastery/02_Thinking_Frameworks/12_project_management_literacy_for_engineers.md` §8, now shown with the actual scoring mechanism behind the qualitative judgment call.

[↑ Back to index](#index)

## 4. Quantitative Risk Analysis

Used when a numeric, probabilistic view of overall project risk exposure is needed — typically for large, high-stakes, or contractually significant projects.

| Technique | What it does |
|---|---|
| **Expected Monetary Value (EMV)** | EMV = Probability × Impact (in currency). Summed across all risks, gives an expected cost of risk exposure — a useful number for sizing a contingency reserve (`02_cost_quality_resource_management.md` §1) |
| **Decision tree analysis** | Models a sequence of decisions and their probabilistic outcomes, calculating the EMV of each path to identify the best choice under uncertainty |
| **Monte Carlo simulation** | Runs a model thousands of times with randomized inputs (drawn from probability distributions) to produce a *distribution* of possible project outcomes (e.g., "70% likely to finish by date X") rather than a single point estimate |
| **Sensitivity analysis (tornado diagram)** | Identifies which individual risks or variables have the greatest potential impact on project outcomes, ranked visually — tells the team where to focus mitigation effort first |

Worked EMV example: a risk of a security review adding delay has a 30% probability of occurring and, if it occurs, a $50,000 impact (contractor extension cost). EMV = 0.3 × $50,000 = **$15,000** — the amount that should reasonably sit in the contingency reserve for that specific risk, rather than an arbitrary round number.

[↑ Back to index](#index)

## 5. Risk Response Strategies

PMI defines distinct strategies for **threats** (negative risk) and **opportunities** (positive risk) — a distinction most engineers never hear named, despite using both instinctively:

### For threats

| Strategy | Definition | Example |
|---|---|---|
| **Avoid** | Eliminate the threat by removing its cause | Choosing a managed cloud service instead of self-hosting infrastructure with a known operational risk |
| **Mitigate** | Reduce the probability and/or impact to an acceptable threshold | Adding schema validation to reduce the probability of pipeline breakage |
| **Transfer** | Shift the impact (and often ownership of the response) to a third party | Purchasing insurance; using a vendor's SLA-backed managed service instead of owning the risk internally |
| **Accept** | Acknowledge the risk and take no proactive action, unless it occurs — can be **passive** (do nothing until triggered) or **active** (set aside a contingency reserve) | Accepting a low-probability, low-impact edge case rather than engineering around it |
| **Escalate** | Hand the risk to a level of the organization with the authority to manage it, when it's outside the project team's control | A platform-wide compliance risk that no single project owns |

### For opportunities (the underused, positive-risk mirror)

| Strategy | Definition |
|---|---|
| **Exploit** | Ensure the opportunity is realized with certainty, by eliminating the uncertainty around it |
| **Enhance** | Increase the probability and/or positive impact of the opportunity |
| **Share** | Allocate ownership to a third party better positioned to capture the opportunity |
| **Accept** | Take advantage of the opportunity if it arises, without actively pursuing it |

The distinction most worth internalizing: **"avoid" and "accept" are opposite ends of a spectrum, and the middle (mitigate, transfer) is where almost all real engineering risk work actually lives.** Naming which strategy is being proposed sharpens a risk conversation immediately — "are we mitigating this or accepting it?" forces an explicit choice instead of letting a risk drift unaddressed by default, the same silent-constraint-erosion pattern flagged in `02_cost_quality_resource_management.md` §4.

[↑ Back to index](#index)

## 6. The RAID Log in Detail

Introduced operationally in `../../Communication-Mastery/02_Thinking_Frameworks/12_project_management_literacy_for_engineers.md` §5 — here is the field-level detail:

| Field | Risks | Assumptions | Issues | Dependencies |
|---|---|---|---|---|
| **Definition** | Uncertain future event with potential impact | Something believed true without verification, on which the plan relies | A risk that has materialized and now requires active management | A reliance on something outside the task's own control |
| **Example** | "Model accuracy might not hit target" | "We're assuming the training data schema is stable" | "The training data schema changed and broke the pipeline" | "Feature pipeline work depends on the platform team's schema migration" |
| **Key fields to track** | Probability, impact, score, owner, response strategy, trigger | What's assumed, and the impact if the assumption proves false | Description, severity, owner, resolution plan, target date | What's depended on, who owns it, needed-by date |
| **Turns into an Issue when** | The risk materializes | The assumption is proven false | (already an issue) | The dependency is missed or delivered late |

The RAID log's real power, worth stating plainly: **an assumption not written down is a risk nobody is tracking, and a dependency not written down is a critical-path item nobody is watching.** The discipline of moving a belief from "in my head" to "a named row in the RAID log" is the single highest-leverage habit in this entire knowledge area, and it costs almost nothing to do at the moment the thought occurs.

[↑ Back to index](#index)

## 7. Glossary — Vocabulary Used in This Chapter

| Term/Phrase | Meaning |
|---|---|
| Risk appetite | The degree of uncertainty an organization is willing to accept for potential reward |
| Risk tolerance | The degree of risk an organization or individual will withstand |
| Risk threshold | The acceptable level of variation around an objective before risk becomes unacceptable |
| Risk owner | The person responsible for monitoring a risk and executing its response |
| Trigger condition | A signal indicating a risk is about to occur or has occurred |
| Probability–impact matrix | A grid scoring risks by likelihood and severity to prioritize response |
| Expected Monetary Value (EMV) | Probability × financial impact, summed to estimate expected risk cost |
| Decision tree analysis | Modeling sequential decisions and probabilistic outcomes to find the best choice |
| Monte Carlo simulation | Running a model many times with randomized inputs to produce a distribution of outcomes |
| Sensitivity analysis / tornado diagram | A ranked visualization of which variables most affect project outcomes |
| Avoid / Mitigate / Transfer / Accept / Escalate | The five standard threat-response strategies |
| Exploit / Enhance / Share / Accept | The four standard opportunity-response strategies |
| RAID log | Running register of Risks, Assumptions, Issues, Dependencies |
| Materialize | (of a risk) To actually occur, converting it from a possibility into a current issue |
| Contingency reserve | Budget set aside for known risks |

[↑ Back to index](#index)
