# Playbook: Schema Drift in Upstream Sources

## What schema drift looks like here
A pipeline log reporting a missing or unexpected column count against a source table --
e.g. "column 'customer_segment' not found, expected 14 columns, found 13." This means an
upstream team changed a table's schema without coordinating with the pipeline that reads it.

## Why retrying doesn't help
The pipeline's code expects a fixed schema. Until either the source schema reverts or the
pipeline's extraction code is updated to match the new schema, every retry fails identically --
there is no transient element to a schema mismatch. Treat any "retry" recommendation for a
schema-drift failure as a bug in the diagnosis, not a valid remediation.

## What actually resolves it
1. Roll back the pipeline to its last known-good config only if the pipeline's *own* deployed
   version changed recently and might have a bad extraction query -- this is a pipeline-side fix
   and only applies when the pipeline itself is the regression.
2. If the *source* schema changed (the common case), no automated action in this project's
   toolset fixes it -- escalate to the upstream data-owning team with the exact column diff from
   the failure logs. This is a genuine human-in-the-loop case, not a gap in tooling to route
   around.
3. Downstream models reading features derived from the affected table (see the model cards) will
   show degraded quality until the schema is reconciled -- flag this cascading risk in the
   incident ticket even if the immediate fix is "escalated, awaiting upstream team."
