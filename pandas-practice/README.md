# Pandas Practice

Pandas notebooks written for data engineer interview prep: markdown
explanations paired with runnable code, covering the topics that come up
most often — core Series/DataFrame concepts, I/O and data cleaning,
indexing/merging, groupby/aggregation/window operations, performance and
scaling, and classic coding problems.

**Unlike `../spark_practice/`, these notebooks are executed** — pandas has
no JVM/cluster setup, so `pip install pandas numpy jupyter` was enough to
actually run every cell and check the real output, not just the syntax.
All six notebooks ran end-to-end with zero errors and zero warnings.

## Setup (to re-run these)

```bash
cd pandas_practice
uv venv .venv && uv pip install --python .venv/bin/python pandas numpy jupyter ipykernel nbconvert
source .venv/bin/activate
jupyter notebook notebooks/
# or re-execute all of them headlessly:
jupyter nbconvert --to notebook --execute --inplace notebooks/*.ipynb
```

## Layout

```
pandas_practice/
  notebooks/
    01_pandas_core_concepts.ipynb              <- Series/DataFrame, index alignment, dtypes, vectorization, views vs copies
    02_data_io_and_cleaning.ipynb              <- read_csv/parquet/json, missing data, dedup, category dtype, chunksize
    03_indexing_selection_and_transformation.ipynb <- loc/iloc, str/dt accessors, apply/assign, merge/concat semantics
    04_groupby_aggregation_and_window.ipynb    <- agg/transform/filter, rank (row_number/rank/dense_rank), pivot_table, rolling/expanding
    05_performance_and_scaling.ipynb           <- iterrows vs itertuples vs apply vs vectorized (measured), memory usage, when to leave pandas
    06_interview_coding_problems.ipynb         <- word count, dedup-latest, sessionization, nth-highest-per-group, resample, merge_asof
  .venv/    <- local venv (pandas, numpy, jupyter) used to write and execute these notebooks
```

Each notebook ends with an interview Q&A section and a one-line pointer to
the next topic — read them in order the first time through, then use them
as a quick-reference the day before an interview.

## Related: `../spark_practice/` and `../sql_postgres_practice/`

Every major problem here (top-N per group, dedup-latest-record,
sessionization, nth-highest-value) is solved again in
`../spark_practice/notebooks/` (PySpark) and several also appear in
`../sql_postgres_practice/practice/` (raw SQL) — deliberately, so the same
mental model can be compared across all three APIs. Interviewers commonly
ask you to translate a solution between pandas, Spark, and SQL; reviewing
the three side by side is the point.

`05_performance_and_scaling.ipynb`'s closing section — "when does pandas
stop being the right tool" — is the natural bridge into `../spark_practice/`:
the answer is essentially "once it doesn't fit on one machine anymore."
