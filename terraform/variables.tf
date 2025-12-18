variable "project_id" {
  description = "GCP project id"
  type        = string
}

variable "region" {
  description = "GCP region"
  type        = string
  default     = "us-central1"
}

variable "prefix" {
  description = "Resource prefix"
  type        = string
  default     = "triage"
}

variable "authorized_cidr" {
  description = "Authorized network for Cloud SQL"
  type        = string
  default     = "0.0.0.0/0"
}

variable "db_user" {
  description = "Database username"
  type        = string
  default     = "postgres"
}

variable "db_password" {
  description = "Database password"
  type        = string
}

variable "backend_image_tag" {
  description = "Container tag for backend"
  type        = string
}

variable "frontend_image_tag" {
  description = "Container tag for frontend"
  type        = string
}

variable "openai_api_key" {
  description = "OpenAI secret"
  type        = string
  sensitive   = true
}
