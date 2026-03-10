output "database_endpoint" {
  value = aws_db_instance.timescaledb.endpoint
}

output "ecr_repository_url" {
  value = aws_ecr_repository.receiver.repository_url
}

output "ecs_cluster_name" {
  value = aws_ecs_cluster.main.name
}

output "receiver_security_group_id" {
  value = aws_security_group.receiver.id
}
