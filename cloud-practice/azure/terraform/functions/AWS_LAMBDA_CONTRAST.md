# Azure Functions vs. AWS Lambda — A Contrast Doc for People Moving from AWS

Both are "serverless compute, run my code on an event." The similarity
mostly stops at that one sentence — the two platforms made different
architectural bets underneath, and most of the "why does Azure make me
configure X" questions trace back to one root cause: **AWS built Lambda
as its own distinct service; Azure built Functions as a layer on top of
its existing App Service (Web App) hosting platform.** Almost every
difference below is a consequence of that one decision.

## 1. Why Azure makes you pick a "Plan" at all

**Lambda**: no equivalent resource exists. Memory (128MB–10GB, CPU scales
with it) and timeout (up to 15 minutes, hard cap) are properties directly
on the function resource. AWS's control plane handles the entire
multi-tenant scheduling/scaling fabric invisibly — there's nothing to
provision besides the function itself.

**Azure Functions**: every Function App is still, underneath, an App
Service "site" (`Microsoft.Web/sites` — the exact resource type Web Apps
use) and every site must reference a **Service Plan**
(`azurerm_service_plan`, `Microsoft.Web/serverFarms`). The Plan is what
actually carries the scaling/billing model:

| Plan SKU | Behavior | Nearest Lambda analog |
|---|---|---|
| `Y1` (Consumption) | Scales to zero, bills per-execution + GB-seconds, ~1M free executions/month | Plain Lambda, on-demand |
| `EP1`/`EP2`/`EP3` (Elastic Premium) | Pre-warmed instances (no cold start), still elastic, VNet integration | Lambda + Provisioned Concurrency |
| `B1`/`S1`/`P1v2`... (Dedicated/App Service) | Always-on reserved VM(s), billed continuously regardless of traffic | Nothing in Lambda — closer to "run your handler on a normal EC2/ECS box yourself" |

The payoff for this extra resource: you can move a Function App between
these three completely different cost/scaling models by changing only
`service_plan_id` — the Function App resource, its code, its identity,
its RBAC role assignments, all untouched. Lambda has no equivalent
"swap the whole execution model without touching the function" move.

## 2. Identity and permissions: one bundle vs. two separate resources

**Lambda**: one **execution role** (an IAM Role) does both jobs at once —
it's what the function assumes to run *and* what carries the attached
policies granting it access to other AWS resources (S3, DynamoDB, etc).

**Azure Functions**: split into two independent resource types.
`identity { type = "SystemAssigned" }` on the Function App is purely
*who it authenticates as* (Azure auto-manages a service principal, no
permissions implied). A separate `azurerm_role_assignment` binds a Role
Definition to that identity at a chosen scope — *what it can do*. An
identity can exist with zero role assignments (able to do nothing at
all); the same Role Definition can be assigned to five different
identities independently. See
[`../function-storage-rbac/README.md`](../function-storage-rbac/README.md)
for the full IAM-policy-document → Azure-Role-Definition translation,
built and verified against a real least-privilege Function + Storage
setup (including the live `403 AuthorizationPermissionMismatch` proof).

## 3. Triggers: event source mappings vs. Triggers *and* Bindings

**Lambda**: you configure an **event source mapping** (or direct
invoke via API Gateway, EventBridge, etc.) that decides *when* your
handler runs. Reading/writing other resources inside the handler is
always your own SDK code (`boto3.client("s3").get_object(...)`).

**Azure Functions**: a **Trigger** plays the same "when does this run"
role (HTTP, Blob, Queue, Timer, Event Grid, Cosmos DB, Service Bus...).
But Functions adds a second concept Lambda has no equivalent for:
**Bindings** — declarative input/output wiring that hands your function
already-materialized data (or a ready-to-write output slot) without you
writing any SDK/client code at all, e.g. an `@app.blob_input` /
`@app.blob_output` decorator that just gives your function a string/bytes
parameter, backed by a container path, no `BlobServiceClient` in sight.
This repo's `function-storage-rbac` demo deliberately does *not* use
Bindings — it calls the Blob SDK directly with `DefaultAzureCredential()`
specifically so the RBAC boundary (which container, which role) stays
fully visible in the code rather than hidden inside binding configuration.

