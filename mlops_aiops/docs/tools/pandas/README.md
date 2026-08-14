# pandas

**Category:** data manipulation / analysis (single-machine, in-memory)

## What it is

pandas is a Python library for working with tabular and time-series data
in memory, built on top of NumPy. Its two core structures are the
`Series` (a single labeled 1-D array) and the `DataFrame` (a 2-D table of
columns, each internally a typed array, sharing a common row index). It
turns "a table" into a first-class object with vectorized operations,
label-based alignment, and a huge standard library of readers/writers
(CSV, Parquet, SQL, JSON, Excel) — the default tool for any dataset that
comfortably fits in one machine's RAM.

## The problem it solves

Raw Python (lists of dicts, or `csv.reader`) makes every row-level
operation an explicit Python-level loop — slow (CPython interpreter
overhead per element) and verbose (manual column extraction, manual type
coercion, manual join logic). NumPy fixes the speed problem for
*homogeneous numeric arrays* but has no concept of labeled columns, mixed
column types in one structure, or missing-value handling. pandas sits on
top of NumPy and adds exactly what's missing for tabular, mixed-type,
partially-missing real-world data: named columns, an index for
alignment, per-column dtypes, and vectorized operations that push the
actual looping down into compiled C/Cython code instead of the Python
interpreter.

## Alternatives

| Tool | How it differs |
|---|---|
| **Polars** | Rust-based, multi-threaded by default, Arrow-backed columnar memory layout, lazy query planning (like Spark's Catalyst) even for single-machine work — generally faster than pandas on the same hardware for the same operation, especially group-by/join-heavy workloads, at the cost of a different (though increasingly pandas-like) API and a younger ecosystem. |
| **Dask** | Parallelizes pandas-like operations across cores or a cluster by splitting a logical DataFrame into many pandas DataFrame partitions and building a lazy task graph — the migration path when data stops fitting on one machine but a full Spark cluster is overkill. |
| **PySpark** (see [Spark](../spark/README.md)) | Distributed, JVM-backed, built for data that doesn't fit in one machine's memory at all and needs to be processed across a cluster; heavier to operate, with a fundamentally different execution model (lazy plan → distributed physical execution) than pandas' eager, single-process execution. |
| **DuckDB** | An embedded, columnar, SQL-first OLAP engine that can query pandas DataFrames, Parquet files, and CSVs directly with SQL, often faster than pandas for aggregation-heavy analytical queries, without needing a server or cluster. |
| **NumPy alone** | Lower-level: fast for homogeneous numeric array math, but no labeled columns, no mixed dtypes in one structure, no built-in missing-data model, no groupby/merge/join vocabulary — pandas is effectively "NumPy plus the parts a real table needs." |
| **Modin** | Drop-in pandas API replacement (`import modin.pandas as pd`) that transparently parallelizes execution across cores (or Dask/Ray as the backend) with minimal code change — a way to get some of Dask's parallelism without rewriting pandas code. |

## Core structures and mechanism

### Series and DataFrame

A `DataFrame` is not a 2-D NumPy array under the hood in the general case
— it's a collection of 1-D arrays (one per column, historically organized
internally into same-dtype "blocks" by the BlockManager, though pandas 2.x
increasingly supports Arrow-backed columns as an alternative backend), all
sharing one `Index` for the rows. This is why:

- Column access (`df["col"]`) is cheap — it's returning/viewing one of the
  underlying arrays, not scanning rows.
- Row access (`df.loc[label]`) is comparatively more expensive — it has to
  pull one element out of every column's array and assemble a new `Series`.
- Mixed dtypes per column are natural (a `DataFrame` can have an `int64`
  column next to an `object` string column next to a `datetime64` column),
  but a single row, if materialized, is dtype `object` — this is the root
  cause of why row-wise iteration (`iterrows()`) is slow and loses type
  information, while column-wise vectorized ops stay fast and typed.

