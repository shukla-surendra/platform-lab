terraform {
  required_providers {
    azurerm = { source = "hashicorp/azurerm" }
    random  = { source = "hashicorp/random" }
    archive = { source = "hashicorp/archive" }
  }
}

provider "azurerm" {
  features {}
}

variable "location" {
  type    = string
  default = "Central India"
}

# B1 (Basic) is the cheapest tier with Always On and custom domains, and
# the default here. Deployment slots and autoscale need Standard (S1) or
# above -- see enable_staging_slot below.
variable "sku_name" {
  type    = string
  default = "B1"
}

# A "staging" slot on the Python app, to demo slot swap (blue/green).
# Slots are a Standard+ feature, so this only works with sku_name = "S1",
# "P0v3", "P1v3", ...
variable "enable_staging_slot" {
  type    = bool
  default = false
}

# 1. Resource Group
resource "azurerm_resource_group" "app" {
  name     = "rg-appservice-demo"
  location = var.location
}

resource "random_string" "suffix" {
  length  = 6
  special = false
  upper   = false
}

# 2. The App Service Plan -- the actual compute (Microsoft.Web/serverFarms).
# A plan is a set of VMs of one size; every app pointed at it runs on ALL
# of those VMs and shares their CPU/RAM. Billing is per plan instance, not
# per app, so the three apps below cost exactly the same as one would.
# os_type is fixed for the plan's lifetime: Linux and Windows apps can
# never share a plan.
resource "azurerm_service_plan" "app" {
  name                = "asp-appservice-demo"
  resource_group_name = azurerm_resource_group.app.name
  location            = azurerm_resource_group.app.location
  os_type             = "Linux"
  sku_name            = var.sku_name
  worker_count        = 1

  lifecycle {
    precondition {
      condition     = !var.enable_staging_slot || !contains(["F1", "B1", "B2", "B3"], var.sku_name)
      error_message = "Deployment slots need Standard tier or above (S1, P0v3, P1v3, ...). Set sku_name accordingly or disable enable_staging_slot."
    }
  }
}

locals {
  apps_dir = "${path.module}/apps"

  # Content hash of each app's source folder. It is baked into the zip
  # FILE NAME because azurerm only redeploys zip_deploy_file when the
  # path changes -- editing app.py under a fixed zip path is a silent no-op.
  python_src_hash = substr(sha1(join("", [
    for f in sort(fileset("${local.apps_dir}/python-flask", "**")) : filesha1("${local.apps_dir}/python-flask/${f}")
  ])), 0, 10)
  node_src_hash = substr(sha1(join("", [
    for f in sort(fileset("${local.apps_dir}/node-express", "**")) : filesha1("${local.apps_dir}/node-express/${f}")
  ])), 0, 10)

  # Free tier can't keep workers warm; everything else should, or the
  # app unloads after ~20 idle minutes and the next request pays a cold start.
  always_on = var.sku_name != "F1"
}

# 3. Package the source. Only source goes in the zip, never
# node_modules/.venv -- Oryx installs dependencies on the server (see
# SCM_DO_BUILD_DURING_DEPLOYMENT), so the artifact stays tiny and the
# dependencies are built for the platform's Linux image, not your laptop.
data "archive_file" "python" {
  type        = "zip"
  source_dir  = "${local.apps_dir}/python-flask"
  output_path = "${path.module}/build/python-flask-${local.python_src_hash}.zip"
  excludes    = ["__pycache__", ".venv"]
}

data "archive_file" "node" {
  type        = "zip"
  source_dir  = "${local.apps_dir}/node-express"
  output_path = "${path.module}/build/node-express-${local.node_src_hash}.zip"
  excludes    = ["node_modules"]
}

# ---------------------------------------------------------------------------
# App type 1: CODE deployment, Python (Flask)
# ---------------------------------------------------------------------------
# "Code" apps run your source on a Microsoft-maintained runtime image
# (here Python 3.12). You never write a Dockerfile; the platform patches
# the OS/runtime underneath you.
resource "azurerm_linux_web_app" "python" {
  name                = "app-py-${random_string.suffix.result}"
  resource_group_name = azurerm_resource_group.app.name
  location            = azurerm_resource_group.app.location
  service_plan_id     = azurerm_service_plan.app.id
  https_only          = true

  # Terraform pushes this zip to the Kudu /api/zipdeploy endpoint after
  # creating the app. Fine for a lab; in real life CI does deployments
  # (az webapp deploy / GitHub Actions) and Terraform only owns infra.
  zip_deploy_file = data.archive_file.python.output_path

  site_config {
    always_on           = local.always_on
    ftps_state          = "Disabled"
    http2_enabled       = true
    minimum_tls_version = "1.2"
    health_check_path   = "/health"
    # How long an instance may fail /health before it's pulled from the
    # load balancer (and eventually replaced).
    health_check_eviction_time_in_min = 5

    application_stack {
      python_version = "3.12"
    }
  }

  app_settings = {
    # Makes zip deploy run Oryx: detect Python, create a venv, pip install
    # -r requirements.txt, and generate the gunicorn start command.
    "SCM_DO_BUILD_DURING_DEPLOYMENT" = "true"
    # App settings surface to the process as ordinary env vars.
    "GREETING" = "hello from the production slot"
  }

  # Slot-sticky settings stay with the slot during a swap instead of
  # travelling with the code (e.g. "which DB am I pointed at").
  sticky_settings {
    app_setting_names = ["GREETING"]
  }

  logs {
    detailed_error_messages = true
    failed_request_tracing  = true
    application_logs {
      file_system_level = "Information"
    }
    http_logs {
      file_system {
        retention_in_days = 3
        retention_in_mb   = 35
      }
    }
  }

  # A Managed Identity costs nothing and is how the app would reach Key
  # Vault / Storage / SQL without secrets (see function-storage-rbac/).
  identity {
    type = "SystemAssigned"
  }
}

