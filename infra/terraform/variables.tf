variable "aws_region" {
  type    = string
  default = "eu-central-1"
}

variable "environment" {
  type    = string
  default = "dev"

  validation {
    condition     = contains(["dev", "staging", "prod"], var.environment)
    error_message = "Environment must be dev, staging, or prod."
  }
}

variable "db_password" {
  type      = string
  sensitive = true
}

variable "db_instance_class" {
  type    = string
  default = "db.t3.micro"
}

variable "receiver_port" {
  type    = number
  default = 8888
}

variable "receiver_cpu" {
  type    = string
  default = "256"
}

variable "receiver_memory" {
  type    = string
  default = "512"
}

variable "receiver_replicas" {
  type    = number
  default = 1
}

variable "ground_station_cidr" {
  type        = string
  default     = "0.0.0.0/0"
  description = "CIDR block of the ground station network allowed to connect"
}