### Index

Every `Series`/`DataFrame` carries an `Index` (row labels) — by default a
`RangeIndex` (0, 1, 2, ...), but can be set to any column (`set_index`),
including a `DatetimeIndex` for time series or a `MultiIndex` for
hierarchical data. The index is what pandas uses for **alignment**:
arithmetic between two Series/DataFrames matches up rows by index label,
not by position — a common source of subtle bugs when two frames that
"look aligned" actually have different (or duplicate, or out-of-order)
index values.

## Indexing: `loc`, `iloc`, and why the distinction matters

| Accessor | Selects by | Example |
|---|---|---|
| `df.loc[...]` | **Label** (index value, column name) | `df.loc[3:5, "amount"]` — rows labeled 3 through 5 *inclusive*, column `amount` |
| `df.iloc[...]` | **Integer position** | `df.iloc[3:5, 0]` — rows at positions 3-4 (Python-slice exclusive), first column by position |
| `df.at[...]` / `df.iat[...]` | Single scalar, by label / by position | Faster than `loc`/`iloc` for single-value access — skips the general-purpose indexing machinery |
| Boolean mask | `df[df["amount"] > 100]` | Row-wise filter; the mask itself is a vectorized comparison, not a loop |
| `df.query("amount > 100")` | String-expression filter | Uses `numexpr` under the hood when available — can be faster than a boolean mask on large frames since it avoids building intermediate boolean arrays in Python |

The `loc`/`iloc` distinction matters because label slicing is
**inclusive** of the end point (`df.loc[3:5]` includes label 5) while
positional slicing follows normal Python semantics (`df.iloc[3:5]`
excludes position 5) — mixing them up silently returns one row more or
fewer than intended, without an error.

### Views vs. copies, and `SettingWithCopyWarning`

```python
subset = df[df["amount"] > 100]   # may be a view OR a copy -- pandas doesn't guarantee which
subset["flag"] = True             # SettingWithCopyWarning: unclear if this mutated df too
```

pandas can't always tell whether a chained selection returned a view into
the original data or an independent copy, so mutating the result of a
chained selection is ambiguous and warned against. The fix is to be
explicit:

```python
subset = df[df["amount"] > 100].copy()   # explicit copy -- safe to mutate
subset["flag"] = True
```

## Vectorization vs. row-wise iteration

The single biggest performance lesson in pandas: **never loop over rows
in Python if a vectorized alternative exists.**

```python
# Slow: Python-level loop, ~100-1000x slower than the vectorized version
# on a non-trivial DataFrame -- every += is a full Python bytecode dispatch
total = 0
for _, row in df.iterrows():
    total += row["amount"]

# Fast: pushes the loop down into compiled C code operating on contiguous
# typed memory (NumPy's ufunc machinery)
total = df["amount"].sum()
```

The reason isn't just "loops are slow in Python" in the abstract — it's
that `iterrows()` additionally reconstructs a full `Series` object (with
its own dtype coercion to `object` when the row is mixed-type) for every
single row, which is far more overhead than the arithmetic itself.
Ranked roughly fastest to slowest for row-wise-feeling logic:

1. **Vectorized built-in ops** (`df["a"] + df["b"]`, `.sum()`, `.where()`,
   boolean masks) — fastest, stays in compiled code the whole time.
2. **`.apply()` on a Series/column** (`df["a"].apply(f)`) — still calls a
   Python function per element, but skips full-row reconstruction; faster
   than row-wise `.apply(axis=1)` but slower than a true vectorized op.
3. **`.apply(f, axis=1)`** — reconstructs a `Series` per row, calls a
   Python function on it; roughly as slow as `iterrows()`, avoid on large
   frames if any vectorized alternative exists.
4. **`.itertuples()`** — meaningfully faster than `iterrows()` when a
   genuine row-wise Python loop can't be avoided, since it returns
   lightweight namedtuples instead of reconstructing a full `Series` per
   row (no dtype coercion, no index lookup machinery).
