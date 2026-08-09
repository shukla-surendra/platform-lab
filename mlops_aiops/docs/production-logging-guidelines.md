# Production Logging Guidelines

Companion to the observability docs in this folder: `observability-terminology.md` and
`observability-on-eks.md` cover the *pipeline* logs travel through (Loki/ELK, shipping,
Grafana); `observability-instrumentation-tradeoffs.md` covers *who's responsible* for
producing telemetry. This doc is about the *content* of the logs themselves — which level
to use, what fields to include, and the anti-patterns that make logs expensive or useless
regardless of which backend stores them.

## 1. Purpose

This document defines a practical production logging standard for
backend services, microservices, ML/AI systems, data pipelines, and
Kubernetes workloads.

The goal is to make production systems:

-   Observable without generating unnecessary log volume
-   Easy to investigate during incidents
-   Searchable and machine-readable
-   Safe with respect to secrets and sensitive data
-   Consistent across services and teams
-   Cost-effective at scale

The central principle is:

> **Production should be diagnosable with normal operational logs. DEBUG
> should provide additional detail, not be the only source of useful
> information.**

------------------------------------------------------------------------

# 2. Logging Levels

## 2.1 ERROR

### Purpose

Use `ERROR` when an operation failed or the service entered a state that
requires investigation or intervention.

An ERROR should answer:

1.  What failed?
2.  Which operation failed?
3.  Which resource/request was affected?
4.  What was the error?
5.  Was the operation retried?
6.  Did the system recover or ultimately fail?

### Include

Recommended fields:

-   `timestamp`
-   `severity`
-   `service`
-   `environment`
-   `service_version`
-   `operation`
-   `request_id`
-   `trace_id`
-   `resource_id`
-   `error_code`
-   `error_type`
-   `retry_count`
-   `duration_ms`
-   `dependency`
-   `status`

### Example

``` text
ERROR OCR processing failed
service=doc-extractor
operation=document_processing
document_id=12345
request_id=abc123
model_version=ocr-v2
error_code=OCR_TIMEOUT
retry_count=3
duration_ms=8210
status=failed
```

### Avoid

Do not generate an ERROR for:

-   Expected validation failures
-   Normal retries
-   User input errors that are handled normally
-   Every occurrence of a known transient event if it is automatically
    recovered

For high-volume failures, consider metrics and aggregation rather than
producing massive duplicate logs.

------------------------------------------------------------------------

# 3. WARN

## Purpose

Use `WARN` when something unexpected happened but the system can
continue, recover, retry, or degrade gracefully.

A WARN should answer:

> **What unusual condition occurred, and what did the system do about
> it?**

### Include

-   Operation
-   Resource/request identifier
-   Unexpected condition
-   Relevant threshold/value
-   Recovery action
-   Retry information
-   Dependency
-   Impact if useful

### Example

``` text
WARN OCR request timed out; retrying
service=doc-extractor
operation=ocr_request
document_id=12345
attempt=2
max_attempts=3
timeout_ms=5000
action=retry
```

Another example:

``` text
WARN Regional endpoint unavailable; using global endpoint
service=doc-extractor
operation=openai_request
region=eu
fallback_region=global
request_id=abc123
```

### Avoid

Do not use WARN for normal expected behavior.

If something happens thousands of times per hour and is part of normal
operation, it probably should be represented as a metric rather than a
WARN log.

------------------------------------------------------------------------

# 4. INFO

## Purpose

INFO is the most important level for normal production operations.

INFO should record significant lifecycle events and business/system
events, not every line of execution.

A useful question is:

> **Would an operator care that this event happened?**

If the answer is no, it probably should not be INFO.

### Good INFO events

Examples:

``` text
INFO service_started
INFO service_ready
INFO message_received
INFO document_processing_started
INFO document_processing_completed
INFO batch_processing_completed
INFO deployment_version_loaded
INFO configuration_loaded
INFO external_dependency_connected
```

### Example

``` text
INFO document processing completed
service=doc-extractor
operation=document_processing
document_id=12345
pages=18
duration_ms=8210
status=success
model_version=ocr-v2
```