# Optional staging slot: a second, fully separate site
# (app-py-xxxx-staging.azurewebsites.net) on the SAME plan's VMs.
# Deploy there, warm it up, then `az webapp deployment slot swap` -- the
# swap is a routing flip, so it's near-instant and instantly reversible.
resource "azurerm_linux_web_app_slot" "python_staging" {
  count           = var.enable_staging_slot ? 1 : 0
  name            = "staging"
  app_service_id  = azurerm_linux_web_app.python.id
  https_only      = true
  zip_deploy_file = data.archive_file.python.output_path

  site_config {
    always_on                         = local.always_on
    ftps_state                        = "Disabled"
    health_check_path                 = "/health"
    health_check_eviction_time_in_min = 5

    application_stack {
      python_version = "3.12"
    }
  }

  app_settings = {
    "SCM_DO_BUILD_DURING_DEPLOYMENT" = "true"
    "GREETING"                       = "hello from the staging slot"
  }
}

# ---------------------------------------------------------------------------
# App type 2: CODE deployment, Node.js (Express)
# ---------------------------------------------------------------------------
# Same deploy model as the Python app, different stack: Oryx sees
# package.json, runs `npm install`, and starts the app with `npm start`.
resource "azurerm_linux_web_app" "node" {
  name                = "app-node-${random_string.suffix.result}"
  resource_group_name = azurerm_resource_group.app.name
  location            = azurerm_resource_group.app.location
  service_plan_id     = azurerm_service_plan.app.id
  https_only          = true
  zip_deploy_file     = data.archive_file.node.output_path

  site_config {
    always_on                         = local.always_on
    ftps_state                        = "Disabled"
    http2_enabled                     = true
    minimum_tls_version               = "1.2"
    health_check_path                 = "/health"
    health_check_eviction_time_in_min = 5

    application_stack {
      node_version = "22-lts"
    }
  }

  app_settings = {
    "SCM_DO_BUILD_DURING_DEPLOYMENT" = "true"
    "GREETING"                       = "hello from node"
  }

  logs {
    application_logs {
      file_system_level = "Information"
    }
    http_logs {
      file_system {
        retention_in_days = 3
        retention_in_mb   = 35
      }
    }
  }

  identity {
    type = "SystemAssigned"
  }
}

# ---------------------------------------------------------------------------
# App type 3: CONTAINER deployment (any language, your own image)
# ---------------------------------------------------------------------------
# Instead of a runtime stack, point the app at an image. App Service pulls
# it and runs it; you own everything inside the image (OS patches too).
# A public Docker Hub image keeps this self-contained -- with a private ACR
# you'd add a user-assigned identity with AcrPull and set
# container_registry_use_managed_identity = true instead of any password.
resource "azurerm_linux_web_app" "container" {
  name                = "app-ctr-${random_string.suffix.result}"
  resource_group_name = azurerm_resource_group.app.name
  location            = azurerm_resource_group.app.location
  service_plan_id     = azurerm_service_plan.app.id
  https_only          = true

  site_config {
    always_on           = local.always_on
    ftps_state          = "Disabled"
    http2_enabled       = true
    minimum_tls_version = "1.2"

    application_stack {
      docker_image_name   = "nginxdemos/hello:latest"
      docker_registry_url = "https://index.docker.io"
    }
  }

  app_settings = {
    # Which port INSIDE the container to forward traffic to. App Service
    # guesses 80/8080 otherwise; set it explicitly for anything else.
    "WEBSITES_PORT" = "80"
    # Containers are stateless by default here: don't mount the shared
    # /home storage that code apps get.
    "WEBSITES_ENABLE_APP_SERVICE_STORAGE" = "false"
  }

  logs {
    http_logs {
      file_system {
        retention_in_days = 3
        retention_in_mb   = 35
      }
    }
  }

  identity {
    type = "SystemAssigned"
  }
}

output "resource_group" {
  value = azurerm_resource_group.app.name
}

output "python_app_name" {
  value = azurerm_linux_web_app.python.name
}

output "python_url" {
  value = "https://${azurerm_linux_web_app.python.default_hostname}"
}

output "python_staging_url" {
  value = var.enable_staging_slot ? "https://${azurerm_linux_web_app_slot.python_staging[0].default_hostname}" : null
}

output "node_app_name" {
  value = azurerm_linux_web_app.node.name
}

output "node_url" {
  value = "https://${azurerm_linux_web_app.node.default_hostname}"
}

output "container_url" {
  value = "https://${azurerm_linux_web_app.container.default_hostname}"
}
