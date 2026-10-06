# ===========================================================================
# Azure Data Factory tutorial: managed identity + parameterized pipeline + trigger
# ===========================================================================
# Builds on ../data-factory (one hard-coded Copy). This one adds what real
# projects use:
#   1. Managed identity + RBAC   no storage keys anywhere
#   2. Parameterized datasets     ONE dataset serves any file
#   3. Parameterized pipeline     pass the file name at run time
#   4. Schedule trigger           created but OFF (so it costs nothing until you start it)
#
#   Resource group
#   ├─ Storage account ── containers: raw (input), processed (output)
#   │                     raw/orders.csv  (sample file, uploaded by Terraform)
#   └─ Data Factory (system-assigned identity)
#        ├─ Linked service  ls_storage   (auth = the factory's own identity)
#        ├─ Datasets        ds_raw_csv, ds_processed_csv   (parameter: fileName)
#        ├─ Pipeline        pl_copy_file  (parameter: fileName) -> 1 Copy activity
#        └─ Trigger         tr_daily      (schedule, deactivated)

terraform {
  required_version = ">= 1.5"

  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 5.0"
    }
    random = {
      source = "hashicorp/random"
    }
  }
}

provider "azurerm" {
  features {}
}

# ---------------------------------------------------------------------------
# Inputs
# ---------------------------------------------------------------------------
variable "location" {
  type    = string
  default = "Central India"
}

variable "default_file_name" {
  description = "Default value of the pipeline's fileName parameter."
  type        = string
  default     = "orders.csv"
}

# ---------------------------------------------------------------------------
# 1. Resource group + storage (the source and the destination of the copy)
# ---------------------------------------------------------------------------
resource "azurerm_resource_group" "this" {
  name     = "rg-adf-tutorial"
  location = var.location
}

resource "random_string" "suffix" {
  length  = 6
  special = false
  upper   = false
}

resource "azurerm_storage_account" "data" {
  name                     = "stadftut${random_string.suffix.result}"
  resource_group_name      = azurerm_resource_group.this.name
  location                 = azurerm_resource_group.this.location
  account_tier             = "Standard"
  account_replication_type = "LRS"
}

resource "azurerm_storage_container" "raw" {
  name               = "raw"
  storage_account_id = azurerm_storage_account.data.id
}

resource "azurerm_storage_container" "processed" {
  name               = "processed"
  storage_account_id = azurerm_storage_account.data.id
}

# Sample input so the first run has something to copy.
resource "azurerm_storage_blob" "sample" {
  name                 = "orders.csv"
  storage_container_id = azurerm_storage_container.raw.id
  type                 = "Block"
  source_content       = <<-CSV
    order_id,status,amount
    1,paid,120.50
    2,shipped,19.99
    3,pending,7.25
  CSV
}

# ---------------------------------------------------------------------------
# 2. Data Factory with a system-assigned managed identity
#    Azure creates an identity for the factory and deletes it with the factory.
# ---------------------------------------------------------------------------
resource "azurerm_data_factory" "this" {
  name                = "adf-tutorial-${random_string.suffix.result}"
  location            = azurerm_resource_group.this.location
  resource_group_name = azurerm_resource_group.this.name

  identity {
    type = "SystemAssigned"
  }
}

# The identity is still just a "user": it can do nothing until you grant a role.
# Blob Data Contributor = read + write blobs (needed to read raw, write processed).
resource "azurerm_role_assignment" "adf_blob" {
  scope                = azurerm_storage_account.data.id
  role_definition_name = "Storage Blob Data Contributor"
  principal_id         = azurerm_data_factory.this.identity[0].principal_id
}

