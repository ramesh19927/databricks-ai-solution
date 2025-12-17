# Databricks AI Workflow

AI-powered workflow for ingesting customer materials and generating Scope of Work documents.

## Quick Start

1. Clone this repository
2. Install dependencies: `pip install -r requirements.txt`
3. Configure your Databricks credentials and OpenAI API key (see Environment below)
4. Run the CLI: `python main.py run --workflow sow-generation`

## Project Structure

- `notebooks/` - Databricks notebooks
- `src/` - Python source code
- `config/` - Configuration files

## Environment

The system reads configuration from environment variables (or a `.env` file):

- `DATABRICKS_HOST` / `DATABRICKS_TOKEN` - Databricks workspace and authentication
- `DATABRICKS_WAREHOUSE_ID` - SQL Warehouse for Unity Catalog persistence
- `DATABRICKS_CATALOG` / `DATABRICKS_SCHEMA` - Where to store documents and SOWs
- `VECTOR_SEARCH_ENDPOINT` / `VECTOR_SEARCH_INDEX` - Vector Search endpoint and index name
- `OPENAI_API_KEY` / `OPENAI_MODEL` - LLM and embedding configuration

## Usage

Run the CLI:

```bash
python main.py run --workflow sow-generation --project-id demo-001
python main.py run --workflow document-ingestion
python main.py status
python main.py test
```

Smoke-test the project without Databricks access:

```bash
python test_workflow.py
```

## Components

- `src/services/document_service.py` - Document ingestion (PDF, DOCX, TXT, CSV), chunking, and Unity Catalog persistence
- `src/services/vector_search_service.py` - Embedding creation and Databricks Vector Search operations
- `src/services/sow_service.py` - SOW generation via LLM with optional Unity Catalog persistence
- `src/orchestration/pipeline.py` - Workflow orchestration and retries
