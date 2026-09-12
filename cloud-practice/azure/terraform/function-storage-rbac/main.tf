terraform {
  required_providers {
    azurerm = { source = "hashicorp/azurerm" }
    random  = { source = "hashicorp/random" }
  }
}

provider "azurerm" {
  features {}
}

# 1. Resource Group
resource "azurerm_resource_group" "demo" {
  name     = "rg-func-rbac-demo"
  location = "Central India"
}

resource "random_string" "suffix" {
  length  = 6
  special = false
  upper   = false
}

# 2. The Function App's OWN runtime storage -- every Function App needs
# one, for internal state (triggers, locks, deployment packages), not for
# your data. This is deliberately the "boring" storage account: accessed
# via key, like the plain functions/ module in this repo. Keeping it
# separate from the "data" account below is what makes the least-privilege
# story about the data account clean -- nothing here conflates "storage
# the platform needs to function" with "storage this specific workload is
# scoped to touch."
resource "azurerm_storage_account" "func_runtime" {
  name                     = "stfuncrt${random_string.suffix.result}"
  resource_group_name      = azurerm_resource_group.demo.name
  location                 = azurerm_resource_group.demo.location
  account_tier             = "Standard"
  account_replication_type = "LRS"
}

# 3. The DATA storage account -- what the function's code actually reads
# from and writes to, using its Managed Identity + custom RBAC roles
# below. No connection string or account key is ever handed to the
# function for this account -- that's the entire point of this module.
resource "azurerm_storage_account" "data" {
  name                     = "stfuncdata${random_string.suffix.result}"
  resource_group_name      = azurerm_resource_group.demo.name
  location                 = azurerm_resource_group.demo.location
  account_tier             = "Standard"
  account_replication_type = "LRS"
}

resource "azurerm_storage_container" "input" {
  name                  = "input"
  storage_account_id    = azurerm_storage_account.data.id
  container_access_type = "private"
}

resource "azurerm_storage_container" "output" {
  name                  = "output"
  storage_account_id    = azurerm_storage_account.data.id
  container_access_type = "private"
}

# 4. Seed a real input file so there's something to process the moment
# the function is deployed. Written using the applying principal's own
# (broad) credentials -- unrelated to the function's deliberately narrow
# identity below.
resource "azurerm_storage_blob" "sample_input" {
  name                 = "sample.csv"
  storage_container_id = azurerm_storage_container.input.id
  type                 = "Block"
  content_type         = "text/csv"
  source_content       = <<-CSV
    order_id,status,amount
    1,pending,42.50
    2,shipped,19.99
    3,pending,7.25
  CSV
}

# 5. Consumption plan -- pay-per-execution, scales to zero when idle.
resource "azurerm_service_plan" "demo" {
  name                = "asp-func-rbac-demo"
  resource_group_name = azurerm_resource_group.demo.name
  location            = azurerm_resource_group.demo.location
  os_type             = "Linux"
  sku_name            = "Y1"
}

# 6. The Function App. `identity { type = "SystemAssigned" }` is the
# Azure equivalent of an AWS Lambda execution role -- except in Azure,
# the *identity* (who the function authenticates as) and the
# *permissions* (what that identity can do) are two entirely separate
# resources (this block, vs. the role definitions/assignments below),
# not one bundled "role" the way AWS's IAM role is both at once.
resource "azurerm_linux_function_app" "demo" {
  name                       = "func-rbac-demo-${random_string.suffix.result}"
  resource_group_name        = azurerm_resource_group.demo.name
  location                   = azurerm_resource_group.demo.location
  service_plan_id            = azurerm_service_plan.demo.id
  storage_account_name       = azurerm_storage_account.func_runtime.name
  storage_account_access_key = azurerm_storage_account.func_runtime.primary_access_key

  site_config {
    application_stack {
      python_version = "3.11"
    }
  }

  app_settings = {
    # No key, no connection string -- just the account name. The function
    # code builds `https://<name>.blob.core.windows.net` itself and
    # authenticates with DefaultAzureCredential(), which (running inside
    # Azure) resolves to this Function App's own Managed Identity token.
    "DATA_STORAGE_ACCOUNT_NAME" = azurerm_storage_account.data.name
    "INPUT_CONTAINER"           = azurerm_storage_container.input.name
    "OUTPUT_CONTAINER"          = azurerm_storage_container.output.name
    # Zip-deploy of Python code needs Oryx to build it remotely (install
    # requirements.txt) -- without this, the deployed zip's dependencies
    # are simply never installed.
    "SCM_DO_BUILD_DURING_DEPLOYMENT" = "true"
    # azurerm_linux_function_app defaults Linux Consumption apps into
    # "Run From Package" mode (WEBSITE_RUN_FROM_PACKAGE set to a SAS URL
    # pointing at an immutable, read-only zip in the runtime storage
    # account). That mode skips Oryx entirely -- there is no remote build
    # step, so a zip without its dependencies pre-vendored inside it just
    # fails to import at runtime with no functions ever registered (hit
    # this directly: `az functionapp function list` came back empty and
    # every route 404'd, silently, with no error surfaced anywhere).
    # Forcing this to "0" makes zip-deploy build remotely via Oryx and run
    # from local writable disk instead, which is what SCM_DO_BUILD_DURING_
    # DEPLOYMENT above actually requires to do anything.
    "WEBSITE_RUN_FROM_PACKAGE" = "0"
  }

  identity {
    type = "SystemAssigned"
  }
}

