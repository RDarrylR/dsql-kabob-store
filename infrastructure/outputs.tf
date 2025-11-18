output "alb_dns_name" {
  description = "DNS name of the load balancer"
  value       = aws_lb.main.dns_name
}

output "alb_zone_id" {
  description = "Zone ID of the load balancer"
  value       = aws_lb.main.zone_id
}

output "ecr_backend_repository_url" {
  description = "URL of the backend ECR repository"
  value       = aws_ecr_repository.backend.repository_url
}

output "ecr_frontend_repository_url" {
  description = "URL of the frontend ECR repository"
  value       = aws_ecr_repository.frontend.repository_url
}

output "ecs_cluster_name" {
  description = "Name of the ECS cluster"
  value       = aws_ecs_cluster.main.name
}

output "dsql_primary_cluster_arn" {
  description = "The Amazon Resource Name (ARN) of the primary DSQL cluster"
  value       = module.dsql_primary.arn
}

output "dsql_primary_cluster_identifier" {
  description = "The primary DSQL cluster identifier"
  value       = module.dsql_primary.identifier
}

output "dsql_secondary_cluster_arn" {
  description = "The Amazon Resource Name (ARN) of the secondary DSQL cluster"
  value       = module.dsql_secondary.arn
}

output "dsql_secondary_cluster_identifier" {
  description = "The secondary DSQL cluster identifier"
  value       = module.dsql_secondary.identifier
}

output "dsql_witness_region" {
  description = "The witness region for the multi-region DSQL cluster"
  value       = var.witness_region
}

output "aws_region" {
  description = "The primary AWS region"
  value       = var.aws_region
}

output "secondary_region" {
  description = "The secondary AWS region for multi-region DSQL"
  value       = var.secondary_region
}