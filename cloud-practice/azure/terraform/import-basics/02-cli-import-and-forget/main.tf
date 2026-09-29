# ─────────────────────────────────────────────────────────────
# Lesson 02: same idea as lesson 01, but there is NO import.tf here.
# We import with the `terraform import` command instead.
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

resource "azurerm_resource_group" "lesson" {
  name     = "rg-lesson02"
  location = "centralindia"

  tags = {
    owner = "me"
  }
}
