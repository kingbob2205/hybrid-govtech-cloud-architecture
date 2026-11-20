# =============================================================================
# Azure Corporate Backbone (5% — Israel Central)
# Microsoft Entra ID Workforce Federation + Microsoft Sentinel Unified SOC SIEM
# =============================================================================

terraform {
  required_version = ">= 1.7.0"
  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 3.115"
    }
  }
}

provider "azurerm" {
  features {}
}

resource "azurerm_resource_group" "soc" {
  name     = "rg-gov-portal-soc-il"
  location = "Israel Central"
}

resource "azurerm_log_analytics_workspace" "sentinel_law" {
  name                = "law-gov-portal-sentinel-il"
  location            = azurerm_resource_group.soc.location
  resource_group_name = azurerm_resource_group.soc.name
  sku                 = "PerGB2018"
  retention_in_days   = 365
}

resource "azurerm_sentinel_log_analytics_workspace_onboarding" "sentinel" {
  workspace_id                 = azurerm_log_analytics_workspace.sentinel_law.id
  customer_managed_key_enabled = false
}