### Avoid

Avoid logging every internal step:

``` text
INFO Downloading page 1
INFO Downloading page 2
INFO Downloading page 3
INFO Running OCR
INFO OCR completed
INFO Running rotation
INFO Rotation completed
INFO Uploading result
```

At scale this becomes extremely expensive and noisy.

Instead, prefer a summary:

``` text
INFO document processing completed
document_id=12345
pages=18
ocr_duration_ms=4200
rotation_duration_ms=1100
total_duration_ms=8210
status=success
```

------------------------------------------------------------------------

# 5. DEBUG

## Purpose

DEBUG is for detailed troubleshooting and developer investigation.

It may contain information that is useful when understanding why a
particular execution path occurred.

### Examples

``` text
DEBUG OCR request constructed
document_id=12345
batch_size=18
preprocessing_options=deskew,rotation
model_version=ocr-v2
```

``` text
DEBUG Selecting fallback endpoint
region=eu
primary_endpoint=regional
fallback_endpoint=global
reason=regional_request_failed
```

### DEBUG can contain

-   Internal decisions
-   Detailed state transitions
-   Dependency request/response metadata
-   Configuration decisions
-   Intermediate processing information
-   Detailed retry information
-   Diagnostic values

### But DEBUG should still respect security rules

DEBUG is not permission to log secrets or sensitive data.

Never log:

-   Passwords
-   API keys
-   Access tokens
-   Private keys
-   Authorization headers
-   Session tokens
-   Sensitive customer information
-   Full documents
-   Full OCR text unless explicitly approved
-   Payment information

------------------------------------------------------------------------

# 6. TRACE

TRACE is extremely fine-grained diagnostic logging.

It can describe:

-   Function-level execution
-   Very detailed state transitions
-   Low-level algorithm decisions
-   Detailed request lifecycle
-   Internal component interactions

Example:

``` text
TRACE entering normalize_coordinates
TRACE coordinate transformation applied
TRACE exiting normalize_coordinates
```

TRACE is normally disabled in production and should be used only when
there is a strong diagnostic need.

------------------------------------------------------------------------

# 7. What Should Be Logged at Each Level?

  ----------------------------------------------------------------------------------------------------------------------
  Information                  ERROR                 WARN                 INFO                DEBUG                TRACE
  ------------- -------------------- -------------------- -------------------- -------------------- --------------------
  Operation                      Yes            Sometimes                   No                  Yes                  Yes
  failed                                                                                            

  Significant              Sometimes            Sometimes                  Yes                  Yes                  Yes
  lifecycle                                                                                         
  event                                                                                             

  Retry                 If exhausted                  Yes           Usually no                  Yes                  Yes

  Internal                 Sometimes            Sometimes           Usually no                  Yes                  Yes
  decision                                                                                          

  Function                        No                   No                   No            Sometimes                  Yes
  entry/exit                                                                                        

  Performance                    Yes                  Yes                  Yes                  Yes                  Yes
  summary                                                                                           

  Full request                    No                   No           Usually no                Avoid                Avoid
  payload                                                                                           

  Secrets                      Never                Never                Never                Never                Never

  Sensitive                  Only if              Only if              Only if              Only if              Only if
  data            justified/redacted   justified/redacted   justified/redacted   justified/redacted   justified/redacted
  ----------------------------------------------------------------------------------------------------------------------

------------------------------------------------------------------------

# 8. Production Does Not Mean DEBUG Must Be Permanently Disabled

A common misconception is:

> "DEBUG is disabled in production, therefore we cannot debug
> production."

That is not the desired architecture.

A production system should be sufficiently observable using:

1.  Metrics
2.  INFO/WARN/ERROR logs
3.  Distributed traces
4.  Correlation IDs
5.  Health checks
6.  Dashboards
7.  Alerting

DEBUG can then be enabled temporarily when additional detail is
required.

Conceptually:

``` text
Normal operation
      |
      +--> Metrics
      +--> INFO
      +--> WARN
      +--> ERROR
      +--> Traces
      |
Incident
      |
      +--> Enable DEBUG selectively
      |
Investigation
      |
      +--> Fix
      |
      +--> Disable DEBUG
```

