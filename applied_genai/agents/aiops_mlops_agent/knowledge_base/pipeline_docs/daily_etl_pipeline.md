# Pipeline: pl-daily-etl

## What it does
Extracts transaction and event data from operational stores and loads it into
`warehouse.sales_fact` and `warehouse.raw_events`. Runs nightly. Every downstream pipeline
(`pl-feature-refresh`, and by extension every model card in this knowledge base) reads from
tables this pipeline populates -- a `pl-daily-etl` failure is upstream of everything else.

## Freshness SLA
`warehouse.raw_events` must be no more than 24 hours stale. `pl-feature-refresh` checks this SLA
at the start of its own run and fails fast (rather than running on stale data) if it's violated --
that's the "freshness SLA" failure category in the pipeline-failure runbook, and it always traces
back to a `pl-daily-etl` problem even though the *error* surfaces in `pl-feature-refresh`.

## Failure blast radius
A `pl-daily-etl` failure doesn't fail loudly downstream right away -- `pl-feature-refresh` only
starts failing once the 24h SLA is actually breached, which can be hours after the ETL failure
itself. When triaging a `pl-feature-refresh` freshness failure, always check `pl-daily-etl`'s own
status and logs, not just re-run the feature refresh -- retrying the feature refresh before the
ETL is fixed just fails again on the same stale source data.
