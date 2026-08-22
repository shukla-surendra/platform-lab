# Route 53 — Module 1 Gate

**Status:** 🟡 OPEN (awaiting learner answers)
**Covers:** [`../../docs/route53/architecture.md`](../../docs/route53/architecture.md)
**Rule:** Do not advance to M2 until these are answered and graded. Rough wording is fine — this checks the mental model, not phrasing.

> Write your answers under each question (or answer in chat). The mentor grades, patches gaps, then opens M2.

---

## Conceptual

**Q1.** Using the "DNS as a live control plane, not a static phone book" mental model, explain why two different users querying the exact same hostname at the exact same moment can validly receive two different IP addresses from Route 53. Name the specific mechanism responsible.

_Answer:_


**Q2.** Route 53 publishes a 100% availability SLA — a guarantee almost no other AWS service makes. Using the control-plane/data-plane split, explain specifically why this is structurally achievable for Route 53 in a way it wouldn't be for a stateful service like RDS.

_Answer:_


## Scenario

**Q3.** A colleague wants `example.com` (the bare zone apex, not `www.example.com`) to point at an Application Load Balancer whose IP address can change at any time. They try to create a `CNAME` record at the apex and it fails. What's the actual DNS-spec reason this fails, what Route 53-specific feature solves it, and why is that feature also cheaper than the workaround they'd need on a non-AWS DNS host?

_Answer:_


## Predict-the-behavior

**Q4.** A hosted zone's health check requires a quorum across multiple independent global health-checker locations, not a single checker. One checker location, in an isolated network blip, reports the resource unreachable while every other checker location reports it healthy. Predict whether Route 53 marks the resource unhealthy and stops routing to it — and explain the distributed-systems principle that determines the answer.

_Answer:_


---

### Grading (mentor fills in)
- Q1:
- Q2:
- Q3:
- Q4:
- **Verdict:** ⬜ Pass → open M2 · ⬜ Needs patch
