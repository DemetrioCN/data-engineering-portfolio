terraform {
  required_providers {
    databricks = {
      source  = "databricks/databricks"
      version = "~> 1.55"
    }
  }
}

provider "databricks" {
  # No explicit credentials: the provider automatically falls back to
  # ~/.databrickscfg (DEFAULT profile), the same one you already authenticated with the CLI.
}