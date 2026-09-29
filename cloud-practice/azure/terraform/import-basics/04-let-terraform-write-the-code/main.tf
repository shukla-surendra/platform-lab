# ─────────────────────────────────────────────────────────────
# Lesson 04: this file has NO resource blocks, on purpose.
# Terraform will WRITE them for you into generated.tf.
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
