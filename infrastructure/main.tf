terraform {
  required_version = ">= 1.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = ">= 6.18"
    }
  }
}

# AWS Provider with default tags applied to all resources
# This ensures consistent tagging across the entire infrastructure
provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      project_name = var.project_name
      environment  = var.environment
      managed_by   = "terraform"
    }
  }
}

# Secondary region provider for DSQL multi-region cluster
provider "aws" {
  alias  = "secondary"
  region = var.secondary_region

  default_tags {
    tags = {
      project_name = var.project_name
      environment  = var.environment
      managed_by   = "terraform"
    }
  }
}

# Witness region provider for DSQL multi-region cluster
provider "aws" {
  alias  = "witness"
  region = var.witness_region

  default_tags {
    tags = {
      project_name = var.project_name
      environment  = var.environment
      managed_by   = "terraform"
    }
  }
}

data "aws_availability_zones" "available" {
  state = "available"
}

data "aws_caller_identity" "current" {}