5. **`iterrows()`** — slowest common option; reconstructs a full `Series`
   per row, coerces mixed dtypes to `object`.

## dtypes and memory

Every column has a dtype, and dtype choice drives both correctness and
memory footprint:

- **Numeric**: `int64`/`float64` by default; downcast with
  `pd.to_numeric(col, downcast="integer")` or explicit `astype("int32")`
  when the value range allows it — meaningful memory savings on large
  frames.
- **`object`**: pandas' catch-all for strings (and anything without a
  dedicated dtype) — each element is a separate Python object with its own
  pointer, the least memory-efficient and slowest-to-operate-on dtype.
- **`category`**: for low-cardinality string columns (e.g. a `status`
  column with 5 distinct values across a million rows), `astype("category")`
  stores the distinct values once and integer codes per row — often a
  10x+ memory reduction and faster groupby/merge on that column, since
  comparisons become integer comparisons instead of string comparisons.
- **Nullable extension types** (`Int64`, `Float64`, `boolean`, `string` —
  capitalized, distinct from `int64`/`bool`/lowercase `str`): support
  `pd.NA` as a genuine missing-value marker without falling back to
  `float64` + `NaN` the way a numpy-backed integer column would (a plain
  `int64` column can't represent a missing value at all — pandas silently
  upcasts it to `float64` the moment a NaN is introduced, which is a common
  source of "why did my ID column become a float" bugs).
- **`datetime64[ns]`**: parsed via `pd.to_datetime()` or `read_csv(...,
  parse_dates=[...])`; enables `.dt` accessor methods and time-based
  indexing/resampling.