## 4. Packaging and deployment

**Lambda**: upload a zip or push a container image directly to the
Lambda service via the API/CLI/console. No separate "hosting platform"
step — the deployment package *is* the unit Lambda runs.

**Azure Functions (Linux Consumption, Python)**: more moving parts, and
one of them bit hard building `function-storage-rbac/`. The default mode
is **"Run From Package"** — `WEBSITE_RUN_FROM_PACKAGE` gets set to a SAS
URL pointing at an immutable zip in a storage account, and the app runs
directly from that mounted, read-only package. Crucially, **that mode has
no remote build step** — `SCM_DO_BUILD_DURING_DEPLOYMENT=true` (which
would normally trigger an Oryx `pip install` on the server) is silently
ignored in Run-From-Package mode. Deployed a zip with just
`function_app.py` + `requirements.txt`, the CLI reported success, and
every route 404'd with **zero functions ever registered** — the Python
worker failed to import undeployed dependencies with no error surfaced
anywhere. The fix: vendor dependencies *inside* the zip yourself
(`pip install --target=.python_packages/lib/site-packages ...`, matching
what `func azure functionapp publish` does automatically) — see the full
walkthrough in
[`../function-storage-rbac/README.md`](../function-storage-rbac/README.md#deploying-the-function-code).
Lambda's zip-upload model has no equivalent failure mode because there's
no separate "build vs. run from package" distinction to get wrong.

## 5. Local tooling

**Lambda**: AWS SAM CLI (or plain `aws lambda` CLI commands) for
build/package/deploy/local-invoke.

**Azure Functions**: **Azure Functions Core Tools** (`func`) is the
equivalent — `func init`, `func new`, `func azure functionapp publish`.
Notably absent from this machine while building these modules, which is
*why* every deployment in this repo's Function modules goes through raw
`az functionapp deployment source config-zip` / the Kudu zipdeploy API
directly instead of the smoother `func publish` path — a real
demonstration that the CLI/API layer underneath `func` is fully usable
on its own, just with more of the packaging steps (see §4) on you
manually.

## 6. Scaling and concurrency

**Lambda**: one concurrency model — each concurrent invocation gets its
own execution environment; **Reserved Concurrency** caps how many a
function can use, **Provisioned Concurrency** keeps N warm at all times
to eliminate cold starts, both are properties of the function itself.

**Azure Functions Consumption plan**: a **Scale Controller** decides how
many host instances to run based on event rate (queue length, HTTP load,
etc.) — conceptually similar goal, different mechanism, and scale-out
granularity/limits vary by trigger type. Cold starts are a real, named
concern on Consumption specifically (idle app scales to zero, so the
first request after idle pays a startup cost) — Premium (`EP*`) plans
exist specifically to keep instances pre-warmed, the closer analog to
Lambda's Provisioned Concurrency, but as a property of the *Plan*, not
the function.

## 7. Execution limits, side by side

| | AWS Lambda | Azure Functions (Consumption) | Azure Functions (Premium/Dedicated) |
|---|---|---|---|
| Max timeout | 15 minutes (hard cap) | 5 min default, up to 10 min configurable | No hard cap |
| Memory | 128 MB – 10 GB, dialed directly, CPU scales with it | Fixed ~1.5 GB per instance | Chosen via Plan SKU (more headroom) |
| Scale to zero | N/A (always effectively "zero" between invocations, billed per-ms) | Yes, native | No (Premium keeps warm instances; Dedicated is always-on) |

## Where this repo's other Azure modules fit in

- [`functions/`](.) (this module) — the plain, empty Function App +
  Consumption Plan, no code deployed.
- [`function-storage-rbac/`](../function-storage-rbac/) — a real,
  deployed, working Function doing actual blob I/O under least-privilege
  custom RBAC roles; the deep dive on §2 and the §4 deployment gotcha
  above, both proven live against a real Azure subscription.
