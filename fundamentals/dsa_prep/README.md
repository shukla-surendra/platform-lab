# DSA Interview Prep

This is **Track A** from the `product-company-transition-plan_1.md` transition plan. Track
B (ML/LLM System Design) lives in `../system_design_foundation/` — both are part of the
same single MkDocs site (see the repo root README), reachable from the nav tabs above
rather than a separate server.

Run `make serve` from the repo root to preview the whole site, or `make build` for a
static build.

A curated, topic-organized set of the highest-frequency coding interview problems
(roughly the well-known "Top 150" tier — Blind 75 + NeetCode 150 extras), each with:

- `problem.md` — statement, the general pattern this problem teaches, a step-by-step
  approach with the reasoning behind it, and complexity
- `solution.py` — clean Python solution + runnable sample test cases (`python3 solution.py`)

Each topic folder also has a `PATTERN.md` — a deeper, problem-agnostic writeup of the
technique itself: how to recognize when it applies, the general template, common
variations, and pitfalls. Read it once per topic; it'll make every problem in that folder
click faster.

## How to use this

1. Work topic by topic in the order below — it's roughly increasing difficulty/dependency
   (e.g. two pointers before sliding window, trees before graphs, 1-D DP before 2-D DP).
2. Start each topic by skimming its `PATTERN.md` to get the general technique in your head.
3. Read a problem's `problem.md`, attempt it yourself, *then* check `solution.py`.
4. Run the solution file directly to sanity-check: `python3 <topic>/<NN>_<name>/solution.py`
5. See `TOP_LIST.md` for a flat priority-ordered checklist if you only have time for a subset.

## Topics (in suggested order)

| # | Folder | Topic |
|---|--------|-------|
| 1 | `arrays_hashing/` | Arrays & Hashing |
| 2 | `two_pointers/` | Two Pointers |
| 3 | `sliding_window/` | Sliding Window |
| 4 | `stack/` | Stack |
| 5 | `binary_search/` | Binary Search |
| 6 | `linked_list/` | Linked List |
| 7 | `trees/` | Trees / BST |
| 8 | `tries/` | Tries |
| 9 | `heap_priority_queue/` | Heap / Priority Queue |
| 10 | `backtracking/` | Backtracking |
| 11 | `graphs/` | Graphs (BFS/DFS/Union-Find/Topo Sort) |
| 12 | `dp_1d/` | 1-D Dynamic Programming |
| 13 | `dp_2d/` | 2-D Dynamic Programming |
| 14 | `greedy/` | Greedy |
| 15 | `intervals/` | Intervals |
| 16 | `math_geometry/` | Math & Geometry |
| 17 | `bit_manipulation/` | Bit Manipulation |

Each problem folder is numbered `NN_problem_name/` for a sensible working order within the topic.

## Difficulty ranking: toughest → medium

If you're short on time and sampling a subset of topics (e.g. two problems per pattern),
weight your time toward the top of this list — this is roughly where FAANG/MAANG loops
actually separate candidates, based on each topic's actual Hard/Medium/Easy mix and how
consistently it shows up across companies. Ranks 11-17 are still universal and asked
everywhere, but rarely the "hard" question in a loop.

| Rank | Folder | Easy/Med/Hard | Why |
|---|---|---|---|
| 1 | `dp_2d/` | 0/3/1 | 2D DP (edit distance, knapsack) — hardest to derive live. |
| 2 | `graphs/` | 0/6/1 | Topological sort, multi-source BFS — high variance. |
| 3 | `dp_1d/` | 1/8/0 | No Hard-tagged problems, but 8 mediums (LIS, coin change, word break) — deep, heavily tested. |
| 4 | `backtracking/` | 0/4/1 | N-Queens, word search — recursion + pruning under time pressure. |
| 5 | `trees/` | 4/4/1 | Max path sum, validate BST are genuinely hard; rest is core. |
| 6 | `heap_priority_queue/` | 2/2/1 | Median-from-stream is a real differentiator. |
| 7 | `tries/` | 0/2/1 | Word Search II is hard; shows up less outside Google/Amazon. |
| 8 | `two_pointers/` | 1/2/1 | Trapping Rain Water is the hard end; otherwise foundational. |
| 9 | `sliding_window/` | 1/3/1 | Min Window Substring is hard; extremely common pattern. |
| 10 | `linked_list/` | 3/2/1 | Merge K Sorted Lists is hard; rest skews easy/medium. |
| 11 | `intervals/` | 1/4/0 | All medium, no hard — asked at nearly every company. |
| 12 | `arrays_hashing/` | 3/5/0 | Foundational, medium-heavy, asked in round 1 everywhere. |
| 13 | `binary_search/` | 1/3/0 | "Search on the answer" variants trip people up, capped at medium. |
| 14 | `stack/` | 1/3/0 | Medium-heavy, universal (valid parens, daily temps). |
| 15 | `greedy/` | 0/4/0 | All medium — proving correctness is the hard part, no Hard-tagged problems. |
| 16 | `math_geometry/` | 0/3/0 | Medium only; less universal — matrix/geometry-heavy products. |
| 17 | `bit_manipulation/` | 5/0/0 | All easy — a round-1 filter, not a differentiator. |

## Status

**Complete — 90 problems across all 17 topics.** Every `solution.py` has been run and its
sample tests pass (`90/90` green as of the last full sweep).

- [x] arrays_hashing (8)
- [x] two_pointers (4)
- [x] sliding_window (5)
- [x] stack (4)
- [x] binary_search (4)
- [x] linked_list (6)
- [x] trees (9)
- [x] tries (3)
- [x] heap_priority_queue (5)
- [x] backtracking (5)
- [x] graphs (7)
- [x] dp_1d (9)
- [x] dp_2d (4)
- [x] greedy (4)
- [x] intervals (5)
- [x] math_geometry (3)
- [x] bit_manipulation (5)
