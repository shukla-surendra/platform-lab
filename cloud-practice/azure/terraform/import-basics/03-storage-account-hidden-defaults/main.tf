# ─────────────────────────────────────────────────────────────
# Lesson 03: TWO resources, a resource group and a storage account in it.
# Written "the obvious way", with only the settings you passed to `az`.
# (The first plan will show you why that isn't enough.)
# ─────────────────────────────────────────────────────────────

terraform {
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

variable "subscription_id" {
  type = string
}

# Storage account names are globally unique across ALL of Azure,
# so yours has a random suffix. It's set in terraform.tfvars.
variable "storage_account_name" {
  type = string
}

resource "azurerm_resource_group" "lesson" {
  name     = "rg-lesson03"
  location = "centralindia"
}

resource "azurerm_storage_account" "lesson" {
  name                     = var.storage_account_name
  resource_group_name      = azurerm_resource_group.lesson.name
  location                 = azurerm_resource_group.lesson.location
  account_tier             = "Standard"
  account_replication_type = "LRS"
}