Check actual memory usage with `df.memory_usage(deep=True)` — the `deep`
flag matters because without it, `object` columns are reported by pointer
size only, wildly understating their real footprint (the interpreter's
per-object overhead plus the string's own bytes).

## Missing data

pandas represents missing data as `NaN` (for float/object columns,
inherited from NumPy's floating-point NaN) or `NaT` (for datetime
columns) by default, with `pd.NA` as the newer, dtype-agnostic marker used
by the nullable extension types above. Key operations:

- `df.isna()` / `df.notna()` — boolean mask of missing values.
- `df.dropna()` — drop rows (or columns, with `axis=1`) containing any
  (or, with `how="all"`, only rows that are *entirely*) missing values.
- `df.fillna(value)` — fill with a constant, or a per-column dict of
  values, or `method="ffill"`/`"bfill"` to propagate the last/next valid
  observation (common in time series).
- **`None` vs `NaN`**: in an `object` column, `None` and `NaN` can both
  appear and both count as missing under `isna()`, but they're distinct
  Python objects — code that does `col == None` instead of `col.isna()`
  will not catch NaN values, and vice versa. Always use `isna()`/`notna()`
  for missing-value checks, never `==`.

## GroupBy: split-apply-combine

```python
df.groupby("category")["amount"].sum()
```

Mechanically, this is three steps: **split** the DataFrame into groups by
the key column's distinct values, **apply** a function to each group
independently, **combine** the per-group results back into a single
Series/DataFrame. Three ways to apply, in increasing order of
flexibility and decreasing order of speed:

- **`.agg()`** (or the shorthand `.sum()`/`.mean()`/etc.) — one aggregate
  value per group; fastest, since it's typically backed by a compiled
  reduction. `.agg({"amount": "sum", "id": "count"})` for different
  aggregations per column in one pass.
- **`.transform()`** — returns a result the **same length as the input**,
  broadcasting the per-group aggregate back to every row in that group
  (e.g. `df["amount"] - df.groupby("category")["amount"].transform("mean")`
  to center each row by its group's mean) — useful when the per-group
  result needs to line back up with the original rows rather than
  collapsing to one row per group.
- **`.apply()`** — most flexible (the function can return anything: a
  scalar, a Series, a whole DataFrame per group), but slowest, since it
  falls back to calling a Python function per group without the
  compiled-reduction fast path `.agg()` gets for common operations.

## Merge, join, concat

| Operation | What it does |
|---|---|
| `pd.merge(left, right, on="key", how="inner")` | SQL-style join on column values; `how` is `"inner"`/`"left"`/`"right"`/`"outer"`, same semantics as SQL joins. |
| `left.join(right)` | Convenience wrapper around `merge` that joins on the **index** by default rather than a column. |
| `pd.concat([df1, df2])` | Stacks DataFrames — row-wise by default (`axis=0`, like SQL `UNION ALL`), or column-wise (`axis=1`) aligning on index. No key-matching logic — pure concatenation. |

Two `merge` arguments worth knowing because they catch real bugs:

- **`validate="one_to_one"`** (or `"one_to_many"`, `"many_to_one"`,
  `"many_to_many"`) — raises an error if the merge keys don't actually
  satisfy the claimed cardinality. Without this, a merge key with
  unexpected duplicates on either side silently **explodes** the row count
  (every matching pair produces a row — a `1:many` merge where you assumed
  `1:1` can silently multiply your row count and double-count downstream
  aggregates) instead of erroring.
- **`indicator=True`** — adds a `_merge` column (`"left_only"`,
  `"right_only"`, `"both"`) showing which side each row's key came from;
  useful for auditing an outer join to see exactly what didn't match.

## Reshaping

- **`pivot_table`**: turns long-format data into wide format, with an
  aggregation function for when multiple rows map to the same
  (index, column) cell (`pivot` alone requires unique combinations and
  errors otherwise).
- **`melt`**: the inverse — wide format to long format, useful for turning
  many similarly-named columns (`jan_sales`, `feb_sales`, ...) into two
  columns (`month`, `sales`).
- **`stack`/`unstack`**: move a column level into the row index (or back),
  operating on `MultiIndex` structures.

## Time series

- Set a `DatetimeIndex` (`df.set_index("timestamp")` after
  `pd.to_datetime`) to unlock date-aware slicing (`df["2026-01":"2026-03"]`)
  and the `.resample()`/`.rolling()` methods.
- **`resample("D").sum()`**: regroups by a fixed time frequency (e.g. daily)
  regardless of how irregular the original timestamps are — conceptually a
  groupby where the key is "which time bucket does this row fall into,"
  filling in buckets with no data as needed (`NaN` or configurable fill).
- **`rolling(window=7).mean()`**: a moving window over the *existing* rows
  (by count or, with a time-based window like `"7D"`, by elapsed time) —
  distinct from `resample`, which changes the row granularity itself;
  `rolling` computes over a sliding view of the current granularity.
- **Timezones**: `tz_localize` attaches a timezone to naive timestamps;
  `tz_convert` converts between timezones on already-aware timestamps —
  a very common source of silent bugs is comparing/joining a
  timezone-naive column against a timezone-aware one, which raises
  (or, worse in older pandas versions, silently mishandles the comparison).

## Worked example: this repo's fraud-detection pipeline

`projects/fraud-detection-xgboost/src/fraud_detection/data.py` and
`features.py` show a small, realistic pandas pipeline end to end:

```python
# data.py -- load and establish invariants the rest of the pipeline relies on
df = pd.read_csv(RAW_DATA_PATH, parse_dates=["timestamp"])
df = df.sort_values("timestamp").reset_index(drop=True)
```

`parse_dates` does the `to_datetime` conversion inline during the CSV
read rather than as a separate pass — one less full-column pass over the
data. Sorting once here, rather than trusting every downstream caller to
re-sort, is what makes the split below correct without every caller
having to remember the invariant themselves.

```python
# features.py -- drop leakage/ID columns, split features from label
drop_cols = [c for c in (*ID_COLUMNS, *LEAKAGE_COLUMNS, TIMESTAMP_COLUMN, TARGET_COLUMN) if c in df.columns]
X = df.drop(columns=drop_cols)
y = df[TARGET_COLUMN]

# chronological split by position -- NOT sklearn's random train_test_split,
# because a random split would leak future rows into training
split_idx = int(len(df) * train_frac)
train_df, test_df = df.iloc[:split_idx].copy(), df.iloc[split_idx:].copy()
```

The `.copy()` here is deliberate: `iloc` slicing can return a view, and
the caller goes on to mutate `train_df`/`test_df` independently later in
the pipeline — an explicit copy avoids a `SettingWithCopyWarning` and, more
importantly, avoids two supposedly-independent splits silently sharing
memory with the original `df`.

Full files:
[`data.py`](../../../projects/fraud-detection-xgboost/src/fraud_detection/data.py),
[`features.py`](../../../projects/fraud-detection-xgboost/src/fraud_detection/features.py).

## Reading large files efficiently

- **`chunksize`**: `pd.read_csv(path, chunksize=100_000)` returns an
  iterator of DataFrames instead of loading the whole file at once —
  process-and-discard each chunk when the full file doesn't fit in memory
  but a full distributed engine ([Spark](../spark/README.md)/Dask) is
  more machinery than the job needs.
- **`usecols`**: read only the columns actually needed — avoids parsing
  (and allocating memory for) columns that will just be dropped
  immediately after load.
- **`dtype`**: pass an explicit dtype dict to `read_csv` to skip pandas'
  type-inference pass and avoid an accidental `object`/mixed-type column
  from ambiguous values.
- **Parquet over CSV**: `pd.read_parquet` reads a columnar, typed,
  compressed binary format — no parsing cost, reads only the requested
  columns off disk, and preserves dtypes exactly (no re-inference needed)
  — the standard interchange format between pandas and
  [Spark](../spark/README.md) for exactly this reason.

## Common gotchas

- **Chained assignment** (`df[df.x > 0]["y"] = 1`) may silently no-op
  instead of raising — always assign through `.loc` in one step
  (`df.loc[df.x > 0, "y"] = 1`) instead of chaining two indexing
  operations.
- **In-place ops return `None`**: `df.dropna(inplace=True)` mutates `df`
  and returns `None` — `df = df.dropna(inplace=True)` silently sets `df`
  to `None`. Prefer the non-`inplace` form (`df = df.dropna()`) — it's not
  meaningfully slower in most cases and removes this whole class of bug.
- **Integer column silently becomes float**: a plain `int64` column with
  no missing values that later gets a `NaN` introduced (e.g. via a
  `reindex` or an outer merge) is silently upcast to `float64`, since
  numpy's `int64` has no representation for missing values — use a
  nullable `Int64` dtype upfront if a column is logically an integer but
  might end up with missing values.
- **Index alignment surprises**: arithmetic between two Series with
  different (or duplicate, or differently-ordered) indexes aligns by
  label, producing `NaN` for any label that doesn't match on both sides
  — often not what's intended when the actual goal was positional
  alignment. Reset or explicitly align (`.reset_index(drop=True)`,
  `.align()`) when index equality isn't guaranteed.

## Relationship to other tools in this repo

- **[XGBoost](../xgboost/README.md)**: `XGBClassifier.fit()` accepts a
  pandas DataFrame directly — `build_feature_matrix()` in this repo's
  fraud-detection pipeline produces exactly the `(X, y)` pandas pair
  XGBoost's sklearn API expects, with no separate conversion step.
- **[Spark](../spark/README.md)**: `.toPandas()` on a Spark DataFrame
  pulls the *entire* distributed result onto the driver as a single
  in-memory pandas DataFrame — used deliberately in this repo's Evidently
  monitoring example once a Spark query has already reduced the data down
  to something that fits on one machine, not as a general escape hatch
  from Spark for large data.
