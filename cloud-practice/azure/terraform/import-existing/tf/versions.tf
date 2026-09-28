terraform {
  required_version = ">= 1.6" # import blocks with variable-based ids
  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 4.0"
    }
  }
}

provider "azurerm" {
  features {}
  subscription_id = var.subscription_id
}

variable "subscription_id" { type = string }
variable "location" { type = string }
variable "storage_account_name" { type = string }

locals {
  rg_name = "rg-import-lab"
  rg_id   = "/subscriptions/${var.subscription_id}/resourceGroups/${local.rg_name}"
}
