# Backfill: running a DAG for past dates

CLI options and API routes below were checked against the Airflow 3.0.6 source. UI wording was
not checked and may differ slightly between 3.0.x versions.

## 1. What it is

A **backfill** runs a scheduled DAG for a range of **past data intervals**.

> "Run this daily DAG for every day from Jan 1 to Jan 10."

Typical reasons:

- You deployed a new DAG and want its history loaded.
- You fixed a bug in a transformation and need to re-process old days.
- A source system was down or late and some days were missed or are wrong.
- You added a new column or metric and need it for old partitions.

## 2. Backfill is an Airflow feature, not a UI feature

The UI button is only one way to start it. Airflow itself does the work.

```
UI button ─┐
CLI       ─┼──> Backfill API/service ──> creates one DagRun per interval ──> scheduler runs them
REST API  ─┘          (a row in the `backfill` table tracks progress)
```

What **Airflow** does when you request a backfill:

1. Reads the DAG's schedule and lists every interval between `from_date` and `to_date`.
2. Creates one DAG run per interval, each with its own `logical_date`, `data_interval_start`
   and `data_interval_end`.
3. Lets the scheduler run those runs like any other, respecting `max_active_runs`, pools,
   concurrency limits, retries and trigger rules.
4. Records the backfill as its own object, so you can see progress, pause it, or cancel it.

What **your DAG code** must do: produce the correct result *for the interval it was given*. Airflow
only creates the runs. It does not know whether your tasks handle old dates correctly. See section 5.

## 3. Prerequisite: the DAG needs a schedule

A backfill walks the schedule's intervals, so there must be a schedule.

| DAG | Backfill possible? |
|---|---|
| `schedule="@daily"` (`02`, `04`, `05`) | Yes |
| `schedule=None` (`01`, `03`) | No: no intervals to enumerate. That is why the option is greyed out. |

## 4. How to run one

### UI
Open the DAG, use the trigger menu, choose the backfill option, pick the date range and the
reprocess behavior.

### CLI
```bash
docker compose exec airflow-scheduler airflow backfill create \
  --dag-id 04_backfill_demo \
  --from-date 2026-01-01 --to-date 2026-01-05 \
  --reprocess-behavior none \
  --max-active-runs 2 \
  --dry-run
```

Remove `--dry-run` to run it for real. Always start with a dry run: it lists the runs that *would*
be created without creating them.

| Option | Meaning |
|---|---|
| `--from-date`, `--to-date` | Range of logical dates to backfill (inclusive). |
| `--reprocess-behavior` | What to do when a run already exists for a date. See section 6. |
| `--max-active-runs` | How many of this backfill's runs execute at once. |
| `--run-backwards` | Newest date first. Not allowed if any task has `depends_on_past=True`. |
| `--dag-run-conf` | JSON passed to each run as `dag_run.conf`. |
| `--dry-run` | Show what would happen; create nothing. |

### REST API (for CI or other systems)

| Method and path | Purpose |
|---|---|
| `POST /api/v2/backfills` | Create a backfill. |
| `POST /api/v2/backfills/dry_run` | Preview what a backfill would create. |
| `GET /api/v2/backfills` and `GET /api/v2/backfills/{id}` | List and inspect. |
| `PUT /api/v2/backfills/{id}/pause` and `/unpause` | Stop or resume creating new runs. |
| `PUT /api/v2/backfills/{id}/cancel` | Cancel it. |

## 5. What your code must do to be backfill-safe

A backfill re-executes your tasks with old dates. Three rules make the result correct.

### Rule 1: derive the date from the run, never from "now"

```python
# WRONG: a backfill of Jan 3 still processes today's data
today = datetime.now()

# RIGHT: uses the interval this run was created for
@task
def extract(data_interval_start=None, data_interval_end=None):
    ...
```

The same applies to SQL: filter on the interval, not on `CURRENT_DATE`. In templates use
`{{ data_interval_start }}`, `{{ data_interval_end }}` or `{{ ds }}`.

### Rule 2: be idempotent

Running the same interval twice must give the same final state, with no duplicates.

