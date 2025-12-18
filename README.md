# Triage System – Databricks AI Workflow

AI-powered workflow for ingesting customer materials, running retrieval-augmented analysis, and generating Statements of Work (SoW). The stack matches the reference triage system with FastAPI, React (Vite), PostgreSQL + pgvector, JWT auth, OpenAI, Databricks ingestion, and GCP deployment via Terraform.

## Contents
- [Architecture](#architecture)
- [Prerequisites](#prerequisites)
- [Environment](#environment)
- [Local Development](#local-development)
- [Databricks Mode](#databricks-mode)
- [Testing](#testing)
- [CI/CD](#cicd)
- [Terraform Deploy](#terraform-deploy)
- [Troubleshooting](#troubleshooting)

## Architecture
- **Backend (FastAPI)**: `/backend/app` with JWT auth, document ingestion, RAG search, and SoW generation. Alembic migrations live in `/backend/alembic`.
- **Frontend (React + Vite)**: `/frontend` provides upload, search, and SoW UI, configurable with `VITE_API_BASE_URL`.
- **Database**: PostgreSQL + pgvector (via Docker Compose or Cloud SQL). Tables for users, refresh tokens, documents, document chunks (vector embeddings), and SOWs.
- **LLM & Embeddings**: OpenAI Chat + embeddings with deterministic local fallback.
- **Databricks Ingestion**: Optional ingestion from Unity Catalog/SQL Warehouse via `DATABRICKS_*` settings.
- **Infra**: Docker Compose for local, Terraform for GCP Cloud Run + Cloud SQL + Artifact Registry, GitHub Actions for CI/CD.

## Prerequisites
- Python 3.11+
- Node.js 20+
- Docker / Docker Compose
- Access to OpenAI API key
- For Databricks mode: workspace host + PAT and SQL Warehouse/HTTP path

## Environment
Copy `.env.example` to `.env` and fill in values:
```
DATABASE_URL=postgresql+psycopg://postgres:postgres@localhost:5432/triage
JWT_SECRET_KEY=replace-me
OPENAI_API_KEY=your-openai-key
OPENAI_MODEL=gpt-4o-mini
EMBEDDING_MODEL=text-embedding-3-small
BACKEND_CORS_ORIGINS=http://localhost:5173
DATABRICKS_HOST=https://your-workspace.cloud.databricks.com
DATABRICKS_TOKEN=your-token-here
DATABRICKS_HTTP_PATH=/sql/1.0/warehouses/xxxx
DATABRICKS_WAREHOUSE_ID=xxxx
```
Frontend expects `VITE_API_BASE_URL` (defaults to `http://localhost:8000/api` when running locally).

## Local Development
1) Start PostgreSQL + pgvector:
```bash
docker-compose up -d db
```

2) Backend setup:
```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
export DATABASE_URL=postgresql+psycopg://postgres:postgres@localhost:5432/triage
alembic -c backend/alembic.ini upgrade head
uvicorn backend.app.main:app --reload
```
API served at `http://localhost:8000`; docs at `/api/docs`.

3) Frontend setup (separate terminal):
```bash
cd frontend
npm install
VITE_API_BASE_URL=http://localhost:8000/api npm run dev -- --host --port 4173
```
Open `http://localhost:4173`.

## Databricks Mode
Set the Databricks env vars (host/token/http path/warehouse). To ingest a table sample into pgvector:
```bash
curl -X POST "http://localhost:8000/api/databricks/ingest-table?table=main.default.customer_docs&limit=25" \
  -H "Authorization: Bearer <access_token>"
```
You can also authenticate via the UI then run a retrieval query and generate a SoW; context from Databricks ingests is indexed like uploaded docs.

## Testing
Run backend smoke tests (requires Postgres from Docker Compose):
```bash
pytest backend/app/tests
```
Front-end build check:
```bash
cd frontend && npm install && npm run build
```

## CI/CD
- `.github/workflows/ci.yml`: runs backend tests against pgvector Postgres service and builds the frontend on PRs/push.
- `.github/workflows/deploy.yml`: builds/pushes backend and frontend images to Artifact Registry and applies Terraform on merges to `main/master`.
- Required GitHub secrets:
  - `GCP_PROJECT_ID`, `GCP_REGION`, `GCP_SA_KEY`
  - `DB_PASSWORD`
  - `OPENAI_API_KEY`

## Terraform Deploy
1) Authenticate to GCP and set env secrets (see above).
2) From `/terraform`:
```bash
terraform init
terraform apply \
  -var="project_id=your-project" \
  -var="region=us-central1" \
  -var="db_password=strongpass" \
  -var="backend_image_tag=backend:<sha>" \
  -var="frontend_image_tag=frontend:<sha>" \
  -var="openai_api_key=$OPENAI_API_KEY"
```
3) Outputs include `backend_url` and `frontend_url`. Set `VITE_API_BASE_URL` to the backend URL for frontend deploys.

## Troubleshooting
- **DB connection refused**: ensure `docker-compose up -d db` is running; check `DATABASE_URL`.
- **pgvector errors**: confirm the container image is `pgvector/pgvector:pg16` and migration ran.
- **Missing secrets**: verify `.env` or GitHub secrets for OpenAI and JWT secret.
- **Cloud Run issues**: check Cloud Run logs and Secret Manager bindings; redeploy images with matching tags.
- **Embedding errors**: ensure `OPENAI_API_KEY` is set; the system will fall back to deterministic local embeddings if not.
- **Databricks auth errors**: validate PAT scope and SQL Warehouse id/http path; run a small `SELECT 1` from the workspace to confirm access.
