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
resource "azurerm_resource_group" "fd" {
  name     = "rg-frontdoor-demo"
  location = "Central India"
}

resource "random_string" "suffix" {
  length  = 6
  special = false
  upper   = false
}

# 2. The origin -- a Storage Account with static website hosting turned
# on. Front Door needs something real to front; this keeps the whole demo
# self-contained (one `terraform apply`) instead of requiring you to
# stand up a separate App Service/VM first. Storage's static website
# feature serves plain HTML/CSS/JS over HTTPS with no server to manage --
# genuinely the simplest possible "real HTTP origin."
resource "azurerm_storage_account" "origin" {
  name                     = "stfdorigin${random_string.suffix.result}"
  resource_group_name      = azurerm_resource_group.fd.name
  location                 = azurerm_resource_group.fd.location
  account_tier             = "Standard"
  account_replication_type = "LRS"
}

# 2b. Static website hosting -- a separate resource (current azurerm),
# not a block on the storage account itself. Enabling this is what
# creates the fixed, system-managed "$web" container static sites serve
# from.
resource "azurerm_storage_account_static_website" "origin" {
  storage_account_id = azurerm_storage_account.origin.id
  index_document     = "index.html"
}

# The "$web" container isn't something this config creates directly (it's
# a side effect of the resource above) -- read it back so the blob below
# can reference it by ID. depends_on is needed explicitly since nothing
# else here gives Terraform a reason to order this after
# azurerm_storage_account_static_website.origin.
data "azurerm_storage_container" "web" {
  name               = "$web"
  storage_account_id = azurerm_storage_account.origin.id
  depends_on         = [azurerm_storage_account_static_website.origin]
}

# 3. A real index.html so hitting the Front Door endpoint after apply
# returns actual content immediately, not a 404 from an empty site.
resource "azurerm_storage_blob" "index" {
  name                 = "index.html"
  storage_container_id = data.azurerm_storage_container.web.id
  type                 = "Block"
  content_type         = "text/html"
  source_content       = "<h1>Hello from behind Azure Front Door</h1>"
}

# 4. Front Door Profile -- Standard tier (Premium adds managed WAF rules,
# bot protection, and Private Link origins, none of which this minimal
# demo needs).
resource "azurerm_cdn_frontdoor_profile" "demo" {
  name                = "fd-demo-${random_string.suffix.result}"
  resource_group_name = azurerm_resource_group.fd.name
  sku_name            = "Standard_AzureFrontDoor"
}

# 5. Endpoint -- this is what actually gets the public
# <name>.azurefd.net hostname you hit from a browser/curl.
resource "azurerm_cdn_frontdoor_endpoint" "demo" {
  name                     = "fde-demo-${random_string.suffix.result}"
  cdn_frontdoor_profile_id = azurerm_cdn_frontdoor_profile.demo.id
}

# 6. Origin Group -- the load-balancing + health-probe unit; an Origin
# (step 7) always belongs to exactly one of these, even with only one
# origin in it, same relationship as a Load Balancer's backend pool.
resource "azurerm_cdn_frontdoor_origin_group" "demo" {
  name                     = "og-demo"
  cdn_frontdoor_profile_id = azurerm_cdn_frontdoor_profile.demo.id

  health_probe {
    path                = "/"
    request_type        = "GET"
    protocol            = "Https"
    interval_in_seconds = 100
  }

  load_balancing {}
}

# 7. Origin -- points at the Storage static website's own hostname.
# certificate_name_check_enabled must stay true against a real hostname
# like this (only ever disabled for IP-address origins, which can't
# present a matching TLS cert).
resource "azurerm_cdn_frontdoor_origin" "demo" {
  name                          = "origin-storage"
  cdn_frontdoor_origin_group_id = azurerm_cdn_frontdoor_origin_group.demo.id

  host_name                      = trimsuffix(replace(azurerm_storage_account.origin.primary_web_endpoint, "https://", ""), "/")
  origin_host_header             = trimsuffix(replace(azurerm_storage_account.origin.primary_web_endpoint, "https://", ""), "/")
  certificate_name_check_enabled = true
}

# 8. Route -- wires the endpoint to the origin group; without this,
# Front Door has a public hostname and a configured origin that are
# simply never connected to each other.
resource "azurerm_cdn_frontdoor_route" "demo" {
  name                          = "route-demo"
  cdn_frontdoor_endpoint_id     = azurerm_cdn_frontdoor_endpoint.demo.id
  cdn_frontdoor_origin_group_id = azurerm_cdn_frontdoor_origin_group.demo.id
  cdn_frontdoor_origin_ids      = [azurerm_cdn_frontdoor_origin.demo.id]

  supported_protocols    = ["Http", "Https"]
  patterns_to_match      = ["/*"]
  forwarding_protocol    = "HttpsOnly"
  https_redirect_enabled = true
  link_to_default_domain = true
}

output "frontdoor_endpoint_hostname" {
  value = azurerm_cdn_frontdoor_endpoint.demo.host_name
}

output "origin_hostname" {
  value = azurerm_storage_account.origin.primary_web_endpoint
}
