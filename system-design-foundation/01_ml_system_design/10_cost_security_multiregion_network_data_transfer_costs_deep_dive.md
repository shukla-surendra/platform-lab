# Deep-Dive: Network / Data-Transfer Costs on AWS, GCP, and Azure

A practical companion to the
[Cost, Security & Multi-Region Governance tutorial](10_cost_security_multiregion.md) — that tutorial covers
cost *attribution* (whose budget a request's cost lands on); this covers a cost most
engineers can't actually explain when asked: **why does moving the same bytes cost
$0, or $0.01/GB, or $0.09/GB, depending on nothing except *which path* they traveled?**
This is one of the most consequential and least-understood line items in any real cloud
bill, and it comes up constantly as a system-design follow-up ("what does this cost at
scale," "why is our bill higher than we expected").

## First principles: why moving data costs money at all

The internet isn't one network — it's thousands of independently-operated networks (your
home ISP, AWS, a corporate network, another cloud) connected to each other via **peering**
(two networks agreeing to exchange traffic, often without money changing hands, when their
traffic volumes are roughly balanced) or **transit** (paying a larger network to carry your
traffic the rest of the way). Every time data crosses from one network to another, someone
is paying for the physical capacity — fiber, routers, and in some cases actual undersea
cables — that carries it.

**Your home ISP bill is a flat fee for *capacity*, not a metered fee for *bytes moved*.**
You pay for a bandwidth tier (e.g. "500 Mbps") regardless of how many actual gigabytes you
move that month, because a residential ISP's cost structure is dominated by the fixed cost
of laying and maintaining the last-mile cable to your home, not the marginal cost of the
bytes themselves — and because most residential connections rarely saturate their pipe
24/7, flat-rate pricing is simpler to sell and administer than metering.

**Cloud providers do the opposite: they meter *bytes*, not *pipe size*, and specifically
meter the direction data leaves their network (egress).** Why the asymmetry:

- **Ingress is free because clouds want your data.** More data stored/processed is more
  revenue from compute and storage — making it free to send data in is a deliberate
  strategic choice, not evidence it's free to carry.
- **Egress is metered because it crosses a real peering/settlement boundary, at a scale
  where that boundary has a real cost.** When a cloud provider's network hands data off to
  your ISP, or to another cloud, at exabyte scale, that's a genuine capacity cost on both
  sides of the handoff — unlike a single home user's traffic, which is a rounding error to
  the networks it crosses.
- **Egress pricing is also, demonstrably, partly a lock-in lever — not purely cost
  recovery.** The clearest evidence: in 2024, regulatory pressure (the EU Data Act, which
  entered into force January 11, 2024) led **all three major clouds** to announce waivers
  of egress fees specifically for customers migrating *off* their platform — AWS (announced
  March 5, 2024, a 90-day free-egress window on request), Google Cloud (announced January
  11, 2024, first mover, requiring account termination within 60 days of migration), and
  Azure (announced March 2024, a 60-day window tied to subscription cancellation). If
  egress pricing were purely a pass-through of real peering costs, there'd be no reason a
  regulator forcing a one-time waiver would matter — the fact that it took regulatory
  pressure to get a *temporary, migration-only* discount is itself evidence the standing
  price includes more than infrastructure cost. **The waivers are one-time-exit-only, not
  a change to standing multi-cloud/hybrid pricing** — day-to-day egress in an active
  multi-cloud architecture is still billed at full standard rates.

## The four cost tiers, explained by which boundary is crossed

The pattern across all three clouds follows the same logic once you see it: **cost tracks
which physical/logical boundary the data crosses, not physical distance.**

1. **Same AZ, private IP → free.** Traffic never leaves the provider's internal network
   fabric — it's switching within their own data center, the same category of cost as a
   packet moving between two ports on the same switch.
2. **Same AZ, *public or Elastic* IP → charged, on AWS specifically.** This is the classic
   gotcha: even though the two instances are physically adjacent, routing through a public/
   Elastic IP sends the traffic out through the internet-gateway/edge path *logically*,
   which is billed like normal data transfer even though it never actually left the
   building. **Cost follows the logical path, not physical proximity** — the single most
   useful mental model in this whole topic.
3. **Cross-AZ, same region → small charge (except Azure).** Separate physical facilities
   need a dedicated inter-DC backbone the provider built and maintains — a real, if small,
   marginal cost, and (AWS/GCP) charged on **both** ends of the transfer.
4. **Cross-region → larger charge.** Now it's the provider's global backbone (or leased
   undersea cable capacity for intercontinental pairs) — real infrastructure with a real
   capacity cost, and pricing that in Azure's and GCP's case explicitly varies by which
   continents are involved.
5. **Internet egress → the largest, tiered charge.** The data leaves the provider's network
   entirely, into a peering/transit relationship whose cost depends on the destination
   network — hence the tiering (cheaper at higher committed volume) and the fact that this
   is the tier the 2024 migration waivers specifically targeted.

## Worked example: an EKS pod downloading from the internet — is it free?

A concrete case worth walking through fully, because the honest answer is "it depends on
the path," not a flat yes — and it's exactly the kind of nuance that trips people up.

**Direction is defined by the cloud's network, not the pod.** When a pod downloads
something — a dataset, a model checkpoint, an API response — data flows *into* AWS's
network from outside. That's **ingress**, even though from the pod's point of view it
feels like "receiving." The pod's own outbound request (the HTTP GET itself) is technically
egress in the other direction, but it's just headers/a URL — negligible size. The actual
payload being downloaded is the ingress side, and **that's the one that's free** — verified,
no exceptions, across all three clouds for standard internet-to-cloud transfer.

**But "free" only holds for the pure data-transfer charge — the path matters, and this is
where the NAT Gateway gotcha from the trade-offs section below actually bites.** Verified
directly against AWS's own pricing page: NAT Gateway's data-processing fee applies *"for
each gigabyte processed through the NAT gateway regardless of the traffic's source or
destination,"* and *"you also incur standard AWS data transfer charges for all data
transferred via the NAT gateway"* — **in addition to** that fee. Two separate, additive
line items, and only one of them is free.

| Path the download takes | What's actually charged |
|---|---|
| Pod has a direct public IP, no NAT Gateway in the path | Genuinely free — pure ingress, nothing else in the way |
| Pod is in a **private subnet**, routing to the internet through a **NAT Gateway** (the common default EKS setup) | The data-transfer charge is still $0 (ingress) — **but the NAT Gateway's $0.045/GB data-processing fee applies to those same bytes anyway**, metered in both directions regardless of the transfer charge being free |
| Pod pulls from an AWS service in the **same region** via a **VPC Endpoint / Gateway Endpoint** (e.g. S3, ECR) instead of the public internet | Genuinely free — bypasses the NAT Gateway entirely, so neither the transfer charge nor the NAT fee applies |

**The practical upshot**: a pod downloading a large dataset or container image from a
public source (Hugging Face, Docker Hub, a public API) is free as far as the
internet-ingress transfer charge goes — but if that pod sits behind a NAT Gateway, which
most production EKS clusters do for security, the download still incurs the NAT Gateway's
per-GB fee on every byte, just under a different line item than "data transfer." At any
meaningful volume (a training pipeline pulling large datasets repeatedly, say), the fix is
routing that specific traffic through a VPC endpoint instead of letting it default through
NAT — the same fix already named in the trade-offs table below.

## Verified current pricing, by provider

**Numbers below verified directly against each provider's own pricing pages** where
possible; anything not independently confirmed is flagged explicitly rather than presented
as certain — cloud pricing changes over time, re-verify before using these in a real cost
model.

### AWS

| Path | Price | Notes |
|---|---|---|
| Ingress from internet | Free | No exceptions found |
| Egress to internet | First 100 GB/month free, then **$0.09/GB** (next ~10 TB), decreasing at higher tiers | Free tier aggregates across services/regions, excludes China/GovCloud |
| Same AZ, private IP | Free | |
| Same AZ, public/Elastic IP | **Charged** like normal transfer (~$0.01/GB) | The gotcha above |
| Cross-AZ, same region | **$0.01/GB**, charged on both sender and receiver | Effectively $0.02/GB round-trip for a request/response pair |
| Cross-region | **~$0.02/GB** (varies by region pair) | Only the sending region is billed |
| NAT Gateway | $0.045/hour **plus** $0.045/GB data-processing fee, **on top of** standard transfer charges | Traffic through a NAT Gateway is billed twice — processing fee + transfer fee — a very common surprise line item |

Source: aws.amazon.com/ec2/pricing, aws.amazon.com/vpc/pricing.

### GCP

| Path | Price | Notes |
|---|---|---|
| Ingress from internet | Free | |
| Egress to internet (Premium Tier, default) | $0.12/GB (0-1 TiB), $0.11/GB (1-10 TiB), $0.085/GB (10 TiB+) for NA/Europe/most of Asia; higher for Indonesia/Korea/South America | Effective Feb 1, 2024. Only ~1 GiB/month is in the Always-Free tier |
| Same zone, private IP | Free | |
| Cross-zone, same region | **$0.01/GB** | Similar model to AWS |
| Cross-region | **$0.02/GB** (NA↔NA) up to **$0.14/GB** (any region↔South America) | Varies materially by continent pair — genuinely worth checking the specific pair for a real cost model |
| Premium vs. Standard Tier | Premium routes over Google's private global backbone (lower latency, costlier); Standard routes over public internet peering (cheaper, more restricted — not available for all resource types, e.g. global load balancers) | A GCP-specific cost-optimization lever the other two clouds don't have an equivalent of |

Source: cloud.google.com/vpc/pricing-announce.

### Azure

| Path | Price | Notes |
|---|---|---|
| Ingress | Free | |
| Egress to internet | First 100 GB/month free, then **~$0.087/GB** (NA/Europe, 100GB-10TB tier), decreasing at higher tiers; higher for Asia/Australia/MEA, highest for South America | Pricing tiers split by **source continent**, not destination — a nuance that differs from AWS/GCP |
| Same AZ | Free | |
| Cross-AZ, same region | **Free** — eliminated **May 2024**, for both private and public IP traffic | **The genuine differentiator from AWS/GCP**, both of which still charge for this |
| Cross-region | ~$0.02/GB intra-continental (NA/Europe) up to ~$0.16/GB (South America) | |

Source: azure.microsoft.com/pricing/details/bandwidth.

## Side-by-side comparison

| | AWS | GCP | Azure |
|---|---|---|---|
| Internet egress free tier | 100 GB/mo | ~1 GiB/mo (Always Free) | 100 GB/mo |
| Internet egress starting rate | $0.09/GB | $0.12/GB (Premium Tier) | ~$0.087/GB |
| Cross-AZ (same region) | $0.01/GB, both ends | $0.01/GB | **Free** (since May 2024) |
| Cross-region | ~$0.02/GB | $0.02-$0.14/GB by continent pair | ~$0.02-$0.16/GB |
| Distinctive gotcha | NAT Gateway double-charge; same-AZ public IP still billed | Premium/Standard Tier choice | Pricing tiered by *source* continent, not destination |

**The one number worth memorizing**: Azure is the only one of the three that made
cross-AZ transfer free — if a design's cost model leans heavily on multi-AZ replication
traffic, that single fact can materially change which cloud is cheaper for that specific
workload, independent of every other pricing line.

## Trade-offs

| Decision | Option A | Option B | When to pick which |
|---|---|---|---|
| Cross-AZ replication cost sensitivity | Accept AWS/GCP's per-GB cross-AZ charge | Move the workload to Azure, or minimize cross-AZ chatter (co-locate chatty services in one AZ, accepting reduced AZ-fault isolation) | If cross-AZ traffic volume is genuinely large and AZ-level fault isolation isn't the dominant requirement, the cost delta is real enough to model explicitly, not assume away |
| NAT Gateway usage | Route all outbound traffic through a NAT Gateway (simple, standard) | Use VPC endpoints / PrivateLink for AWS-service traffic specifically, bypassing NAT entirely for that portion | VPC endpoints avoid both the NAT Gateway's hourly charge and its data-processing fee for traffic to AWS services (S3, DynamoDB, etc.) — a common, high-leverage cost optimization |
| GCP network tier | Premium Tier (default) | Standard Tier where eligible | Standard Tier is a real lever for cost-sensitive, latency-tolerant, region-local traffic; not available for all resource types |
| Multi-cloud migration timing | Migrate opportunistically, absorbing standard egress rates | Time a full exit to use the 2024 regulatory-driven waiver window | The waiver is one-time and requires full account/subscription termination within a short window (60-90 days) — only worth planning around for a genuine full exit, not an ongoing hybrid architecture |

## Failure Modes to Raise Proactively

- **Same-AZ traffic accidentally routed through public/Elastic IPs on AWS** — silently
  billed like normal transfer despite zero physical distance; the fix is verifying private
  IP/VPC-internal routing is actually what's happening, not assuming AZ co-location alone
  is free.
- **NAT Gateway data-processing fee compounding with transfer charges** — a workload
  pushing meaningful volume through a NAT Gateway pays *twice*; VPC endpoints/PrivateLink
  are the standard fix for AWS-service-bound traffic specifically.
- **Cross-region replication costs scaling silently with growth** — a multi-region
  architecture's data-transfer line item grows with data volume, not request count; a cost
  model built around request volume alone will miss this until the bill arrives.
- **Assuming the 2024 egress waivers apply to ongoing multi-cloud traffic** — they don't;
  they're one-time, exit-only, and time-boxed (60-90 days), not a standing change to
  day-to-day cross-cloud pricing.
- **GCP Standard Tier assumed universally available** — it isn't; some resource types
  (e.g. global load balancers) require Premium Tier, so a cost model can't assume Standard
  Tier savings apply uniformly across an architecture.

## Make It Yours

- Look at a real cloud bill you've seen (yours or a project's) — was data transfer a
  line item anyone had actually modeled in advance, or a surprise?
- If you've run a multi-AZ or multi-region architecture, was cross-AZ/cross-region
  transfer cost ever explicitly weighed against the fault-isolation benefit it buys, or
  was multi-AZ just assumed as a default with the cost accepted unexamined?
- Have you seen (or can you construct) a NAT Gateway double-charge scenario, and what
  would the VPC-endpoint fix have saved?

## Practice Questions

- Design the network topology for a service with heavy East-West (service-to-service)
  traffic across three AZs in one region — where does the transfer cost actually
  accumulate, and how would you reduce it without giving up AZ-level fault isolation?
- A team's monthly cloud bill has a data-transfer line item that's grown 5x in three
  months with no corresponding growth in request volume — walk through your diagnostic
  process live.
- You're advising a team planning to migrate off AWS to GCP over the next quarter — how
  would you structure the migration to take advantage of the 2024 egress-waiver policy,
  and what constraints does that waiver impose on the migration plan?

## Articulate It: Interview Framing & Vocabulary

### Three Ways to Explain This

- **Boundary-crossing framing (the default for this topic):** "Network cost tracks which
  boundary the data crosses, not physical distance — same-AZ private traffic never leaves
  the provider's internal fabric, so it's free; the moment traffic crosses into a public
  routing path, a different AZ, a different region, or out to the internet entirely, a
  real capacity cost gets incurred and billed, in roughly that increasing order."
- **Peering-economics framing (good for 'why does egress cost more than ingress'):**
  "Ingress is free because clouds want your data — it's a strategic choice, not a cost
  reflection. Egress is metered because it crosses a real peering or transit boundary at a
  scale where that boundary has genuine settlement cost — and the fact that regulators had
  to force a temporary migration-only waiver in 2024 is itself evidence egress pricing
  isn't purely cost-recovery."
- **ISP-analogy framing (good for grounding this for someone new to cloud billing):**
  "A home ISP charges a flat fee for *capacity* because most residential usage never
  saturates the pipe and their costs are dominated by fixed last-mile infrastructure.
  Clouds meter *bytes*, specifically on egress, because at their scale actual bytes moved
  is a far more precise proxy for real infrastructure and peering cost than a flat access
  fee would be — and it's also more profitable, which is why egress fees became a
  regulatory target."

### Vocabulary Builder

- **peering** (n.) — two networks agreeing to exchange traffic directly, often without
  payment, when their traffic volumes are roughly balanced; the alternative to transit.
- **transit** (n.) — paying a larger network to carry your traffic onward to the rest of
  the internet, the arrangement smaller networks (and cloud customers' own ISPs) typically
  rely on.
- **last-mile cost** (n. phrase) — the fixed infrastructure cost of the final physical
  connection to an end user, the dominant cost driver behind flat-rate residential ISP
  pricing.
- **"…cost follows the logical path, not physical proximity"** — the single most useful
  phrase for explaining the same-AZ-public-IP gotcha, or any case where physically-close
  resources still incur transfer charges because of how the traffic is routed.
- **egress fee as lock-in** — the industry criticism, evidenced concretely by the 2024
  regulatory-driven waivers, that standing egress pricing serves a switching-cost function
  beyond pure infrastructure cost recovery.

---

**See also:** [Cost, Security & Multi-Region Governance tutorial](10_cost_security_multiregion.md) ·
[Data Governance in MLOps](10_cost_security_multiregion_data_governance_deep_dive.md)
