# How a Zip Ends Up Running on App Service

The zip itself never runs. It's just the delivery format. App Service
**unpacks** it, **builds** it, and runs the result inside a **container
image that Microsoft provides**. The deploy log for this module shows
each step (`az webapp log deployment show -g rg-appservice-demo -n <app>`):

```
Repository path is /tmp/zipdeploy/extracted    ← 1. zip unpacked
Running oryx build...                          ← 2. dependencies installed
Triggering recycle                             ← 3. app container restarted
Deployment successful. ... Extract zip. Remote build.
```

## The two containers behind every Linux web app

Every web app on Linux App Service is really two containers on the plan's
VM. Both share one persistent disk mounted at `/home`.

```
                    App Service Plan VM (e.g. B1)
 ┌──────────────────────────────────────────────────────────────┐
 │                                                              │
 │  ┌─────────────────────┐          ┌──────────────────────┐   │
 │  │ Kudu / SCM container│          │ App container        │   │
 │  │ <app>.scm.azure...  │          │ mcr.microsoft.com/   │   │
 │  │                     │          │ appsvc/python:3.12   │   │
 │  │ receives the zip,   │          │                      │   │
 │  │ runs Oryx build     │          │ runs gunicorn app:app│   │
 │  └─────────┬───────────┘          └──────────┬───────────┘   │
 │            │  writes                  reads  │               │
 │            ▼                                 ▼               │
 │       ┌─────────────────────────────────────────────┐        │
 │       │ /home  (persistent, network-backed storage) │        │
 │       │   └── site/wwwroot/  ← your built app       │        │
 │       └─────────────────────────────────────────────┘        │
 └──────────────────────────────────────────────────────────────┘
```

- **Kudu (the SCM site)** at `https://<app>.scm.azurewebsites.net` is a
  management container. It exists to receive deployments, run builds, and
  give you a console, file browser, and logs.
- **The app container** serves your traffic. For a code app it runs a
  standard runtime image that Microsoft maintains, chosen by
  `application_stack { python_version = "3.12" }` (or `node_version`, etc.)
  in `main.tf`. The image contains no code of its own. Your code comes
  from the `/home` mount.
- **`/home`** is persistent storage shared by both containers and by every
  instance of the plan. Anything written outside `/home` is lost when the
  container restarts.

## Step by step

### 1. Upload

`zip_deploy_file` in `main.tf` makes Terraform POST the zip to Kudu:

```
POST https://<app>.scm.azurewebsites.net/api/zipdeploy
```

`az webapp deploy --type zip`, the VS Code extension, and the GitHub
Actions `azure/webapps-deploy` action all call this same Kudu endpoint.

### 2. Unpack

Kudu extracts the zip to `/tmp/zipdeploy/extracted`.

### 3. Build with Oryx

Because `SCM_DO_BUILD_DURING_DEPLOYMENT=true` is set in `app_settings`,
Kudu runs **Oryx**, Microsoft's build tool. It works much like a
Dockerfile you never had to write:

| Oryx finds | Detects | Build step |
|---|---|---|
| `requirements.txt` | Python | Creates a virtualenv and runs `pip install -r requirements.txt` |
| `package.json` | Node | Runs `npm install` (and `npm run build` if that script exists) |
| `*.csproj` | .NET | Runs `dotnet publish` |

The build output is written to `/home/site/wwwroot`.

**Without** `SCM_DO_BUILD_DURING_DEPLOYMENT`, the files are just copied
across. Nothing is installed, so Python fails at startup with
`ModuleNotFoundError: No module named 'flask'`.

This is also why the zips in this module contain **only source code**, with
no `node_modules` or `.venv`. Dependencies are installed on the Linux
image, so native packages are compiled for the platform instead of your
laptop.

### 4. Start

Kudu restarts ("recycles") the app container. On boot, the container runs
a startup script that Oryx generated with the command it detected:

| App | Oryx detects | Start command |
|---|---|---|
| `apps/python-flask` | `app = Flask(...)` in `app.py` | `gunicorn app:app` |
| `apps/node-express` | `"start"` script in `package.json` | `npm start` → `node server.js` |

