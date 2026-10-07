# Handling new and dynamic source data in ADF

## The core idea

ADF does **not** remember which files it has already processed.

- A **dataset** only describes *shape and location* (container, file name, format). It holds no state.
- A **pipeline run** does what it is told: copy the file it is given.
- In this tutorial, nothing tracks processed vs unprocessed. Run `pl_copy_file` twice with `orders.csv` and the second run just overwrites `processed/orders.csv`.

So "how are new files handled" is a design you build **around** the pipeline. There are two separate questions:

1. **Discovery**: how does the pipeline learn that new data exists? (trigger, listing, time window)
2. **Tracking**: how do you know what is done? (move/delete, time window state, watermark, control table)

## Making the dataset dynamic (prerequisite)

Do not create one dataset per file. Parameterize it, as this tutorial does:

```
trigger / caller ──▶ pipeline parameter ──▶ dataset parameter ──▶ file path
                     @pipeline().parameters.fileName      @dataset().fileName
```

Parameterize whichever parts change: `fileName`, `folderPath`, `container`, even the linked service (for many storage accounts). One dataset then serves any file.

Useful expressions:

| Need | Expression |
|---|---|
| Pipeline parameter | `@pipeline().parameters.fileName` |
| File that fired a blob event trigger | `@triggerBody().fileName`, `@triggerBody().folderPath` |
| Tumbling window start / end | `@trigger().outputs.windowStartTime`, `@trigger().outputs.windowEndTime` |
| Date-partitioned folder | `@formatDateTime(utcnow(),'yyyy/MM/dd')` |
| Item inside a ForEach | `@item().name` |

## Patterns

### 1. Storage event trigger (new file arrives, pipeline runs)
- A **blob created** trigger fires once per new blob and passes the file name into the pipeline parameter.
- Best fit when files arrive irregularly and should be processed promptly.
- Needs the `Microsoft.EventGrid` resource provider registered. In Terraform: `azurerm_data_factory_trigger_blob_event`.
- Events are delivered at-least-once, and in rare cases can be missed. Make the pipeline idempotent and keep a catch-up path (pattern 3 or 5) for important data.

### 2. Move or delete after a successful copy
- `raw/` = unprocessed. After Copy succeeds, a **Delete** activity removes the source (or a second Copy moves it to `archive/`).
- Copy's "delete source files after completion" option does the same in one step.
- State lives in the folder layout, so it is easy to see and debug.
- The Delete/move activity must have `dependsOn` Copy with condition `Succeeded`. A failed file then stays in `raw/` and is retried next run.
- Trade-off: you lose the original in `raw/` unless you archive it. Prefer archive over delete.

### 3. Tumbling window + modified-time filter
- A **tumbling window trigger** runs for fixed, contiguous, non-overlapping windows (for example every hour) and keeps per-window state: Succeeded, Failed, Waiting.
- The Copy source filters with `modifiedDatetimeStart = @trigger().outputs.windowStartTime` and `modifiedDatetimeEnd = @trigger().outputs.windowEndTime`.
- Gives you backfill (set a past start date), retry of a single failed window, and exactly-one-run-per-window semantics.
- Weakness: relies on blob last-modified time. Late-arriving files whose timestamp falls in an already-processed window are missed. Add a delay on the trigger to allow for lateness.

### 4. Get Metadata + ForEach
- `Get Metadata` (childItems) lists the files in a folder, `ForEach` loops over them and runs Copy per file (`@item().name`).
- Combine with a filter against what is already done (pattern 5) to copy only new files.
- Set `ForEach` to parallel with a sensible `batchCount`. Note the limits: ForEach runs 50 items by default in parallel (max 50), and Get Metadata/Lookup outputs are capped (about 4 MB / 5,000 rows for Lookup). Very large listings need paging or a different approach.

### 5. Watermark / control table (the standard incremental load)
- Keep a small state store: a SQL table (or a blob) with `last_processed_time` per source, or one row per file with status.
- Each run: **Lookup** the watermark, copy rows/files newer than it, then update the watermark only **after** the copy succeeds.
- Per-file variant (audit trail): table with `file_name`, `status`, `run_id`, `started`, `finished`, `rows_copied`, `error`. Insert a row at start, update on success or failure. Retrying failures is then a query: `WHERE status = 'Failed'`.
- Best for database sources (use a `modified_at` or an incrementing ID column) and for any case where you need an audit trail.

### 6. Change-based features (where the source supports it)
- **Change Data Capture / incremental in Mapping Data Flows** and the **Copy Data tool's** incremental options track changes for you on supported sources.
- Use these instead of building your own watermark when the source is supported.

## Choosing a pattern

| Situation | Use |
|---|---|
| Files land at random times, want near-real-time | Event trigger (1), plus a catch-up |
| Files land on a schedule, need backfill/retry per period | Tumbling window (3) |
| Simple landing folder, no need to keep originals in place | Move/archive after copy (2) |
| Need an audit trail, retries, per-file status | Control table (5), usually with Get Metadata + ForEach (4) |
| Database table source | Watermark (5) or CDC (6) |

Combining is normal. A common robust setup: **event trigger + archive after copy + control table logging**.

## Best practices

1. **Make every pipeline idempotent.** A rerun for the same file/window must give the same result. Overwrite the target or upsert. Never blindly append.
2. **Update state last.** Move, delete, or advance the watermark only after the data is safely written (`dependsOn` ... `Succeeded`).
3. **Never process a file still being written.** Upload under a temp name and rename, write a `.done` marker file, or add a short delay. Event triggers can fire before the upload completes for large files.
4. **Archive, don't delete.** Keep originals in `archive/` (with a lifecycle rule to expire them) so you can reprocess.
5. **Quarantine bad files.** On failure, move the file to an `error/` folder, log the reason, and continue with the others. One bad file should not block the batch.
6. **Parameterize, don't duplicate.** One generic dataset + pipeline driven by parameters, rather than a copy per file or table. For many sources, drive a ForEach from a config table (a metadata-driven pipeline).
7. **Use managed identity.** No keys in linked services (as this tutorial does). Grant the factory identity only the roles it needs.
8. **Keep state outside the factory.** Watermarks and logs in a SQL table or blob survive redeploys. Pipeline variables do not persist between runs.
9. **Handle schema drift deliberately.** For CSVs that change, enable schema drift in Mapping Data Flows or map columns explicitly. Decide whether a new column should fail or be tolerated.
10. **Monitor and alert.** Use Monitor > Pipeline runs and set Azure Monitor alerts on failed runs. Track rows copied to spot silent empty loads.
11. **Control concurrency.** Set the pipeline's `concurrency` and ForEach `batchCount` so an event burst does not overwhelm the source or sink.
12. **Test with backfill and rerun.** Before trusting a design, rerun the same file, run two files at once, and kill a run halfway to check you end in a consistent state.

## Applying this to the tutorial

The current pipeline takes `fileName` as a parameter and has one Copy activity. A natural extension (README step 7):

1. Add `azurerm_data_factory_trigger_blob_event` on the `raw` container, passing `@triggerBody().fileName` into `fileName`.
2. Add a second activity (Delete, or a Copy to `archive/`) in `activities_json` with `dependsOn` `CopyRawToProcessed` = `Succeeded`.
3. Optionally log each run to a control table or blob.

Remember: edits made in the studio are not saved to Terraform and get reverted on the next `terraform apply`. Put the changes in `main.tf`.
