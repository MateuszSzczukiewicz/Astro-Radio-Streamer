terraform {
  required_version = ">= 1.5"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }

  backend "s3" {
    bucket = "astro-radio-streamer-tfstate"
    key    = "prod/terraform.tfstate"
    region = "eu-central-1"
  }
}

provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      Project     = "astro-radio-streamer"
      Environment = var.environment
      ManagedBy   = "terraform"
    }
  }
}

resource "aws_vpc" "main" {
  cidr_block           = "10.0.0.0/16"
  enable_dns_hostnames = true
  enable_dns_support   = true
}

resource "aws_subnet" "private_a" {
  vpc_id            = aws_vpc.main.id
  cidr_block        = "10.0.1.0/24"
  availability_zone = "${var.aws_region}a"
}

resource "aws_subnet" "private_b" {
  vpc_id            = aws_vpc.main.id
  cidr_block        = "10.0.2.0/24"
  availability_zone = "${var.aws_region}b"
}

resource "aws_db_subnet_group" "tsdb" {
  name       = "astro-tsdb-subnet-group"
  subnet_ids = [aws_subnet.private_a.id, aws_subnet.private_b.id]
}

resource "aws_security_group" "tsdb" {
  name   = "astro-tsdb-sg"
  vpc_id = aws_vpc.main.id

  ingress {
    from_port       = 5432
    to_port         = 5432
    protocol        = "tcp"
    security_groups = [aws_security_group.receiver.id]
  }
}

resource "aws_security_group" "receiver" {
  name   = "astro-receiver-sg"
  vpc_id = aws_vpc.main.id

  ingress {
    from_port   = var.receiver_port
    to_port     = var.receiver_port
    protocol    = "tcp"
    cidr_blocks = [var.ground_station_cidr]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

resource "aws_db_instance" "timescaledb" {
  identifier     = "astro-telemetry-${var.environment}"
  engine         = "postgres"
  engine_version = "17"
  instance_class = var.db_instance_class

  allocated_storage     = 100
  max_allocated_storage = 1000
  storage_type          = "gp3"
  storage_encrypted     = true

  db_name  = "telemetry"
  username = "astro"
  password = var.db_password

  db_subnet_group_name   = aws_db_subnet_group.tsdb.name
  vpc_security_group_ids = [aws_security_group.tsdb.id]

  backup_retention_period = 7
  multi_az                = var.environment == "prod"
  deletion_protection     = var.environment == "prod"

  skip_final_snapshot = var.environment != "prod"
}

resource "aws_ecr_repository" "receiver" {
  name                 = "astro-radio-streamer/receiver"
  image_tag_mutability = "IMMUTABLE"

  image_scanning_configuration {
    scan_on_push = true
  }
}

resource "aws_ecs_cluster" "main" {
  name = "astro-${var.environment}"

  setting {
    name  = "containerInsights"
    value = "enabled"
  }
}

resource "aws_ecs_task_definition" "receiver" {
  family                   = "astro-receiver"
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = var.receiver_cpu
  memory                   = var.receiver_memory
  execution_role_arn       = aws_iam_role.ecs_execution.arn

  container_definitions = jsonencode([
    {
      name  = "receiver"
      image = "${aws_ecr_repository.receiver.repository_url}:latest"
      portMappings = [
        {
          containerPort = var.receiver_port
          protocol      = "tcp"
        }
      ]
      environment = [
        { name = "DATABASE_URL", value = "postgresql://astro:${var.db_password}@${aws_db_instance.timescaledb.endpoint}/telemetry" },
        { name = "RECEIVER_HOST", value = "0.0.0.0" },
        { name = "RECEIVER_PORT", value = tostring(var.receiver_port) },
        { name = "BATCH_SIZE", value = "100" },
        { name = "FLUSH_TIMEOUT", value = "2.0" },
      ]
      logConfiguration = {
        logDriver = "awslogs"
        options = {
          "awslogs-group"         = "/ecs/astro-receiver"
          "awslogs-region"        = var.aws_region
          "awslogs-stream-prefix" = "receiver"
        }
      }
    }
  ])
}

resource "aws_ecs_service" "receiver" {
  name            = "astro-receiver"
  cluster         = aws_ecs_cluster.main.id
  task_definition = aws_ecs_task_definition.receiver.arn
  desired_count   = var.receiver_replicas
  launch_type     = "FARGATE"

  network_configuration {
    subnets         = [aws_subnet.private_a.id]
    security_groups = [aws_security_group.receiver.id]
  }
}

resource "aws_iam_role" "ecs_execution" {
  name = "astro-ecs-execution-${var.environment}"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "ecs-tasks.amazonaws.com"
        }
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "ecs_execution" {
  role       = aws_iam_role.ecs_execution.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}

resource "aws_cloudwatch_log_group" "receiver" {
  name              = "/ecs/astro-receiver"
  retention_in_days = 30
}
