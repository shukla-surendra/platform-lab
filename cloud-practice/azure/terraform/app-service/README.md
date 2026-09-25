# Terraform: Azure App Service (three app types, one plan)

One Linux **App Service Plan** (B1) hosting three Web Apps that cover the
three ways you actually put something on App Service:

| App | Type | What runs it | Code |
|---|---|---|---|
| `app-py-xxxxxx` | Code deploy, Python 3.12 | Flask + gunicorn, built by Oryx | [`apps/python-flask`](apps/python-flask) |
| `app-node-xxxxxx` | Code deploy, Node 22 LTS | Express, built by Oryx | [`apps/node-express`](apps/node-express) |
| `app-ctr-xxxxxx` | Container | Public image `nginxdemos/hello` from Docker Hub | none: the image *is* the app |

The code apps are zipped by the `archive` provider and pushed with
`zip_deploy_file`, so a single `terraform apply` gives you working URLs.
There's also an optional **staging deployment slot** on the Python app
(`enable_staging_slot = true`, needs Standard tier or above).

Coming from AWS? [`AWS_CONTRAST.md`](AWS_CONTRAST.md) maps App Service
onto Elastic Beanstalk / App Runner / ECS and explains where the models
differ.

> ⚠️ **This creates billable resources.** A B1 Linux plan bills per hour
> whether or not anything calls the apps (~US$13/month in Central India;
> check the pricing page for current numbers). All three apps share that one
> plan, so they cost the same as one app would. Switching to `S1` for slots
> costs roughly 5× as much. Run `terraform destroy` when done.

---

## What App Service is

App Service is Azure's managed **PaaS for HTTP workloads**: web apps, REST
APIs, mobile backends. You hand it code or a container image. Azure runs
the VMs, OS patching, load balancer, TLS termination, and scaling, and
gives you `https://<name>.azurewebsites.net`.

### The two resources you always create

```
azurerm_service_plan  (Microsoft.Web/serverFarms)   ← the COMPUTE: VM size × instance count, OS, price
        ▲   ▲   ▲
        │   │   └── azurerm_linux_web_app "container"   ← the APPS (Microsoft.Web/sites):
        │   └────── azurerm_linux_web_app "node"            hostname, runtime, settings, identity
        └────────── azurerm_linux_web_app "python"
```

- **Plan** = a pool of identical VMs. `sku_name` picks the size and the
  feature set, `worker_count` picks how many VMs. You pay for the plan.
- **App (site)** = one deployable thing with its own hostname, settings, and
  identity. Each app on a plan runs on **every** instance of that plan.
  Three apps on a 2-instance plan means 6 processes on 2 VMs, and they compete
  for the same CPU and RAM.
- Scaling out is a plan property, so all apps on the plan scale together.
  Give a noisy app its own plan.
- A plan's OS is fixed: Linux and Windows apps can't share one.

### Deployment models

| Model | You provide | Azure owns | Used here |
|---|---|---|---|
| **Code** (built-in stack) | Source code + `requirements.txt` / `package.json` / `.csproj` | OS, runtime (Python, Node, .NET, Java, PHP), patching | Python, Node |
| **Container** | A Docker image (Docker Hub, ACR, any registry) | Host OS only | nginx container |
| **Multi-container** (Compose) | *Retired*, so use sidecars or Container Apps instead | n/a | n/a |

**What happens during a code deploy.** `zip_deploy_file` POSTs the zip to
the app's **Kudu/SCM site** (`<app>.scm.azurewebsites.net/api/zipdeploy`).
Because `SCM_DO_BUILD_DURING_DEPLOYMENT=true` is set, Kudu runs **Oryx**,
which:

1. Detects the language (`requirements.txt` means Python, `package.json` means Node).
2. Installs dependencies *on the Linux image* (pip into a venv, or `npm install`).
3. Works out the start command: `gunicorn app:app` for a Flask `app.py`, or
   `npm start` for Node. You can override it with `site_config.app_command_line`.

That's why the zips hold only source code, with no `node_modules` or `.venv`.

[`HOW_ZIP_DEPLOY_WORKS.md`](HOW_ZIP_DEPLOY_WORKS.md) walks through the
whole path: the Kudu and app containers, the shared `/home` disk, the Oryx
build, how the start command is chosen, and Run From Package.

### SKU tiers (Linux)

| Tier | SKUs | Notable features |
|---|---|---|
| Free / Shared | F1 | Shared compute, 60 CPU-min/day, no Always On, no custom TLS. Toy use only |
| Basic | B1–B3 | Dedicated VMs, Always On, custom domains + TLS, manual scale (up to 3 instances) |
| Standard | S1–S3 | + **deployment slots** (5), **autoscale** (up to 10), daily backups |
| Premium v3 | P0v3–P5mv3 | + faster hardware, 20 slots, up to 30 instances, zone redundancy |
| Isolated v2 | I1v2+ | Runs in your own App Service Environment (ASE) inside your VNet. Single-tenant |

