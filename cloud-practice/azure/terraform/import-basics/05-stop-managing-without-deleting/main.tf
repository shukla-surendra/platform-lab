# ─────────────────────────────────────────────────────────────
# Lesson 05: the reverse of import.
# Terraform CREATES these two resource groups, then we tell it to
# let go of one of them WITHOUT deleting it.
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

resource "azurerm_resource_group" "keep" {
  name     = "rg-lesson05-keep"
  location = "centralindia"
}

resource "azurerm_resource_group" "handover" {
  name     = "rg-lesson05-handover"
  location = "centralindia"
}