------------------------------------------------------------------------

# 9. Prefer Selective DEBUG

Do not turn every production instance into DEBUG if the service is
processing millions of requests.

Bad approach:

``` text
100 pods
   |
   +--> DEBUG enabled everywhere
```

Better:

``` text
100 pods
   |
   +--> 99 pods: INFO
   |
   +--> 1 pod: DEBUG
```

Even better, where the architecture supports it:

``` text
request_id=abc123
        |
        +--> detailed diagnostic logging
```

This dramatically reduces log volume while preserving diagnostic
capability.

------------------------------------------------------------------------

# 10. Structured Logging

Production logs should preferably be structured rather than free-form
text.

### Avoid

``` text
Document 12345 failed while processing OCR after 8.2 seconds
```

### Prefer

``` json
{
  "severity": "ERROR",
  "service": "doc-extractor",
  "operation": "document_processing",
  "document_id": "12345",
  "error_code": "OCR_TIMEOUT",
  "duration_ms": 8210,
  "status": "failed"
}
```

Structured logs allow log systems to:

-   Search fields
-   Aggregate errors
-   Filter by service
-   Group by error code
-   Calculate statistics
-   Correlate requests
-   Build dashboards
-   Create alerts

------------------------------------------------------------------------

# 11. Standard Context Fields

A useful baseline for production services is:

``` text
timestamp
severity
service
environment
service_version
host
pod
namespace
request_id
trace_id
operation
resource_id
status
duration_ms
error_code
```

Not every log needs every field, but services should have a consistent
schema.

For Kubernetes:

``` text
service=doc-extractor
environment=production
namespace=extraction
pod=doc-extractor-7d98f8
service_version=1.8.8
```

------------------------------------------------------------------------

# 12. Correlation IDs

Correlation IDs are one of the most valuable pieces of production
observability.

A request may travel through:

``` text
API
 |
 +--> SQS
       |
       +--> Preprocessor
              |
              +--> OCR
                     |
                     +--> Extractor
                            |
                            +--> Database
```

Use a consistent identifier:

``` text
request_id=abc123
```

or preferably a distributed tracing identifier:

``` text
trace_id=abc123
```

Then an incident can be investigated across services.

Example:

``` text
API
request_id=abc123

SQS
request_id=abc123

Preprocessor
request_id=abc123

OCR
request_id=abc123

Extractor
request_id=abc123
```

This is much more useful than searching through unrelated log lines.

------------------------------------------------------------------------

# 13. Logging Performance

Logging itself consumes:

-   CPU
-   Memory
-   Disk
-   Network bandwidth
-   Storage
-   Log ingestion capacity
-   Search/indexing resources

Therefore:

> **Logging is production traffic. Treat it as a system resource.**

For example, if one request produces:

``` text
50 log lines
```

and the system handles:

``` text
1,000,000 requests/day
```

that can produce:

``` text
50,000,000 log events/day
```

Even if each event is small, the aggregate cost and search noise can
become significant.

------------------------------------------------------------------------

# 14. Avoid Logging Inside High-Volume Loops

### Poor approach

``` python
for page in document.pages:
    logger.info("Processing page")
    process(page)
    logger.info("Page processed")
```

For a 100-page document, that is already 200 log events.

### Better approach

``` python
for page in document.pages:
    process(page)

logger.info(
    "document_processing_completed",
    extra={
        "pages": len(document.pages),
        "duration_ms": duration_ms,
    },
)
```

Use DEBUG if individual page-level diagnostics are actually needed.

------------------------------------------------------------------------

# 15. Batch Processing

For batch systems, avoid logging every item at INFO.

### Avoid

``` text
INFO Processing message 1
INFO Processing message 2
INFO Processing message 3
...
INFO Processing message 1000
```

### Prefer

``` text
INFO batch_processing_completed
batch_size=1000
success_count=987
failure_count=13
duration_ms=147260
throughput_per_hour=2440
```

Then log individual failures at ERROR/WARN when they need investigation.