# 7. Custom role #1: read-only, and ONLY on the input container. Mirrors
# Microsoft's own built-in "Storage Blob Data Reader" role's data_actions
# exactly, but assignable_scopes pins it to one container instead of a
# whole storage account/subscription -- the Azure analog of an AWS IAM
# policy statement scoped to `arn:aws:s3:::bucket/input/*` with
# `s3:GetObject` + `s3:ListBucket`.
resource "azurerm_role_definition" "blob_reader_input" {
  name        = "Blob Reader - input container only (${random_string.suffix.result})"
  scope       = azurerm_storage_container.input.id
  description = "Read blob content and list the 'input' container. No write, no delete, no access to any other container."

  permissions {
    actions = []
    data_actions = [
      # Container-level "read" (list containers/get properties) is a
      # control-plane Action in Azure's model (isDataAction: false,
      # confirmed via `az provider operation show --namespace
      # Microsoft.Storage`) -- it is NOT a valid data_action at all, and
      # Azure rejects it outright if you try. Only the blobs/* operations
      # are true DataActions. This role is deliberately just blob content
      # read -- no container-listing capability granted.
      "Microsoft.Storage/storageAccounts/blobServices/containers/blobs/read",
    ]
  }

  assignable_scopes = [
    azurerm_storage_container.input.id,
  ]
}

# 8. Custom role #2: write-only, and ONLY on the output container. No
# read data_action at all -- this identity can drop a file in `output`
# but cannot read anything back out of it once written.
resource "azurerm_role_definition" "blob_writer_output" {
  name        = "Blob Writer - output container only (${random_string.suffix.result})"
  scope       = azurerm_storage_container.output.id
  description = "Write (create/overwrite) blob content in the 'output' container only. No read, no delete, no access to any other container."

  permissions {
    actions = []
    data_actions = [
      "Microsoft.Storage/storageAccounts/blobServices/containers/blobs/write",
      "Microsoft.Storage/storageAccounts/blobServices/containers/blobs/add/action",
    ]
  }

  assignable_scopes = [
    azurerm_storage_container.output.id,
  ]
}

# 9. Bind each custom role to the Function App's Managed Identity, at
# each container's own scope -- this is the "attach policy to role" step
# from the AWS mental model, except the "policy" (role definition) and
# the "attach" (role assignment) are explicitly two different resource
# types here, and the scope is a property of the assignment (and
# constrained by the definition's assignable_scopes), not baked into the
# policy document's Resource field the way an ARN is in AWS IAM.
resource "azurerm_role_assignment" "reader_binding" {
  scope              = azurerm_storage_container.input.id
  role_definition_id = azurerm_role_definition.blob_reader_input.role_definition_resource_id
  principal_id       = azurerm_linux_function_app.demo.identity[0].principal_id
}

resource "azurerm_role_assignment" "writer_binding" {
  scope              = azurerm_storage_container.output.id
  role_definition_id = azurerm_role_definition.blob_writer_output.role_definition_resource_id
  principal_id       = azurerm_linux_function_app.demo.identity[0].principal_id
}

output "resource_group_name" {
  value = azurerm_resource_group.demo.name
}

output "function_app_name" {
  value = azurerm_linux_function_app.demo.name
}

output "default_hostname" {
  value = azurerm_linux_function_app.demo.default_hostname
}

output "data_storage_account_name" {
  value = azurerm_storage_account.data.name
}

output "function_principal_id" {
  value = azurerm_linux_function_app.demo.identity[0].principal_id
}