Set `site_config.app_command_line` to override the detected command
(e.g. `gunicorn --workers 4 --bind 0.0.0.0:8000 app:app`).

### 5. Serve

Azure's shared front end handles TLS for `*.azurewebsites.net`, then
forwards plain HTTP to the port in the container's `PORT` environment
variable. That's why:

- `server.js` must listen on `process.env.PORT`. A hard-coded port means
  the platform's warm-up probe never gets an answer.
- The original scheme arrives in the `X-Forwarded-Proto` header. The Node
  app echoes it back as `forwardedProto: "https"`.

`terraform apply` returns as soon as step 3 succeeds, but step 4 can take
a few more minutes on a small SKU. Until it finishes you'll still see
Azure's placeholder page ("Hey, Python developers!").

## Code app vs. container app

The container app in this module (`app-ctr-*`) skips steps 1–4 entirely.
App Service pulls the image and runs it.

| | Code app (`app-py-*`, `app-node-*`) | Container app (`app-ctr-*`) |
|---|---|---|
| Image | Microsoft's runtime image | Your image (`nginxdemos/hello`) |
| Where your code lives | `/home/site/wwwroot`, mounted in | Inside the image |
| Who builds it | Oryx, on Azure, at deploy time | You, with `docker build`, before deploy |
| Deploy artifact | Zip of source | Image tag in a registry |
| Who patches the OS and runtime | Microsoft | You (rebuild the image) |
| `/home` mount | Always | Off here (`WEBSITES_ENABLE_APP_SERVICE_STORAGE=false`) |

A "code deploy" is still a container deploy. The difference is that
Microsoft owns the image, and your code is mounted into it instead of
being built into it.

## Variant: Run From Package

The setting `WEBSITE_RUN_FROM_PACKAGE=1` turns on a different model. The zip is
**not** extracted or built. It's mounted read-only as `wwwroot`.

| | Zip deploy + Oryx (this module) | Run From Package |
|---|---|---|
| Build on server | Yes | No. The zip must already contain dependencies |
| `wwwroot` | Writable files | Read-only mount of the zip |
| Deploy is atomic | No. Files are copied over the old ones | Yes. The mount switches to the new zip |
| Typical use | Web Apps with interpreted languages | Function Apps, pre-built CI artifacts |

That's the trap the [`function-storage-rbac`](../function-storage-rbac)
module hit: Linux Consumption Function Apps default to Run From Package,
so Oryx never ran and the Python dependencies were missing.

## See it yourself

```bash
APP=$(terraform output -raw python_app_name)

# Shell into the running app container
az webapp ssh -g rg-appservice-demo -n $APP
  ls -la /home/site/wwwroot      # app.py, requirements.txt, build output
  cat /opt/startup/startup.sh    # the startup script Oryx generated
  ps aux | grep gunicorn         # the process actually serving requests
  env | grep -E 'PORT|WEBSITE_'  # platform-injected environment

# Full build log of the last deployment
az webapp log deployment show -g rg-appservice-demo -n $APP --query "[].message" -o tsv

# Live stdout/stderr of the app
az webapp log tail -g rg-appservice-demo -n $APP
```

The Kudu dashboard at `https://<app>.scm.azurewebsites.net` has the same
information in a browser: Environment, Debug console (file browser), and
Deployments.

## AWS equivalents

| Step | App Service | Elastic Beanstalk | Lambda |
|---|---|---|---|
| Artifact | Zip POSTed to Kudu | Zip "source bundle" uploaded to S3 | Zip uploaded to Lambda (or S3) |
| Build on platform | Oryx (`pip`/`npm install`) | Platform hooks run `pip`/`npm install` on the EC2 instance | None. The zip must contain dependencies (like Run From Package) |
| Where code runs | Microsoft's runtime container | EC2 instance with the runtime pre-installed | AWS's managed runtime (Firecracker micro-VM) |
| Start command | Auto-detected / `app_command_line` | `Procfile` | `handler` setting |
| Management plane | Kudu (SCM site) | EB agent on the instance | n/a |

Elastic Beanstalk is the closest match: upload a zip, the platform unpacks
it onto a machine with the runtime already installed, installs the
dependencies, and starts the process.