------------------------------------------------------------------------

# 16. Performance Logging

For performance-sensitive services, include timing information in
important logs.

Example:

``` text
INFO document_processing_completed
document_id=12345
pages=18
preprocess_ms=1200
ocr_ms=4200
rotation_ms=1100
extractor_ms=900
total_ms=7400
```

This makes performance regressions much easier to identify.

However, avoid logging every tiny operation unless it is genuinely
useful.

------------------------------------------------------------------------

# 17. ML/OCR Pipeline Example

For an OCR pipeline:

``` text
SQS
 |
Preprocessor
 |
OCR
 |
Extractor
 |
Postprocessor
 |
S3/Database
```

A useful logging strategy is:

### Message received

``` text
INFO message_received
message_id=abc123
document_id=12345
queue=ocr-processing
```

### Processing started

``` text
INFO document_processing_started
document_id=12345
pages=18
service_version=1.8.8
model_version=ocr-v2
```

### External service warning

``` text
WARN OCR request timeout; retrying
document_id=12345
attempt=2
timeout_ms=5000
```

### Fallback

``` text
WARN regional endpoint failed; using global endpoint
document_id=12345
region=eu
fallback=global
```

### Completion

``` text
INFO document_processing_completed
document_id=12345
pages=18
ocr_ms=4200
rotation_ms=1100
extraction_ms=900
total_ms=7400
status=success
```

### Final failure

``` text
ERROR document_processing_failed
document_id=12345
error_code=OCR_TIMEOUT
retry_count=3
duration_ms=8210
status=failed
```

------------------------------------------------------------------------

# 18. Logging vs Metrics vs Traces

Do not use logs for everything.

## Metrics answer:

> "How much / how often?"

Examples:

``` text
ocr_requests_total
ocr_failures_total
ocr_latency_seconds
documents_processed_total
queue_depth
```

## Logs answer:

> "What happened?"

Example:

``` text
OCR request failed
document_id=12345
error_code=OCR_TIMEOUT
```

## Traces answer:

> "Where did the time/failure occur?"

Example:

``` text
API             100 ms
 |
SQS              20 ms
 |
Preprocessor    300 ms
 |
OCR            7200 ms  <-- problem
 |
Extractor       200 ms
```

A mature system uses all three.

------------------------------------------------------------------------

# 19. Error Codes

Use stable error codes rather than relying only on human-readable
messages.

Example:

``` text
OCR_TIMEOUT
OCR_INVALID_RESPONSE
OCR_AUTH_FAILURE
OCR_RATE_LIMIT
S3_UPLOAD_FAILED
DATABASE_CONNECTION_FAILED
MESSAGE_DESERIALIZATION_FAILED
```

Then you can query:

``` text
error_code=OCR_TIMEOUT
```

and immediately see the scope of the problem.

Avoid changing error codes unnecessarily because dashboards and alerts
may depend on them.

------------------------------------------------------------------------

# 20. Exception and Stack Traces

For unexpected exceptions, include the exception type and stack trace
where useful.

Example:

``` text
ERROR database operation failed
operation=insert_extraction
document_id=12345
error_code=DATABASE_INSERT_FAILED
exception_type=TimeoutError
```

The stack trace should generally be attached to the error event rather
than manually printed as dozens of unrelated log messages.

Avoid logging the same exception multiple times at multiple layers.

For example, this is noisy:

``` text
ERROR database failed
ERROR repository failed
ERROR service failed
ERROR controller failed
```

Prefer a clear ownership model where the exception is logged once with
sufficient context, while upper layers add context only when it
materially helps.

------------------------------------------------------------------------

# 21. Sensitive Data

Never log secrets.

Examples of data that should not appear in logs:

``` text
Authorization: Bearer eyJ...
api_key=sk-...
password=...
private_key=...
session_token=...
```

Also be careful with:

-   Customer names
-   Email addresses
-   Phone numbers
-   Addresses
-   Identity information
-   Full documents
-   OCR text
-   Financial information
-   Authentication information

Use IDs and hashes where appropriate.

Instead of:

