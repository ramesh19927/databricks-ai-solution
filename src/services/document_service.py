# Document Service for Databricks AI Workflow
# Handles ingestion and processing of customer documents (PDF, DOCX, TXT, CSV)

import csv
import json
import logging
import re
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

logger = logging.getLogger(__name__)


class DocumentProcessor:
    """Process and persist documents for downstream AI workflows."""

    def __init__(
        self,
        databricks_host: Optional[str],
        token: Optional[str],
        catalog: Optional[str] = None,
        schema: Optional[str] = None,
        table: str = "documents",
        warehouse_id: Optional[str] = None,
        chunk_size: int = 800,
        chunk_overlap: int = 120,
    ) -> None:
        if chunk_overlap >= chunk_size:
            raise ValueError("chunk_overlap must be smaller than chunk_size")
        self.databricks_host = databricks_host.rstrip("/") if databricks_host else None
        self.token = token
        self.catalog = catalog
        self.schema = schema
        self.table = table
        self.warehouse_id = warehouse_id
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.supported_formats = {".pdf", ".docx", ".txt", ".csv"}

    def process_file(self, file_path: str) -> Dict[str, Any]:
        """Process a single file and extract text."""
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        file_ext = path.suffix.lower()
        if file_ext not in self.supported_formats:
            raise ValueError(f"Unsupported file format: {file_ext}")

        logger.info("Processing file %s", path.name)
        if file_ext == ".pdf":
            return self._process_pdf(path)
        if file_ext == ".docx":
            return self._process_docx(path)
        if file_ext == ".txt":
            return self._process_txt(path)
        return self._process_csv(path)

    def _process_pdf(self, path: Path) -> Dict[str, Any]:
        from PyPDF2 import PdfReader

        content: List[str] = []
        with path.open("rb") as file:
            reader = PdfReader(file)
            for idx, page in enumerate(reader.pages):
                text = page.extract_text() or ""
                content.append(text.strip())
                logger.debug("Extracted page %s with %s characters", idx + 1, len(text))

        full_text = "\n".join(content)
        return {
            "file_path": str(path),
            "content": full_text,
            "page_count": len(content),
            "format": "pdf",
            "file_name": path.name,
        }

    def _process_docx(self, path: Path) -> Dict[str, Any]:
        from docx import Document

        doc = Document(path)
        paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
        full_text = "\n".join(paragraphs)
        return {
            "file_path": str(path),
            "content": full_text,
            "paragraphs": len(paragraphs),
            "format": "docx",
            "file_name": path.name,
        }

    def _process_txt(self, path: Path) -> Dict[str, Any]:
        text = path.read_text(encoding="utf-8", errors="ignore")
        return {
            "file_path": str(path),
            "content": text,
            "format": "txt",
            "file_name": path.name,
        }

    def _process_csv(self, path: Path) -> Dict[str, Any]:
        text_rows: List[str] = []
        with path.open("r", encoding="utf-8", errors="ignore") as handle:
            reader = csv.reader(handle)
            for row in reader:
                text_rows.append(", ".join(row))
        csv_text = "\n".join(text_rows)
        return {
            "file_path": str(path),
            "content": csv_text,
            "rows": len(text_rows),
            "format": "csv",
            "file_name": path.name,
        }

    def chunk_text(self, text: str) -> List[str]:
        """Chunk text into overlapping windows for embeddings."""
        sanitized = re.sub(r"\s+", " ", text).strip()
        if not sanitized:
            return []

        words = sanitized.split(" ")
        chunks: List[str] = []
        start = 0
        while start < len(words):
            end = min(start + self.chunk_size, len(words))
            chunk = " ".join(words[start:end]).strip()
            if chunk:
                chunks.append(chunk)
            start = end - self.chunk_overlap
            if start < 0:
                start = 0
            if end == len(words):
                break
        return chunks

    def build_chunks(self, file_record: Dict[str, Any]) -> List[Dict[str, Any]]:
        chunks = []
        for idx, chunk in enumerate(self.chunk_text(file_record.get("content", ""))):
            chunks.append(
                {
                    "chunk_id": idx,
                    "content": chunk,
                    "file_name": file_record.get("file_name"),
                    "format": file_record.get("format"),
                    "metadata": {
                        "file_path": file_record.get("file_path"),
                        "page_count": str(file_record.get("page_count", "")),
                        "rows": str(file_record.get("rows", "")),
                    },
                }
            )
        return chunks

    def ingest_files(self, file_paths: Iterable[str]) -> List[Dict[str, Any]]:
        """Process multiple files and return chunked content."""
        documents: List[Dict[str, Any]] = []
        for file_path in file_paths:
            try:
                record = self.process_file(file_path)
                documents.extend(self.build_chunks(record))
            except Exception as exc:  # noqa: BLE001
                logger.exception("Failed to process %s: %s", file_path, exc)
        return documents

    def save_to_unity_catalog(self, chunks: List[Dict[str, Any]]) -> bool:
        """Persist chunked text to Unity Catalog using SQL warehouses."""
        if not (self.databricks_host and self.token and self.warehouse_id):
            logger.warning("Unity Catalog not configured; skipping persistence")
            return False
        if not chunks:
            logger.info("No chunks to persist")
            return True

        table_name = self._qualified_table_name()
        create_sql = (
            f"CREATE TABLE IF NOT EXISTS {table_name} "
            "(file_name STRING, chunk_id INT, content STRING, format STRING, metadata MAP<STRING, STRING>)"
        )
        self._execute_sql(create_sql)

        for chunk in chunks:
            metadata_json = json.dumps(chunk.get("metadata", {}))
            insert_sql = (
                f"INSERT INTO {table_name} (file_name, chunk_id, content, format, metadata) "
                "VALUES (:file_name, :chunk_id, :content, :format, from_json(:metadata, 'MAP<STRING, STRING>'))"
            )
            params = {
                "file_name": chunk.get("file_name"),
                "chunk_id": chunk.get("chunk_id"),
                "content": chunk.get("content"),
                "format": chunk.get("format"),
                "metadata": metadata_json,
            }
            self._execute_sql(insert_sql, params=params)
        logger.info("Persisted %s chunks to %s", len(chunks), table_name)
        return True

    def _qualified_table_name(self) -> str:
        if self.catalog and self.schema:
            return f"{self.catalog}.{self.schema}.{self.table}"
        if self.schema:
            return f"{self.schema}.{self.table}"
        return self.table

    def _execute_sql(self, statement: str, params: Optional[Dict[str, Any]] = None) -> None:
        if not (self.databricks_host and self.token and self.warehouse_id):
            raise RuntimeError("Databricks SQL configuration is missing")

        url = f"{self.databricks_host}/api/2.0/sql/statements"
        headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
        }
        payload: Dict[str, Any] = {"statement": statement, "warehouse_id": self.warehouse_id}
        if params:
            payload["parameters"] = [{"name": key, "value": value} for key, value in params.items()]

        response = self._http_request("POST", url, headers, payload)
        statement_id = response.get("statement_id")
        if not statement_id:
            raise RuntimeError("Failed to submit statement to Databricks SQL")

        self._poll_statement(statement_id, headers)

    def _poll_statement(self, statement_id: str, headers: Dict[str, str]) -> None:
        status_url = f"{self.databricks_host}/api/2.0/sql/statements/{statement_id}"
        start = time.time()
        while True:
            result = self._http_request("GET", status_url, headers)
            status = result.get("status", {}).get("state")
            if status in {"PENDING", "RUNNING", "QUEUED"}:
                if time.time() - start > 120:
                    raise TimeoutError("SQL execution timed out")
                time.sleep(1)
                continue
            if status == "FAILED":
                error = result.get("status", {}).get("error", {})
                raise RuntimeError(f"SQL execution failed: {error}")
            return

    def _http_request(
        self, method: str, url: str, headers: Dict[str, str], payload: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        data = json.dumps(payload).encode("utf-8") if payload else None
        req = urllib.request.Request(url, data=data, headers=headers, method=method)
        try:
            with urllib.request.urlopen(req, timeout=30) as response:
                body = response.read().decode()
        except urllib.error.HTTPError as exc:  # noqa: BLE001
            raise RuntimeError(f"HTTP request failed: {exc.reason}") from exc
        if not body:
            return {}
        try:
            return json.loads(body)
        except json.JSONDecodeError:
            return {"raw": body}
