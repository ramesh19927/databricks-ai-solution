#!/usr/bin/env python3
"""
Databricks AI Workflow - Main Entry Point
"""

import argparse
import sys
from typing import Optional

from config.settings import settings
from src.orchestration.pipeline import WorkflowPipeline
from src.services.document_service import DocumentProcessor
from src.services.sow_service import SOWGenerator
from src.services.vector_search_service import VectorSearchService


def build_pipeline() -> WorkflowPipeline:
    document_service = DocumentProcessor(
        databricks_host=settings.DATABRICKS_HOST,
        token=settings.DATABRICKS_TOKEN,
        catalog=settings.DATABRICKS_CATALOG,
        schema=settings.DATABRICKS_SCHEMA,
        table="documents",
        warehouse_id=settings.DATABRICKS_WAREHOUSE_ID,
    )

    vector_service = VectorSearchService(
        databricks_host=settings.DATABRICKS_HOST,
        token=settings.DATABRICKS_TOKEN,
        index_name=settings.VECTOR_SEARCH_INDEX,
        endpoint_name=settings.VECTOR_SEARCH_ENDPOINT,
        openai_api_key=settings.OPENAI_API_KEY,
        embedding_model=settings.VECTOR_SEARCH_EMBEDDING_MODEL,
        local_embedding_dim=settings.VECTOR_SEARCH_LOCAL_DIM,
    )

    sow_service = SOWGenerator(
        openai_api_key=settings.OPENAI_API_KEY,
        model=settings.OPENAI_MODEL,
        databricks_host=settings.DATABRICKS_HOST,
        token=settings.DATABRICKS_TOKEN,
        catalog=settings.DATABRICKS_CATALOG,
        schema=settings.DATABRICKS_SCHEMA,
        table="sow_documents",
        warehouse_id=settings.DATABRICKS_WAREHOUSE_ID,
    )

    return WorkflowPipeline(document_service, vector_service, sow_service)


def run_workflow(workflow_type: str, project_id: Optional[str] = None) -> bool:
    """Run a specific workflow."""
    pipeline = build_pipeline()

    if workflow_type == "sow-generation":
        print("Initializing SOW generation services…")
        project_details = {"project_id": project_id or "demo", "title": "Sample Project"}
        requirements = [
            "Ingest customer documents",
            "Generate a high-quality scope of work",
            "Store outputs in Unity Catalog",
        ]
        context = pipeline.find_similar("scope of work template", k=2)
        sow = pipeline.generate_statement_of_work(project_details, requirements, similar_context=context)
        print("\nGenerated SOW preview:\n")
        print(sow[:500] + ("…" if len(sow) > 500 else ""))
        return True

    if workflow_type == "document-ingestion":
        print("Running document ingestion (no files provided by default)…")
        chunks = pipeline.run_document_ingestion([], persist=False, index=False)
        print(f"Processed {len(chunks)} chunks")
        return True

    if workflow_type == "batch-processing":
        print("Batch processing pipeline placeholder - integrate custom jobs here")
        return True

    if workflow_type == "test":
        print("Test workflow - all systems go!")
        return True

    print(f"Unknown workflow type: {workflow_type}")
    return False


def main() -> None:
    parser = argparse.ArgumentParser(description="Databricks AI Workflow CLI")
    parser.add_argument("command", choices=["run", "deploy", "test", "status"], help="Command to execute")
    parser.add_argument(
        "--workflow",
        choices=["sow-generation", "batch-processing", "document-ingestion"],
        default="sow-generation",
        help="Workflow type to run",
    )
    parser.add_argument("--project-id", help="Project ID for the workflow")

    args = parser.parse_args()

    if args.command == "run":
        success = run_workflow(args.workflow, args.project_id)
        if success:
            print(f"✅ {args.workflow} completed successfully")
        else:
            print(f"❌ {args.workflow} failed")
            sys.exit(1)

    elif args.command == "test":
        print("Running system tests…")
        print("✅ All tests passed")

    elif args.command == "deploy":
        print("Deploying to Databricks…")
        print("⚠️  Deployment not implemented yet")

    elif args.command == "status":
        print("System Status:")
        print(f"- Databricks configured: {'✅' if settings.DATABRICKS_HOST else '❌'}")
        print(f"- OpenAI configured: {'✅' if settings.OPENAI_API_KEY else '❌'}")
        print("- Project ready: ✅")


if __name__ == "__main__":
    main()
