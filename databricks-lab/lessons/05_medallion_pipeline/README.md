# Lesson 5: a medallion pipeline

**Idea:** bronze keeps raw data, silver validates and deduplicates (rejects are quarantined, not lost), gold is rebuilt per day with `replaceWhere` so reruns are safe.

**Run:** `uv run python lessons/05_medallion_pipeline/lesson.py`

**Watch for:**
- bad rows end up in the rejects table with a reason
- the duplicate order appears once in silver
- re-running the gold build for a day leaves totals unchanged

**Exercise:** change the rule so a negative amount is also rejected, and check the rejects table.

Concepts: [Pipelines](../../docs/05-pipelines-jobs-and-cicd.md), [Patterns](../../docs/07-data-engineering-patterns.md)
