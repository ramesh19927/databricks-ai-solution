# SOW Service for Databricks AI Workflow
# Generates Statements of Work using LLMs and templates

import datetime as dt
import json
import logging
import time
from textwrap import dedent
from typing import Any, Dict, List, Optional

import urllib.error
import urllib.request
import importlib

logger = logging.getLogger(__name__)


class SOWGenerator:
    """Generate Statements of Work based on project inputs and retrieved context."""

    def __init__(
        self,
        openai_api_key: Optional[str] = None,
        model: str = "gpt-4o-mini",
        databricks_host: Optional[str] = None,
        token: Optional[str] = None,
        catalog: Optional[str] = None,
        schema: Optional[str] = None,
        table: str = "sow_documents",
        warehouse_id: Optional[str] = None,
    ) -> None:
        self.client = self._create_openai_client(openai_api_key)
        self.model = model
        self.databricks_host = databricks_host.rstrip("/") if databricks_host else None
        self.token = token
        self.catalog = catalog
        self.schema = schema
        self.table = table
        self.warehouse_id = warehouse_id

    def generate_sow(
        self,
        project_details: Dict[str, Any],
        requirements: List[str],
        constraints: Optional[List[str]] = None,
        context_snippets: Optional[List[str]] = None,
        tone: str = "professional",
    ) -> str:
        prompt = self._build_prompt(project_details, requirements, constraints, context_snippets, tone)

        if self.client:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are an expert project manager crafting SOWs."},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.2,
            )
            return response.choices[0].message.content or ""

        logger.warning("OpenAI not configured; returning templated SOW")
        return prompt

    def save_sow(self, sow_text: str, project_id: str, metadata: Optional[Dict[str, Any]] = None) -> bool:
        if not (self.databricks_host and self.token and self.warehouse_id):
            logger.warning("Unity Catalog not configured; skipping SOW persistence")
            return False

        metadata = metadata or {}
        timestamp = dt.datetime.utcnow().isoformat()
        statement = (
            f"CREATE TABLE IF NOT EXISTS {self._qualified_table_name()} "
            "(project_id STRING, created_at TIMESTAMP, sow_text STRING, metadata MAP<STRING, STRING>)"
        )
        self._execute_sql(statement)

        insert_sql = (
            f"INSERT INTO {self._qualified_table_name()} (project_id, created_at, sow_text, metadata) "
            "VALUES (:project_id, current_timestamp(), :sow_text, from_json(:metadata, 'MAP<STRING, STRING>'))"
        )
        params = {
            "project_id": project_id,
            "sow_text": sow_text,
            "metadata": json.dumps({"created_at": timestamp, **metadata}),
        }
        self._execute_sql(insert_sql, params=params)
        logger.info("Saved SOW for project %s", project_id)
        return True

    def _qualified_table_name(self) -> str:
        if self.catalog and self.schema:
            return f"{self.catalog}.{self.schema}.{self.table}"
        if self.schema:
            return f"{self.schema}.{self.table}"
        return self.table

    def _build_prompt(
        self,
        project_details: Dict[str, Any],
        requirements: List[str],
        constraints: Optional[List[str]],
        context_snippets: Optional[List[str]],
        tone: str,
    ) -> str:
        scope = "\n- ".join(requirements)
        constraint_text = "\n- ".join(constraints or []) or "None provided"
        context_text = "\n---\n".join(context_snippets or []) or "No context retrieved"
        return dedent(
            f"""
            Create a Statement of Work in a {tone} tone.

            Project Details: {project_details}
            Requirements:\n- {scope}
            Constraints:\n- {constraint_text}
            Context Snippets:\n{context_text}

            Include milestones, deliverables, acceptance criteria, and success metrics.
            Provide a concise executive summary followed by detailed sections.
            """
        ).strip()

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
        while True:
            result = self._http_request("GET", status_url, headers)
            state = result.get("status", {}).get("state")
            if state in {"PENDING", "RUNNING", "QUEUED"}:
                time.sleep(1)
                continue
            if state == "FAILED":
                raise RuntimeError(f"SQL execution failed: {result}")
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

    def _create_openai_client(self, api_key: Optional[str]):
        if not api_key:
            return None
        spec = importlib.util.find_spec("openai")
        if not spec:
            logger.warning("openai package not installed; skipping client creation")
            return None
        openai_module = importlib.import_module("openai")
        return openai_module.OpenAI(api_key=api_key)
