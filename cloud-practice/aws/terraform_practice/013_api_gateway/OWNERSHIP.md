# Who owns what: API Gateway between DevOps and developers

Your doubt: "As a DevOps engineer I can create the API Gateway, but I shouldn't be responsible for creating routes and wiring them to Lambdas." That instinct is correct and is how most organisations split it. This document spells out the split and how to make it work in practice. *(verified)* means checked in this lab (`terraform validate`, local handler runs); everything else is general practice, so adapt it to your organisation.

## 1. The mental model

- **Platform / DevOps builds the road**: the API, its stage, security, logging, limits, domain, and the paved path (module) for putting something on it.
- **Developers decide what travels on it**: which URLs exist (routes), what code answers them (Lambdas), and how that code is configured.

Routes are the **public contract of the application** (`GET /orders/{id}`), a product decision that changes with every feature. If DevOps had to create every route, DevOps would become a ticket queue and a release bottleneck. If developers could change the API itself (auth, logging, throttling, domain), a shared security boundary would have no owner.

## 2. Ownership table

| Item | Owner | Why |
|---|---|---|
| API Gateway (the `aws_apigatewayv2_api`) | **Platform** | Shared, long-lived, security-relevant |
| Stage, `auto_deploy` | **Platform** | Controls how changes go live |
| Access logging, log retention | **Platform** | Organisation-wide standard |
| Default throttling, quotas | **Platform** | Protects backends and cost |
| CORS policy | **Platform** (teams may request exceptions) | Browser security policy |
| Custom domain, certificate, WAF, base-path mappings | **Platform** | Edge security, DNS |
| Authorizers (JWT/Cognito/Lambda authorizer) | **Platform defines**, route says which to use | Central identity; consistent auth |
| Published contract (SSM parameters: `api_id`, `execution_arn`) | **Platform** | The stable interface for teams |
| The reusable module `lambda_route` | **Platform writes**, developers use | Bakes in standards once |
| **Routes** (`GET /hello`, `POST /orders`) | **Developer** | Application API contract |
| **Integration + invoke permission** (Lambda <-> route wiring) | **Hidden in the module**; developer never writes it | Boilerplate, easy to get wrong |
| **Lambda code** | **Developer** | Business logic |
| Lambda settings (memory, timeout, env vars) | **Developer** (within module limits) | Tuned to the code |
| Lambda's own IAM permissions (e.g. read a DynamoDB table) | **Developer requests, platform guards** (review or permission boundary) | Least privilege without blocking |
| Resources the service itself needs (its queue, table) | **Developer** (own stack) | Belong to the service |
| Alarms/dashboards for the API as a whole | **Platform** | Shared health view |
| Alarms for one service | **Developer** | They know what "bad" looks like |

Rule of thumb: **shared and security-relevant -> platform; specific to one feature -> developer.**

## 3. How this lab implements the split

```
platform/             one Terraform root, one state, one pipeline, changes rarely
modules/lambda_route/ platform-maintained module (use a git tag/registry in real life)
services/             developer Terraform root, own state, own pipeline, changes often
```

1. **Shared API**: the platform stack creates the API and stage (no routes, no Lambdas).
2. **A published contract**: the platform writes `api_id` and `execution_arn` to SSM Parameter Store. The services stack reads them (`data "aws_ssm_parameter"`); no shared state, no copy-pasted IDs, and the platform can restructure internals without breaking teams as long as these names keep their meaning.
3. **Auto-deploy**: the `$default` stage has `auto_deploy = true`, so a route added by a service is live automatically; the platform does not redeploy. *(HTTP API behaviour. With the older REST API (v1) you must create an explicit deployment, usually with a `triggers` hash, which couples teams to a shared deploy step and is one reason HTTP APIs suit this model better.)*
4. **A paved-road module**: one block per route creates the Lambda, its own IAM role, log group, integration, route and a permission scoped to that exact route. *(verified: validates, and the handlers behave correctly on sample events; not applied.)*
5. **Separate state and pipelines**: a developer's `apply` can never modify the API, and a platform change never touches a service's functions.

Developer experience for a new endpoint: add `src/<name>/handler.py`, add a 6-line `module` block, open a PR. No platform ticket.

## 4. Guardrails: how the platform stays safe without being a bottleneck

