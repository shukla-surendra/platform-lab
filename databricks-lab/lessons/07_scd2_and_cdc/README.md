# Lesson 7: SCD Type 2 and CDC

**Idea:** SCD2 keeps history by closing the old row and inserting a new one (one `MERGE` using a NULL-key trick); CDC must be applied in **source sequence** order, not arrival order.

**Run:** `uv run python lessons/07_scd2_and_cdc/lesson.py`

**Watch for:**
- the changed customer gets two rows with validity ranges
- the out-of-order CDC feed still produces the newest value
- a delete event removes the row

**Exercise:** add a second change for customer 1 and make the SCD2 merge handle two changes in one batch.

Concepts: [Patterns](../../docs/07-data-engineering-patterns.md)
