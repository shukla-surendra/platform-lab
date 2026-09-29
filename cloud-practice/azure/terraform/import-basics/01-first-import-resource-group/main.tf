# ─────────────────────────────────────────────────────────────
# Lesson 01 — the ONE resource we want Terraform to take over.
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

# This block describes the resource group EXACTLY as it already exists
# in Azure (same name, same location, same tags).
resource "azurerm_resource_group" "lesson" {
  name     = "rg-lesson01"
  location = "centralindia"

  tags = {
    owner = "me"
  }
}