# ---------------------------------------------------------------------------
# 3. Linked service = the CONNECTION. No key or connection string: it only holds
#    the endpoint, and ADF authenticates as its managed identity.
# ---------------------------------------------------------------------------
resource "azurerm_data_factory_linked_service_azure_blob_storage" "storage" {
  name                 = "ls_storage"
  data_factory_id      = azurerm_data_factory.this.id
  service_endpoint     = azurerm_storage_account.data.primary_blob_endpoint
  use_managed_identity = true

  depends_on = [azurerm_role_assignment.adf_blob]
}

# ---------------------------------------------------------------------------
# 4. Datasets = WHAT data (shape + location) on top of a linked service.
#    The file name is a PARAMETER, filled in by the pipeline at run time.
# ---------------------------------------------------------------------------
resource "azurerm_data_factory_dataset_delimited_text" "raw" {
  name                = "ds_raw_csv"
  data_factory_id     = azurerm_data_factory.this.id
  linked_service_name = azurerm_data_factory_linked_service_azure_blob_storage.storage.name

  parameters = {
    fileName = ""
  }

  azure_blob_storage_location {
    container                = azurerm_storage_container.raw.name
    filename                 = "@dataset().fileName"
    dynamic_filename_enabled = true # tells ADF the value above is an expression
  }

  column_delimiter    = ","
  first_row_as_header = true
}

resource "azurerm_data_factory_dataset_delimited_text" "processed" {
  name                = "ds_processed_csv"
  data_factory_id     = azurerm_data_factory.this.id
  linked_service_name = azurerm_data_factory_linked_service_azure_blob_storage.storage.name

  parameters = {
    fileName = ""
  }

  azure_blob_storage_location {
    container                = azurerm_storage_container.processed.name
    filename                 = "@dataset().fileName"
    dynamic_filename_enabled = true
  }

  column_delimiter    = ","
  first_row_as_header = true
}

# ---------------------------------------------------------------------------
# 5. Pipeline = the ORCHESTRATION. One Copy activity. The pipeline parameter is
#    handed to both datasets with the expression @pipeline().parameters.fileName
# ---------------------------------------------------------------------------
resource "azurerm_data_factory_pipeline" "copy_file" {
  name            = "pl_copy_file"
  data_factory_id = azurerm_data_factory.this.id

  parameters = {
    fileName = var.default_file_name
  }

  activities_json = jsonencode([
    {
      name = "CopyRawToProcessed"
      type = "Copy"
      inputs = [{
        referenceName = azurerm_data_factory_dataset_delimited_text.raw.name
        type          = "DatasetReference"
        parameters    = { fileName = "@pipeline().parameters.fileName" }
      }]
      outputs = [{
        referenceName = azurerm_data_factory_dataset_delimited_text.processed.name
        type          = "DatasetReference"
        parameters    = { fileName = "@pipeline().parameters.fileName" }
      }]
      typeProperties = {
        source = { type = "DelimitedTextSource" }
        sink   = { type = "DelimitedTextSink" }
      }
    }
  ])
}

# ---------------------------------------------------------------------------
# 6. Trigger = WHEN it runs. Created deactivated; start it in the tutorial (step 6).
# ---------------------------------------------------------------------------
resource "azurerm_data_factory_trigger_schedule" "daily" {
  name            = "tr_daily"
  data_factory_id = azurerm_data_factory.this.id
  activated       = false
  frequency       = "Day"
  interval        = 1

  pipeline {
    name       = azurerm_data_factory_pipeline.copy_file.name
    parameters = { fileName = var.default_file_name }
  }
}

# ---------------------------------------------------------------------------
# Outputs (used by scripts/run_pipeline.sh)
# ---------------------------------------------------------------------------
output "resource_group_name" {
  value = azurerm_resource_group.this.name
}

output "data_factory_name" {
  value = azurerm_data_factory.this.name
}

output "storage_account_name" {
  value = azurerm_storage_account.data.name
}

output "pipeline_name" {
  value = azurerm_data_factory_pipeline.copy_file.name
}

output "trigger_name" {
  value = azurerm_data_factory_trigger_schedule.daily.name
}
