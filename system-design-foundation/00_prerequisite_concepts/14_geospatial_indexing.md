# Prerequisite Concepts, Part 14: Geospatial Indexing — Finding What's Nearby

Every prior part in this series indexed data along one dimension at a time — a B-tree's
sorted key, a hash index's exact match, a range shard's contiguous key space. Geographic
proximity breaks that assumption outright: "find everything within 2km of this point" is
inherently a **two-dimensional** question, latitude and longitude together, and none of the
structures already covered generalize to it directly. This part covers the family of
techniques that make "what's nearby" a fast, indexable query instead of a brute-force scan.

## The Problem, Precisely

**Why a normal index doesn't work**: sort locations by latitude alone, then filter by
longitude, and two points can be geographically close while sitting far apart in that sort
order — a point at latitude 40.0° can be next to one at 40.0001° or one at 40.7°, and a 1D
sort has no way to express "near" across two independent axes at once. This is the same
family of problem [Part 11's vector-search section
named](11_taxonomy_of_storage_choice.md#the-newest-arrival-vector-databases-similarity-search-in-high-dimensional-space):
an index built for exact-match or single-dimension ordering doesn't generalize to
"nearest in a multi-dimensional space" without a structure built specifically for it. The
naive fallback — compute the distance from every stored point to the query point, filter by
radius — is exactly [Part 2's full table scan
problem](02_data_and_consistency.md#indexing-why-databases-dont-scan-everything), just in a
different geometry: it works on a small table and falls over completely at real scale.

## Geohash: Turning 2D Proximity Into a 1D String

**The core idea**: recursively bisect the world into a grid. At each step, split the
remaining longitude range in half and record which half the point falls in as a bit, then
do the same for latitude, alternating between the two axes, building up a bit string one
step at a time — then encode that bit string into a short, base32 alphanumeric string.

**The property that makes this useful as an index**: points that are geographically close
usually **share a common prefix**. A geohash of `9q8y` covers a coarse region; `9q8yyk`
covers a much smaller area nested inside it. This means geographic proximity search reduces
to a **string-prefix range query** — exactly the range-scan machinery [Part 10's B-tree
already provides](10_physics_of_persistence.md#b-trees-fully-unpacked-optimizing-for-reads-by-paying-on-writes).
No new storage engine is needed: index the geohash string in a normal B-tree, and "find
everything near this point" becomes "find everything whose geohash starts with this prefix"
— a familiar, already-understood query shape.

**Precision is controlled by string length** — each additional character roughly narrows the
bounding box by a further factor: illustratively, 1 character covers thousands of
kilometers, 5 characters covers a few kilometers, 7 characters covers roughly a city block,
9 characters covers a few meters. Choosing precision is choosing how coarse or fine the
prefix-match granularity is.

### The Boundary Problem — Geohash's Real Flaw

Two points can sit meters apart in the real world while landing on **opposite sides of a
grid cell boundary** — one just east of an edge, the other just west — and end up with
almost no shared geohash prefix at all, despite being neighbors. A naive "search by geohash
prefix" query can silently miss real nearby points sitting just across a cell edge.

**The standard mitigation**: query not just the cell the point falls in, but that cell
*plus its eight neighboring cells* (the 3×3 grid around the query point), then filter the
combined results by actual distance. This catches edge cases at the cost of checking more
cells than strictly necessary — a real, accepted overhead, not a full fix, since the same
edge problem recurs (just less often) at the boundary of that larger 3×3 region too.

## Quad-Trees and R-Trees: Structure-Based Alternatives

**Quad-trees** recursively subdivide 2D space into four quadrants, but — unlike geohash's
fixed-precision grid — only subdivide further where data density actually requires it: a
dense urban area gets subdivided deeply, a sparse rural one stays one large node. This gives
adaptive resolution geohash's fixed grid doesn't have, at the cost of being a genuine tree
structure to maintain and shard, rather than a plain string that slots into an existing
B-tree.

**R-trees** index **bounding boxes**, not just points — the right structure when what's
being indexed is shapes (roads, delivery zones, geofences), not single coordinates.
PostGIS (Postgres's spatial extension) implements its spatial indexes as R-trees via
Postgres's GiST index type, making this the practical default for "give me a real database
with real geospatial queries" rather than a hand-rolled geohash scheme.

## H3: The Modern Industry Answer to the Boundary Problem

Uber open-sourced **H3**, a hexagonal hierarchical spatial index, specifically to fix
geohash's boundary weakness. The core structural difference: **hexagonal cells have uniform
adjacency** — every neighboring cell is the same distance from the center cell, which isn't
true of a rectangular grid (a diagonal neighbor is farther away than an edge neighbor in a
square grid, an asymmetry that makes "check the neighbors too" messier to reason about
correctly). H3 keeps geohash's core trick — a hierarchical, prefix-like indexable cell ID —
while making neighbor-checking and edge handling meaningfully cleaner. It's the structure
actually used in the [ride-hailing dispatch case
study's](../../system_design_practice/04_design_ride_hailing_dispatch/tutorial.md) own
geospatial deep-dive, and has become the practical modern default well beyond Uber itself.

## Choosing Between Them

| Structure | Best for | Real cost |
|---|---|---|
| **Geohash** | Fast to adopt — reuses a plain B-tree/hash index, no new infrastructure | The boundary problem; needs the 3×3-neighbor-cell mitigation |
| **Quad-tree** | Data with very uneven density (dense cities, sparse countryside) | A real tree to build, maintain, and shard, not a plain indexable string |
| **R-tree** | Indexing shapes/regions, not just points (PostGIS's actual default) | More complex than either — designed for bounding boxes, not single coordinates |
| **H3** | Production-grade proximity search at scale, uniform-neighbor correctness | A dedicated library/dependency, not "just add a column to an existing index" |

**The pattern worth naming, echoing [Part 11's whole
taxonomy](11_taxonomy_of_storage_choice.md)**: none of these four wins on every axis — geohash
trades correctness-at-edges for simplicity and reuse of existing indexing infrastructure;
H3 trades that simplicity for genuinely better correctness, at the cost of adopting a
dedicated structure. The right choice is, once again, a first-principles decision about the
actual workload — how much does an edge-case miss actually cost this specific product — not
a default reached for out of familiarity.

## Designing and Operating From First Principles

1. Have I actually checked whether my geospatial queries can tolerate geohash's boundary
   problem — or does a missed nearby result (a driver, a restaurant) have a real product
   cost that makes H3 or an R-tree the more honest choice?
2. If I'm using geohash, am I querying the neighboring cells too, or only the point's own
   cell — the single most common mistake that silently drops real nearby results?
3. Is what I'm indexing actually points, or shapes/regions (delivery zones, geofences) — and
   have I picked a structure (R-tree) built for that, rather than forcing points-only
   tooling onto a shapes problem?
4. Have I chosen my geohash/H3 precision level deliberately, based on the actual radius my
   queries care about — or left it at a default that's either too coarse (misses real
   matches) or too fine (fragments nearby points across too many cells)?

## Key Takeaways

- **Geographic proximity is inherently two-dimensional**, and no structure already covered
  in this series (B-tree, hash index, LSM-tree) generalizes to "nearest in 2D space" without
  a purpose-built technique — the same category of gap [Part 11 named for vector
  search](11_taxonomy_of_storage_choice.md#the-newest-arrival-vector-databases-similarity-search-in-high-dimensional-space).
- **Geohash turns 2D proximity into a 1D string-prefix query**, reusing a plain B-tree —
  cheap to adopt, no new infrastructure required.
- **The boundary problem is geohash's real, named flaw**: nearby points on opposite sides of
  a cell edge can share almost no prefix at all — mitigated, not eliminated, by querying the
  3×3 neighborhood of cells around a point.
- **Quad-trees give adaptive resolution** (dense areas subdivide further, sparse ones don't)
  at the cost of being a real tree to build and shard, not a plain indexable string.
- **R-trees index bounding boxes/shapes, not just points** — PostGIS's actual default via
  GiST indexes, and the right tool when what's stored is regions, not coordinates.
- **H3 (Uber) fixes geohash's boundary weakness structurally** with hexagonal cells and
  uniform neighbor adjacency, at the cost of adopting a dedicated library rather than reusing
  an existing index.
- **No structure wins on every axis** — the choice is a first-principles trade-off (Part
  11's whole taxonomy, applied here) between simplicity/reuse and correctness at cell edges,
  not a default reached for out of familiarity.

## Quick Self-Check

- Why can't sorting locations by latitude, then filtering by longitude, answer "what's
  nearby" correctly — what specifically breaks?
- Explain precisely why a geohash prefix match can be reused with a plain B-tree index,
  rather than needing a dedicated spatial storage engine.
- Two points are 10 meters apart in the real world but share zero geohash prefix
  characters. How is this possible, and what query-time fix catches this case?
- Why does a quad-tree's adaptive subdivision matter for data with very uneven density
  (a dense city center vs. sparse countryside) in a way a fixed-precision geohash grid
  doesn't handle as well?
- Why is an R-tree the right structure for indexing delivery zones or geofences, when a
  geohash or H3 index (built for points) isn't?
- What specific structural property of hexagonal cells makes H3's neighbor-checking cleaner
  than geohash's rectangular grid — why does "uniform adjacency" matter here?

## Articulate It: Interview Framing & Vocabulary

### Three Ways to Explain This

- **Dimensionality framing (the default for 'how would you find nearby X' questions):** "I'd
  start by naming why this isn't a normal indexing problem — proximity is two-dimensional,
  and none of the usual structures (B-trees, hash indexes) generalize to 'nearest in 2D
  space' on their own. Geohash's whole trick is turning that 2D problem back into a 1D
  string-prefix query so it can reuse a plain B-tree instead of needing new infrastructure."
- **Boundary-problem framing (good for showing depth beyond 'just use geohash'):** "I'd flag
  geohash's real flaw directly: two points meters apart can land on opposite sides of a grid
  cell and share almost no prefix. The fix is querying the neighboring cells too, not just
  the point's own cell — and if that edge-case miss has a real product cost, I'd reach for
  H3 instead, which fixes the problem structurally with hexagonal, uniformly-adjacent cells."
- **Points-vs-shapes framing (good for a delivery-zone/geofencing question):** "I'd separate
  what's actually being indexed — single coordinates versus shapes and regions. Geohash and
  H3 are built for points; if I'm indexing delivery zones or geofences, an R-tree indexing
  bounding boxes (PostGIS's actual default via GiST) is the right structure, not a
  points-only scheme stretched to cover shapes."

### Vocabulary Builder

**Technical shorthand — use these instead of over-explaining the concept every time:**

- **geohash** (n.) — a technique encoding a (latitude, longitude) pair into a short
  alphanumeric string via recursive grid bisection, such that geographically close points
  usually share a common prefix — turns 2D proximity into a 1D range/prefix query.
- **boundary problem (geohash)** (n. phrase) — two geographically close points landing on
  opposite sides of a grid cell edge and sharing little or no geohash prefix; mitigated by
  querying the surrounding 3×3 cell neighborhood, not eliminated outright.
- **quad-tree** (n.) — a tree recursively subdividing 2D space into four quadrants, only as
  deep as local data density requires — adaptive resolution, unlike a fixed-precision grid.
- **R-tree** (n.) — a spatial index over bounding boxes rather than points, the structure
  behind PostGIS's default spatial indexes (via Postgres's GiST index type) — built for
  shapes/regions, not single coordinates.
- **H3** (n., proper — Uber) — a hexagonal hierarchical spatial index fixing geohash's
  boundary weakness via uniform cell adjacency; the modern production default for
  large-scale proximity search.
- **uniform adjacency** (n. phrase) — the property that every neighboring cell is equidistant
  from a hexagon's center, unlike a square grid where diagonal neighbors sit farther away
  than edge neighbors — the structural reason H3's neighbor-checking is cleaner than
  geohash's.

**Expressive phrases — for stating a trade-off fluently instead of listing pros/cons:**

- **"…turning a 2D problem back into a 1D one"** — a compact way to describe geohash's
  entire trick: reusing ordinary indexing infrastructure by encoding proximity as a prefix.
- **"…mitigated, not eliminated"** — a precise way to describe the 3×3-neighbor-cell fix for
  geohash's boundary problem, without overselling it as a full solution.
- **"…points versus shapes is the real fork in the road"** — a fluent way to route a
  geospatial design question toward the right structure (geohash/H3 vs. R-tree) based on
  what's actually being indexed.

---

**Previous:** [Part 13: CAP Theorem & PACELC](13_cap_theorem_and_pacelc.md)  |  **Next:** [Part 15: Caching — Trading Freshness for Speed](15_caching.md)
