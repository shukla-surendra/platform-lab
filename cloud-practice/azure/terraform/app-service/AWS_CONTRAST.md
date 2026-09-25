# Azure App Service vs. AWS: A Contrast Doc for People Moving from AWS

AWS has no single service that matches App Service. Its features are
spread across **Elastic Beanstalk** (code-to-running-app PaaS), **App
Runner** (container/source to HTTPS URL), and, if you build it yourself,
**ECS/Fargate + ALB**. App Service is closest to Beanstalk in *what it
does* and closest to App Runner in *how little you manage*. The biggest
structural difference is the **Plan**. AWS has no resource like it.

## 1. Service mapping

| Need | Azure | AWS |
|---|---|---|
| Push code, platform picks runtime & runs it | App Service (code deploy) | Elastic Beanstalk, App Runner (source) |
| Push a container, get an HTTPS URL | App Service (container), Container Apps | App Runner, ECS Fargate + ALB |
| Event-driven, scale-to-zero functions | Azure Functions (runs *on* App Service infra) | Lambda |
| Serverless containers w/ scale-to-zero, KEDA | Azure Container Apps | App Runner (partial), ECS + custom scaling |
| Static SPA + API | Static Web Apps | Amplify Hosting, S3 + CloudFront |
| Kubernetes | AKS | EKS |
| Single-tenant, in-your-VNet PaaS | App Service Environment (ASE v3) | No direct equivalent (Beanstalk in your VPC is closest) |

## 2. The Plan: the resource AWS doesn't have

**Azure**: `azurerm_service_plan` is a pool of VMs you pay for. Apps are
*placed onto* it, and many apps can share one plan's instances.
Scaling, pricing tier, OS, and region all belong to the plan, not the app.

**Elastic Beanstalk**: each *environment* gets its own EC2 Auto Scaling
Group and load balancer. There's no built-in way to pack three apps onto
one environment's instances. You'd run three environments and pay for
three sets of instances (plus three ALBs).

**App Runner**: each *service* scales independently and bills per vCPU/GB
of its own instances. There's no shared pool.

What this means in practice:

- **Density is cheap on Azure.** This lab's three apps on one B1 cost the
  same as one app. The AWS equivalent is 3 Beanstalk environments (3× EC2 + 3× ALB),
  or 3 App Runner services each with provisioned memory.
- **Noisy neighbours are your problem on Azure.** Apps on a plan share CPU
  and RAM, and they scale out together. On AWS, isolation is the default.
- **Moving an app between plans** (e.g. B1 → a dedicated P1v3) means
  changing `service_plan_id`. The app's hostname, settings, and identity
  stay the same.

## 3. Deployment model

| | App Service | Elastic Beanstalk | App Runner |
|---|---|---|---|
| Artifact | Zip (source) or container image | Zip "source bundle" in S3, or Docker | Image in ECR, or GitHub source |
| Build on platform | **Oryx** (`SCM_DO_BUILD_DURING_DEPLOYMENT`) | Platform hooks (`.ebextensions`, `.platform/`) | Managed build from source (limited runtimes) |
| Deploy endpoint | Kudu `/api/zipdeploy`, `az webapp deploy`, GitHub Actions | `eb deploy`, CodePipeline | Auto-deploy on ECR push / git push |
| Start command | Auto-detected, override `app_command_line` | `Procfile` | Configured start command |
| Config → env vars | `app_settings` | Environment properties | Environment variables / Secrets Manager refs |
| Secrets | Key Vault references in app settings (`@Microsoft.KeyVault(...)`) | SSM/Secrets Manager via instance role | Native Secrets Manager / SSM references |

## 4. Blue/green: slots vs. environment swap

| | App Service slots | Beanstalk |
|---|---|---|
| Mechanism | Extra live site on the **same plan VMs**. Swap = routing flip | Two full environments. "Swap environment URLs" = **DNS CNAME swap** |
| Speed | Seconds, no DNS propagation | Depends on DNS TTL, and clients may cache the old IP |
| Extra cost | None (shares the plan), but needs Standard+ tier | A second full environment (instances + LB) |
| Config that stays put | `sticky_settings` (slot settings) | Each environment keeps its own config naturally |
| Rolling / canary | Traffic % routing to a slot (`az webapp traffic-routing`) | Rolling, rolling w/ batch, immutable, traffic-splitting deploy policies |

App Runner has no slots or blue/green. Each deploy is a rolling
replacement with automatic rollback if health checks fail.

## 5. Scaling

| | App Service | Beanstalk | App Runner |
|---|---|---|---|
| Unit | Plan instances (all apps on the plan) | EC2 instances in the env's ASG | Container instances per service |
| Autoscale | Standard+: rules on CPU/memory/queue/schedule, or **automatic scaling** (Premium v3, HTTP-driven) | ASG policies (CPU, network, custom CloudWatch metric) | Concurrency-based (requests per instance), automatic |
| Scale to zero | ❌ (min 1 instance, billed. Use Functions/Container Apps for zero) | ❌ | ❌ billed for memory when idle, but vCPU is paused |
| Max instances | 3 (Basic), 10 (Standard), 30 (Premium), 100+ (ASE) | ASG limit | 25 default (raisable) |
| Vertical scale | Change plan SKU. Instances restart in place | Change instance type. Rolling replace | Change vCPU/memory per service |