| Pattern | Idempotent? |
|---|---|
| Overwrite a partition (`dt=2026-01-03`) | Yes |
| `MERGE` / upsert on a key | Yes |
| Delete the interval's rows, then insert | Yes (do both in one transaction) |
| Blind `INSERT` / append to a file | **No**: a repeated backfill duplicates data |
| Non-deterministic output (random, "latest" lookups) | **No** |

`04_backfill_demo.py` overwrites `dt=<day>.txt`, so backfilling a range twice still leaves one
file per day.

### Rule 3: be safe to run in parallel

Several intervals may run at the same time (`max_active_runs`). Runs must not share one output
file, one staging table, or one lock. Partition outputs by interval.

Also consider:

- **`depends_on_past=True`** makes each day wait for the previous day. It is safe but forces
  serial execution and blocks `--run-backwards`.
- **Late-arriving or changing source data:** re-running an old day may give different results
  than the original run. Decide whether that is correct or whether you need snapshots.
- **Side effects:** a backfill that sends emails, Slack messages or API writes will do it for every
  past day. Guard those tasks or skip them during backfills.
- **Load on the source system:** 365 days at once can overwhelm a database. Limit with
  `--max-active-runs` or a pool.

## 6. Reprocess behavior

Controls what happens when a run already exists for a date in the range.

| Value | Behavior |
|---|---|
| `none` (default) | Skip dates that already have a run. Only creates runs for missing dates. |
| `failed` | Also re-run dates whose existing run failed. |
| `completed` | Re-run every date in the range, even ones that already succeeded. |

Use `completed` after fixing a bug that affected successful runs too.

## 7. Backfill vs `catchup` vs clearing

| | Trigger | Range | Typical use |
|---|---|---|---|
| `catchup=True` | Automatic when the DAG is unpaused | Everything since `start_date` | New DAG that should load full history |
| Backfill | Manual, on demand | A range you choose, works with `catchup=False` | Re-process or fill a specific period |
| Clear task instances | Manual, in the UI | Existing runs only | Re-run a failed or wrong run that already exists |

`catchup=True` with an old `start_date` is a common production surprise: unpausing launches
hundreds of runs. Keep `catchup=False` and use a controlled backfill instead.

## 8. Lab: try it

1. Start the stack (see README) and unpause `04_backfill_demo`. `catchup=False`, so one run appears.
2. Dry run:
   ```bash
   docker compose exec airflow-scheduler airflow backfill create \
     --dag-id 04_backfill_demo --from-date 2026-01-01 --to-date 2026-01-05 --dry-run
   ```
3. Run it without `--dry-run`. Watch five runs appear in the Grid view.
4. `ls logs/backfill_demo/`. One file per day.
5. Run the same backfill again with `--reprocess-behavior completed`. Still one file per day:
   that is idempotency.
6. Break it on purpose: change `write_text` in `04_backfill_demo.py` to append (open the file with
   mode `"a"`). Backfill twice with `completed` and see duplicated lines.
7. Try `--max-active-runs 1` vs `3` and compare how the runs overlap in the Grid view.

## 9. Interview questions

**What is a backfill, and how is it different from `catchup`?**
Running a scheduled DAG for past intervals. `catchup` does it automatically on unpause for
everything since `start_date`. A backfill is manual, targets a range you choose, and works even
with `catchup=False`.

**Why can't you backfill a DAG with `schedule=None`?**
No schedule means no intervals to create runs for.

**Is backfill handled by the UI or the code?**
By Airflow's backfill service. The UI, CLI and REST API all call it. Your DAG code only needs to
be correct for any interval it receives.

**What makes a DAG safe to backfill?**
Use the run's data interval instead of `now()`, write idempotently (overwrite or upsert), and
avoid shared outputs between parallel runs.

**What goes wrong if tasks append data and you backfill twice?**
Duplicate rows. Re-running is only safe if tasks are idempotent.

**How do you limit the load of a large backfill?**
`--max-active-runs`, pools, and `max_active_tasks` on the DAG.

**What does `depends_on_past` change for backfills?**
Each interval waits for the previous one to succeed, so runs are serial, and `--run-backwards` is
rejected.

**How do you re-run only the failed days?**
Backfill with `--reprocess-behavior failed`, or clear the failed task instances.