Giving developers freedom to add routes is only safe with guardrails:

- **The module enforces standards**: runtime, arm64, log retention, one role per function, permission scoped to a single route, tags, a `route_key` validation (`^(GET|POST|...) /`).
- **Permission boundary / SCPs** on roles developers create, so a function can't grant itself admin rights.
- **Policy as code** in CI (OPA/Conftest, Sentinel, Checkov): e.g. fail a plan that opens `lambda:*` on `*`, or adds a route without an authorizer where one is mandatory.
- **CODEOWNERS / branch rules**: developers own `services/**`; platform must review `platform/**` and `modules/**`.
- **Naming and path prefixes per team** (`/orders/*` for the orders team) so two teams can't both claim `GET /items` (API Gateway rejects duplicate route keys within one API, and the collision shows up at apply time).
- **Throttling, auth and logging live at the platform level**, so even a buggy service can't remove them.
- **Version the module** (git tag or registry) and have services pin it, so a platform change doesn't silently alter every service on the next apply.

## 5. Other ways to divide it (and the trade-offs)

| Model | How | Pros | Cons |
|---|---|---|---|
| **A. Shared API + module (this lab)** | Platform owns API; teams add routes via module | Self-service, one domain, shared standards | Shared blast radius for API-level settings; requires platform discipline |
| **B. One API per team/service** | Each team stacks its own API Gateway (platform provides a module for the whole API) | Cleanest ownership; no route collisions | More APIs and domains; cross-service consistency is up to the module (can map several APIs to one custom domain with base paths) |
| **C. Single OpenAPI file** | Platform owns the API; routes are defined in one OpenAPI spec that developers edit by PR | One reviewed document of the whole API | Merge conflicts, single deploy step, spec and Lambda wiring (`x-amazon-apigateway-integration`) are verbose |
| **D. Routes as data (`routes.yaml`)** | Platform module reads a YAML list of routes and creates integrations; devs edit only YAML | Very simple for developers | Less flexible; module must anticipate every option |
| **E. DevOps owns everything** | Platform creates API, routes and Lambdas | Tight control | Bottleneck; DevOps must understand every feature; slow releases (what you want to avoid) |

For most teams that already have a platform function, **A or B** is the right starting point.

## 6. Where code deploys fit

The same two models as in lesson 011 apply inside the `services` stack:

- **Model 1**: `terraform apply` rebuilds and redeploys the Lambda when `src/` changes (what this lab does; the module uses `archive_file` and `source_code_hash`).
- **Model 2**: Terraform creates the function once (with `ignore_changes` on the code hash), and CI ships new zips with `update-function-code`.

See `../011_lambda_sqs/DEPLOYMENT_GUIDE.md` (sections 2-4) and `../012_step_functions/STEP_FUNCTIONS_GUIDE.md` (sections 9-10, "which pipeline" and "which repo").

### Which pipeline for which change

| Change | Who / which pipeline |
|---|---|
| New or changed route | Developer: **services** pipeline |
| Lambda code | Developer: **code** pipeline (Model 2) or **services** apply (Model 1) |
| Lambda memory/timeout/env | Developer: **services** pipeline |
| API stage, logging, throttling, CORS, domain, authorizer | Platform: **platform** pipeline |
| Module change (new standard) | Platform: release a new module version, then services bump the version |

## 7. Things that surprise developers (platform should document them)

- Platform-level **throttling** applies to every route.
- **CORS** is set once at the API.
- HTTP API integrations time out at about 30 seconds *(general knowledge; verify)* regardless of the Lambda timeout.
- A route returning **500** right after creation usually means a missing/incorrect invoke permission (the module handles it).
- **Route keys must be unique per API**: `GET /orders` can only exist once.
- If the platform stack is destroyed or replaced, services break; hence the stable SSM contract and the destroy order in the README.

## 8. Follow-up lessons

1. Add a JWT authorizer in the platform stack and let a route opt in via a module variable (`authorizer_id`).
2. Add a custom domain + certificate + base-path mappings (platform), `/orders` mapped to the orders team's API (model B).
3. Add policy-as-code (Checkov or OPA) to fail a plan that breaks the guardrails.
4. Split the services stack into two teams with separate state and path prefixes, and cause a deliberate route collision to see the error.
5. Compare with the REST API (v1) and its required deployment resource.
