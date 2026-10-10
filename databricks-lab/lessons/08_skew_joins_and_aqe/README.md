# Lesson 8: skew, joins and AQE

**Idea:** one hot key sends most rows to one partition; broadcast joins avoid the shuffle; salting spreads a hot key; AQE re-plans at runtime.

**Run:** `uv run python lessons/08_skew_joins_and_aqe/lesson.py`

**Watch for:**
- rows-per-partition output showing the imbalance
- `SortMergeJoin` + `Exchange` vs `BroadcastHashJoin` in the plans
- identical results from the salted two-phase aggregation

**Exercise:** change the hot-key share from 70% to 10% and compare the partition sizes.

Concepts: [Spark performance](../../docs/03-spark-internals-and-performance.md)
