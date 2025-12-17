# Workflow Orchestrator for Databricks AI Workflow
# Coordinates ingestion, vector indexing, and SOW generation

import logging
from typing import Any, Dict, Iterable, List, Optional

from src.services.document_service import DocumentProcessor
from src.services.sow_service import SOWGenerator
from src.services.vector_search_service import VectorSearchService

logger = logging.getLogger(__name__)


class WorkflowPipeline:
    """High-level orchestrator for the Databricks AI Workflow."""

    def __init__(
        self,
        document_service: DocumentProcessor,
        vector_service: VectorSearchService,
        sow_service: SOWGenerator,
        max_retries: int = 3,
    ) -> None:
        self.document_service = document_service
        self.vector_service = vector_service
        self.sow_service = sow_service
        self.max_retries = max_retries

    def run_document_ingestion(self, files: Iterable[str], persist: bool = True, index: bool = True) -> List[Dict[str, Any]]:
        file_list = list(files)
        logger.info("Starting document ingestion for %s files", len(file_list))
        chunks = self.document_service.ingest_files(file_list)
        if persist:
            self._with_retry(lambda: self.document_service.save_to_unity_catalog(chunks))
        if index:
            self._with_retry(lambda: self.vector_service.upsert(chunks))
        return chunks

    def generate_statement_of_work(
        self,
        project_details: Dict[str, Any],
        requirements: List[str],
        constraints: Optional[List[str]] = None,
        similar_context: Optional[List[Dict[str, Any]]] = None,
        tone: str = "professional",
        persist: bool = False,
    ) -> str:
        snippets = [item.get("metadata", {}).get("content", item.get("content", "")) for item in similar_context or []]
        sow = self._with_retry(
            lambda: self.sow_service.generate_sow(project_details, requirements, constraints, snippets, tone)
        )
        if persist:
            project_id = str(project_details.get("project_id")) if project_details else "default"
            self._with_retry(lambda: self.sow_service.save_sow(sow, project_id, metadata=project_details))
        return sow

    def find_similar(self, query: str, k: int = 5) -> List[Dict[str, Any]]:
        return self._with_retry(lambda: self.vector_service.similarity_search(query, k))

    def _with_retry(self, func):
        attempts = 0
        last_error: Optional[Exception] = None
        while attempts < self.max_retries:
            try:
                return func()
            except Exception as exc:  # noqa: BLE001
                attempts += 1
                last_error = exc
                logger.warning("Attempt %s/%s failed: %s", attempts, self.max_retries, exc)
        if last_error:
            raise last_error
        raise RuntimeError("Operation failed with no attempts executed")