## 6. Networking

| | App Service | AWS |
|---|---|---|
| Default ingress | Public multi-tenant front end, `*.azurewebsites.net`, TLS included | Beanstalk: your ALB in your VPC. App Runner: public `*.awsapprunner.com` |
| Private ingress | **Private Endpoint** on the app (disables public access) | Beanstalk: internal ALB. App Runner: VPC Ingress Connection (PrivateLink) |
| Egress into private network | **Regional VNet Integration** (delegated subnet) | Beanstalk: already in your VPC. App Runner: VPC Connector |
| IP allow-lists | `site_config.ip_restriction` (+ separate rules for the SCM site) | Security groups / WAF |
| Fully isolated | ASE v3 inside your VNet | Beanstalk in private subnets |

The key mental shift: **a Beanstalk app lives in your VPC by default, and an
App Service app does not.** It runs on Microsoft's multi-tenant front end, and
you bolt VNet connectivity on in each direction separately (Private Endpoint
for inbound, VNet Integration for outbound).

## 7. Identity

| | App Service | AWS |
|---|---|---|
| Workload identity | System- or user-assigned **Managed Identity** (Entra ID) | **Instance profile** (Beanstalk) / **instance role** (App Runner) |
| Granting access | RBAC role assignment on the *target* resource's scope | IAM policy attached to the *role* |
| Pull private images | Managed identity + `AcrPull` role | ECR access role (App Runner) / instance profile |
| In code | `DefaultAzureCredential()` | Default credential provider chain |

The same "direction" difference applies as in Functions vs. Lambda. AWS
attaches permissions *to the caller's role*. Azure assigns roles *on the
target resource* to the caller's identity.

## 8. Observability & ops access

| | App Service | AWS |
|---|---|---|
| Logs | `az webapp log tail`, filesystem/blob logs, Diagnostic Settings → Log Analytics | CloudWatch Logs (Beanstalk log streaming, App Runner automatic) |
| APM | Application Insights (auto-instrumentation for .NET/Java/Node/Python) | X-Ray, CloudWatch Application Signals |
| Shell into instance | `az webapp ssh`, Kudu console | Beanstalk: SSH/SSM Session Manager to EC2. App Runner: none |
| Built-in diagnostics | "Diagnose and solve problems" blade | Beanstalk enhanced health |

## 9. Cost model at a glance

| | App Service | Beanstalk | App Runner |
|---|---|---|---|
| Service fee | None. You pay for the plan | None. You pay for EC2 + ALB + … | Per vCPU-sec active + GB-sec provisioned |
| Idle cost | Full plan price | Full EC2 + ALB | Memory only |
| Load balancer | Included | ALB billed separately (~US$16+/month) | Included |
| TLS cert | Free managed cert for custom domains | ACM (free) on ALB | Included |
| Cheapest always-on option | B1 (~US$13/month Linux) | t4g.nano/micro + ALB | ~0.5 GB memory idle charge |

For small, always-on apps, App Service is usually cheaper than Beanstalk
because the load balancer is included and several apps can share one plan.
For spiky, mostly idle traffic, App Runner (or Azure Container Apps) wins.

## 10. Terraform resource mapping

| This module | Elastic Beanstalk equivalent | App Runner equivalent |
|---|---|---|
| `azurerm_service_plan` | (none. Instance type/ASG lives on the environment) | `aws_apprunner_auto_scaling_configuration_version` (loosely) |
| `azurerm_linux_web_app` (code) | `aws_elastic_beanstalk_application` + `_application_version` + `_environment` + S3 object | `aws_apprunner_service` (source code config) |
| `azurerm_linux_web_app` (container) | `aws_elastic_beanstalk_environment` (Docker platform) | `aws_apprunner_service` (image repository) |
| `azurerm_linux_web_app_slot` | Second `aws_elastic_beanstalk_environment` + CNAME swap | none |
| `app_settings` | `setting { namespace = "aws:elasticbeanstalk:application:environment" }` | `runtime_environment_variables` |
| `identity { SystemAssigned }` | `aws_iam_instance_profile` + role | `instance_configuration.instance_role_arn` |
| `health_check_path` | `aws:elasticbeanstalk:application` → `Application Healthcheck URL` | `health_check_configuration` |

## TL;DR for AWS people

- Think of **Plan = your pool of EC2 instances**, and **Web App = one
  Beanstalk environment that doesn't own its own instances**.
- Load balancer, TLS, and hostname come built in. You never create an ALB.
- It isn't in your VNet by default. Add Private Endpoint (inbound) and VNet
  Integration (outbound) when you need private networking.
- Slots give you blue/green in seconds via a routing flip, not a DNS CNAME swap.
- Scale-to-zero isn't available here. For that, use Functions (Consumption) or Container Apps.
