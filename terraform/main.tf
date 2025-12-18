terraform {
  required_version = ">= 1.5.0"
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = ">= 5.21.0"
    }
  }
}

provider "google" {
  project = var.project_id
  region  = var.region
}

resource "google_project_service" "apis" {
  for_each = toset([
    "run.googleapis.com",
    "artifactregistry.googleapis.com",
    "sqladmin.googleapis.com",
    "secretmanager.googleapis.com",
    "compute.googleapis.com",
  ])
  project = var.project_id
  service = each.key
}

resource "google_artifact_registry_repository" "backend" {
  location      = var.region
  repository_id = "${var.prefix}-backend"
  description   = "Container registry for backend"
  format        = "DOCKER"
}

resource "google_artifact_registry_repository" "frontend" {
  location      = var.region
  repository_id = "${var.prefix}-frontend"
  description   = "Container registry for frontend"
  format        = "DOCKER"
}

resource "google_sql_database_instance" "db" {
  name             = "${var.prefix}-pg"
  database_version = "POSTGRES_15"
  region           = var.region
  settings {
    tier = "db-custom-1-3840"
    ip_configuration {
      ipv4_enabled = true
      authorized_networks {
        value = var.authorized_cidr
      }
    }
  }
  depends_on = [google_project_service.apis]
}

resource "google_sql_database" "app" {
  name     = "triage"
  instance = google_sql_database_instance.db.name
}

resource "google_sql_user" "app" {
  name     = var.db_user
  instance = google_sql_database_instance.db.name
  password = var.db_password
}

resource "google_secret_manager_secret" "openai" {
  secret_id = "${var.prefix}-openai"
  replication {
    automatic = true
  }
}

resource "google_secret_manager_secret_version" "openai_version" {
  secret      = google_secret_manager_secret.openai.id
  secret_data = var.openai_api_key
}

resource "google_service_account" "backend_sa" {
  account_id   = "${var.prefix}-backend"
  display_name = "Backend Cloud Run"
}

resource "google_cloud_run_v2_service" "backend" {
  name     = "${var.prefix}-backend"
  location = var.region
  template {
    service_account = google_service_account.backend_sa.email
    containers {
      image = "${google_artifact_registry_repository.backend.repository_url}/${var.backend_image_tag}"
      env {
        name  = "DATABASE_URL"
        value = "postgresql+psycopg://${var.db_user}:${var.db_password}@${google_sql_database_instance.db.public_ip_address}:5432/${google_sql_database.app.name}"
      }
      env {
        name  = "OPENAI_API_KEY"
        value_source {
          secret_key_ref {
            secret  = google_secret_manager_secret.openai.secret_id
            version = "latest"
          }
        }
      }
    }
  }
  traffic {
    percent         = 100
    latest_revision = true
  }
  depends_on = [google_project_service.apis]
}

resource "google_cloud_run_v2_service" "frontend" {
  name     = "${var.prefix}-frontend"
  location = var.region
  template {
    containers {
      image = "${google_artifact_registry_repository.frontend.repository_url}/${var.frontend_image_tag}"
      env {
        name  = "VITE_API_BASE_URL"
        value = google_cloud_run_v2_service.backend.uri
      }
    }
  }
  depends_on = [google_project_service.apis]
}

output "backend_url" {
  value = google_cloud_run_v2_service.backend.uri
}

output "frontend_url" {
  value = google_cloud_run_v2_service.frontend.uri
}
