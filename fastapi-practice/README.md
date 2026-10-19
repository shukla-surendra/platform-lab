# FastAPI Practice

FastAPI notebooks written for interview prep: markdown explanations paired
with runnable code, covering the topics that come up most often — core
routing/validation, Pydantic schemas, dependency injection and
middleware, async/concurrency, data-engineering-flavored API patterns
(ingestion, pagination, streaming, batch scoring), and testing plus
classic coding problems.

**Like `../pandas_practice/`, these notebooks are executed** — FastAPI
has no JVM/cluster setup, so `pip install fastapi uvicorn httpx pydantic`
was enough to actually run every cell. Every endpoint is exercised with
`fastapi.testclient.TestClient` (the same tool FastAPI apps are unit
tested with), so responses, status codes, and validation errors in the
notebooks are real output, not typed-out guesses. Notebook 04 goes a step
further and spins up a real `uvicorn` server on localhost to measure the
actual latency difference a blocking call makes under concurrent load.
All six notebooks ran end-to-end with zero errors and zero warnings.

## Setup (to re-run these)

```bash
cd fastapi_practice
uv venv .venv && uv pip install --python .venv/bin/python fastapi uvicorn httpx pydantic python-multipart jupyter ipykernel nbconvert
source .venv/bin/activate
jupyter notebook notebooks/
# or re-execute all of them headlessly:
jupyter nbconvert --to notebook --execute --inplace notebooks/*.ipynb
```

## Layout

```
fastapi_practice/
  notebooks/
    01_fastapi_core_concepts.ipynb                  <- ASGI vs WSGI, path/query/body params, response_model, TestClient, /docs
    02_pydantic_validation_and_serialization.ipynb  <- Field constraints, custom validators, nested models, extra="forbid", aliasing
    03_dependency_injection_and_middleware.ipynb    <- Depends(), auth deps, yield-based cleanup, sub-dependencies, middleware, exception handlers
    04_async_and_concurrency.ipynb                  <- async def vs def, the blocking-call footgun (measured against a live uvicorn server), asyncio.gather
    05_data_engineering_patterns_with_fastapi.ipynb <- file upload ingestion, offset vs cursor pagination, StreamingResponse, BackgroundTasks, batch scoring
    06_testing_and_interview_problems.ipynb         <- dependency_overrides, in-memory CRUD, HMAC-verified idempotent webhooks, simple rate limiting
  .venv/    <- local venv (fastapi, uvicorn, httpx, jupyter) used to write and execute these notebooks
```

Each notebook ends with an interview Q&A section and a one-line pointer to
the next topic — read them in order the first time through, then use them
as a quick-reference the day before an interview.

## Related: `../pandas_practice/` and `../spark_practice/`

Those two cover the data-processing side of a pipeline (transformations,
joins, aggregations); this project covers the API layer that often sits
in front of or behind one — ingestion endpoints for landing raw data,
pagination/streaming for exporting large results, and batch-prediction
serving for a trained model.
