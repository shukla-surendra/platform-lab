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
resource "azurerm_resource_group" "adf" {
  name     = "rg-datafactory-demo"
  location = "Central India"
}

resource "random_string" "suffix" {
  length  = 6
  special = false
  upper   = false
}

# 2. Storage account this pipeline reads from and writes to. ETL needs
# something real to move data between; one account with two containers
# keeps this demo self-contained (one `terraform apply`) instead of
# requiring separate source/sink systems.
resource "azurerm_storage_account" "data" {
  name                     = "stadfdata${random_string.suffix.result}"
  resource_group_name      = azurerm_resource_group.adf.name
  location                 = azurerm_resource_group.adf.location
  account_tier             = "Standard"
  account_replication_type = "LRS"
  account_kind             = "StorageV2"
}

resource "azurerm_storage_container" "raw" {
  name                  = "raw"
  storage_account_id    = azurerm_storage_account.data.id
  container_access_type = "private"
}

resource "azurerm_storage_container" "processed" {
  name                  = "processed"
  storage_account_id    = azurerm_storage_account.data.id
  container_access_type = "private"
}

# 3. Seed a real input file so the pipeline has something to copy the
# moment you trigger it -- same idea as front-door's index.html: don't
# make the demo require a manual upload step before it does anything.
resource "azurerm_storage_blob" "sample_input" {
  name                 = "sample.csv"
  storage_container_id = azurerm_storage_container.raw.id
  type                 = "Block"
  content_type         = "text/csv"
  source_content       = <<-CSV
    order_id,status,amount
    1,pending,42.50
    2,shipped,19.99
    3,pending,7.25
  CSV
}

# 4. Data Factory -- the workspace everything below lives in. No
# git/DevOps integration configured (that's for a real team's CI/CD
# workflow, not a solo demo).
resource "azurerm_data_factory" "adf" {
  name                = "adf-demo-${random_string.suffix.result}"
  location            = azurerm_resource_group.adf.location
  resource_group_name = azurerm_resource_group.adf.name
}

# 5. Linked Service -- ADF's connection info to the storage account.
# Uses the account key directly for this demo; a real deployment would
# give the Data Factory a Managed Identity and grant it an RBAC role on
# the storage account instead of embedding a key in pipeline config.
resource "azurerm_data_factory_linked_service_azure_blob_storage" "data" {
  name              = "ls-storage"
  data_factory_id   = azurerm_data_factory.adf.id
  connection_string = azurerm_storage_account.data.primary_connection_string
}

# 6. Datasets -- a named pointer to one specific path within a Linked
# Service. One for the source file, one for the destination path; the
# Copy activity below references these by name, not by raw paths.
resource "azurerm_data_factory_dataset_azure_blob" "raw_sample" {
  name                = "ds-raw-sample"
  data_factory_id     = azurerm_data_factory.adf.id
  linked_service_name = azurerm_data_factory_linked_service_azure_blob_storage.data.name

  path     = azurerm_storage_container.raw.name
  filename = azurerm_storage_blob.sample_input.name
}

resource "azurerm_data_factory_dataset_azure_blob" "processed_sample" {
  name                = "ds-processed-sample"
  data_factory_id     = azurerm_data_factory.adf.id
  linked_service_name = azurerm_data_factory_linked_service_azure_blob_storage.data.name

  path     = azurerm_storage_container.processed.name
  filename = azurerm_storage_blob.sample_input.name
}

# 7. Pipeline -- one Copy activity, raw -> processed. Real ADF pipeline
# definitions are JSON under the hood (this is literally what the
# portal's drag-and-drop designer generates and what `az datafactory
# pipeline create-run` submits) -- the provider exposes that directly
# via activities_json rather than modeling every activity type in HCL.
resource "azurerm_data_factory_pipeline" "copy_raw_to_processed" {
  name            = "pl-copy-raw-to-processed"
  data_factory_id = azurerm_data_factory.adf.id

  activities_json = <<JSON
[
  {
    "name": "CopyRawToProcessed",
    "type": "Copy",
    "typeProperties": {
      "source": { "type": "BlobSource" },
      "sink": { "type": "BlobSink" }
    },
    "inputs": [
      { "referenceName": "${azurerm_data_factory_dataset_azure_blob.raw_sample.name}", "type": "DatasetReference" }
    ],
    "outputs": [
      { "referenceName": "${azurerm_data_factory_dataset_azure_blob.processed_sample.name}", "type": "DatasetReference" }
    ]
  }
]
JSON
}

output "resource_group_name" {
  value = azurerm_resource_group.adf.name
}

output "data_factory_name" {
  value = azurerm_data_factory.adf.name
}

output "storage_account_name" {
  value = azurerm_storage_account.data.name
}

output "pipeline_name" {
  value = azurerm_data_factory_pipeline.copy_raw_to_processed.name
}