``` text
customer_email=user@example.com
```

consider:

``` text
customer_id=12345
```

if the email is not required for troubleshooting.

------------------------------------------------------------------------

# 22. Log Sampling

For extremely high-volume systems, log sampling can reduce cost.

For example:

``` text
Successful requests:
    log 1 out of 100

Failed requests:
    log 100%

Rare/high-value events:
    log 100%
```

The exact sampling policy depends on the system.

Do not blindly sample errors if doing so could hide important incidents.

------------------------------------------------------------------------

# 23. Log Retention

Retention should be based on:

-   Operational requirements
-   Incident investigation needs
-   Compliance requirements
-   Security policies
-   Storage cost
-   Data sensitivity

A common strategy is:

``` text
Hot logs
    |
    +--> short retention
    +--> fast search

Archived logs
    |
    +--> longer retention
    +--> cheaper storage
```

Not every log needs to remain searchable forever.

------------------------------------------------------------------------

# 24. Production Logging Anti-Patterns

## Anti-pattern 1: Logging everything at INFO

``` text
INFO function started
INFO function ended
INFO variable calculated
INFO API called
INFO response received
```

Result:

-   Huge volume
-   High cost
-   Difficult investigation
-   Important events buried in noise

------------------------------------------------------------------------

## Anti-pattern 2: DEBUG is the only useful diagnostic information

If INFO only says:

``` text
ERROR processing failed
```

while DEBUG contains all the context, production operators are
effectively blind when DEBUG is disabled.

Important operational context belongs in INFO/WARN/ERROR.

------------------------------------------------------------------------

## Anti-pattern 3: Logging entire payloads

``` text
INFO request={huge JSON payload}
INFO response={huge JSON response}
```

Problems:

-   Cost
-   Performance
-   Security
-   Privacy
-   Search noise

Log metadata and identifiers instead.

------------------------------------------------------------------------

## Anti-pattern 4: Duplicate errors

``` text
ERROR OCR failed
ERROR service failed
ERROR request failed
```

for the same underlying exception.

This can make one failure appear to be three failures.

------------------------------------------------------------------------

## Anti-pattern 5: No correlation ID

Without a request/trace identifier, distributed-system debugging becomes
much harder.

------------------------------------------------------------------------

# 25. Recommended Production Standard

A practical baseline is:

``` text
INFO
    Significant lifecycle and business events

WARN
    Unexpected but recoverable conditions

ERROR
    Failed operations requiring investigation

DEBUG
    Detailed troubleshooting information

TRACE
    Extremely detailed execution information
```

And every important event should use structured context:

``` text
service
environment
version
operation
request_id
trace_id
resource_id
status
duration_ms
error_code
```

------------------------------------------------------------------------

# 26. Incident Investigation Workflow

When an incident occurs:

### Step 1 --- Check metrics

Determine:

``` text
Is the error rate increasing?
Is latency increasing?
Which service is affected?
When did it start?
```

### Step 2 --- Check logs

Search by:

``` text
service
time range
error_code
request_id
trace_id
resource_id
```

### Step 3 --- Follow the trace

Identify where the request spent time or failed.

### Step 4 --- Check recent changes

Look at:

``` text
deployment
configuration
model version
library version
infrastructure
dependency
feature flag
```

### Step 5 --- Enable DEBUG selectively if necessary

Only after normal observability is insufficient.

### Step 6 --- Investigate

Collect detailed evidence.

### Step 7 --- Fix and restore normal logging

Disable temporary DEBUG once the investigation is complete.

------------------------------------------------------------------------

# 27. Golden Rule

The most important rule is:

> **Don't ask "How many logs should we generate?" Ask "What information
> will we need during an incident?"**

A good production system has:

``` text
                OBSERVABILITY
                     |
        +------------+------------+
        |            |            |
      Metrics       Logs        Traces
        |            |            |
      What?        What?        Where?
        |            |            |
        +------------+------------+
                     |
                Investigation
                     |
              Temporary DEBUG
                     |
                   Fix
```

The goal is not minimum logging.

The goal is:

> **Maximum diagnostic value per log event.**
