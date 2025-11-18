# Aurora DSQL Multi-Region Cluster for globally distributed SQL database
#
# Using the official terraform-aws-modules/rds-aurora DSQL module
# which supports multi-region clusters with AWS Provider >= 6.18

# Primary region cluster
module "dsql_primary" {
  source  = "terraform-aws-modules/rds-aurora/aws//modules/dsql"
  version = "~> 9.0"

  deletion_protection_enabled = false
  witness_region              = var.witness_region
  create_cluster_peering      = true
  clusters                    = [module.dsql_secondary.arn]

  tags = {
    Name        = "${var.project_name}-dsql-primary"
    Environment = var.environment
    Region      = var.aws_region
  }
}

# Secondary region cluster
module "dsql_secondary" {
  source  = "terraform-aws-modules/rds-aurora/aws//modules/dsql"
  version = "~> 9.0"

  providers = {
    aws = aws.secondary
  }

  deletion_protection_enabled = false
  witness_region              = var.witness_region
  create_cluster_peering      = true
  clusters                    = [module.dsql_primary.arn]

  tags = {
    Name        = "${var.project_name}-dsql-secondary"
    Environment = var.environment
    Region      = var.secondary_region
  }
}

# Keep these resource blocks as aliases for backward compatibility with existing references
resource "aws_dsql_cluster" "primary" {
  count = 0
}

resource "aws_dsql_cluster" "secondary" {
  count = 0
}