### Features this module turns on, and why

| Setting | Why |
|---|---|
| `https_only = true` | Plain HTTP gets a 301 redirect to HTTPS |
| `minimum_tls_version = "1.2"`, `ftps_state = "Disabled"` | Baseline hardening. FTP publishing is legacy, so use zip deploy or CI |
| `always_on` | Without it, an idle app unloads after about 20 minutes and the next request pays a cold start |
| `health_check_path = "/health"` | The front end pings every instance. After repeated failures an instance leaves the rotation and is later replaced |
| `app_settings` | Show up as **environment variables**. Changing one restarts the app |
| `sticky_settings` | Settings that stay with the *slot* during a swap (e.g. which DB it points at) |
| `identity { SystemAssigned }` | Free Entra ID identity for secret-less access to Key Vault, Storage, and SQL. See [`../function-storage-rbac`](../function-storage-rbac) |
| `logs {}` | App stdout and HTTP logs on the local filesystem. Stream them with `az webapp log tail` |
| `WEBSITES_PORT` (container) | Which port *inside* the container receives traffic |

### Deployment slots (blue/green)

A slot is a separate live site (`<app>-staging.azurewebsites.net`) with
its own settings, running on the **same plan VMs**. The workflow:

1. Deploy the new version to `staging`.
2. Hit it and warm it up. The platform also warms it before a swap.
3. `az webapp deployment slot swap` flips routing between the slots. It
   takes seconds with no dropped requests. To roll back, swap again.

Settings in `sticky_settings` **stay** in their slot. Everything else moves
with the code.

---

## Usage

```bash
terraform init
terraform apply                     # creates infra AND deploys both code apps
```

Test all three apps:

```bash
curl -s $(terraform output -raw python_url) | jq
curl -s $(terraform output -raw node_url)   | jq
curl -s $(terraform output -raw container_url) | head -20
```

`terraform apply` returns once Kudu reports the build succeeded, but the
app then recycles. For a few minutes you may still see Azure's
placeholder page ("Hey, Python developers!" / "waiting for your content").
Retry until JSON comes back.

The Python and Node responses show the **same `instance`** value even
though `host` (the container) differs. That's the plan model in action:
both apps are containers on the one B1 VM.

### Redeploy after changing code

Edit anything under `apps/` and run `terraform apply` again. The zip file
name contains a hash of the source, so Terraform detects the change and
redeploys. (With a fixed zip path, azurerm would never notice that the
contents changed.)

Outside Terraform, which is what CI would do:

```bash
cd apps/python-flask && zip -r ../../build/py.zip . && cd ../..
az webapp deploy -g rg-appservice-demo -n $(terraform output -raw python_app_name) \
  --src-path build/py.zip --type zip
```

### Try slots

```bash
terraform apply -var sku_name=S1 -var enable_staging_slot=true
curl -s $(terraform output -raw python_staging_url) | jq .message   # "hello from the staging slot"

az webapp deployment slot swap -g rg-appservice-demo \
  -n $(terraform output -raw python_app_name) --slot staging --target-slot production
curl -s $(terraform output -raw python_url) | jq .message           # still "production": GREETING is sticky
```

### Operate

```bash
APP=$(terraform output -raw python_app_name)
az webapp log tail -g rg-appservice-demo -n $APP             # live stdout/stderr
az webapp ssh      -g rg-appservice-demo -n $APP             # shell into the running container
az webapp config appsettings list -g rg-appservice-demo -n $APP -o table
az appservice plan update -g rg-appservice-demo -n asp-appservice-demo --number-of-workers 2   # scale out
```

The Kudu console at `https://<app>.scm.azurewebsites.net` shows deployment
history, the Oryx build log, env vars, and a file browser.

## Troubleshooting

| Symptom | Likely cause |
|---|---|
| "Application Error" page / 503 right after deploy | Container still starting, or the app crashed at boot. Check `az webapp log tail` |
| Node app starts but times out | App listens on a hard-coded port instead of `process.env.PORT` |
| `ModuleNotFoundError` in Python | `SCM_DO_BUILD_DURING_DEPLOYMENT` missing, so Oryx never ran pip |
| Container app 503 | `WEBSITES_PORT` doesn't match the port the image `EXPOSE`s / listens on |
| Placeholder page right after a successful deploy | App is still recycling onto the new build. Wait a few minutes |
| Code edits not deployed | Zip path didn't change. This module avoids that with a content hash |
| `Conflict` / slot error on apply | Slots on B1. Use S1+ |

## What's deliberately not here

No Application Insights, no VNet integration or private endpoints, no
custom domain or managed certificate, no autoscale rules, no ACR (a public
image keeps it self-contained), no Windows/.NET app (it would need a second
plan, because the OS is per-plan), and no CI pipeline.

## Teardown

```bash
terraform destroy
```
