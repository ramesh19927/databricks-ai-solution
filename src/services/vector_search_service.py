# Vector Search Service for Databricks AI Workflow
# Connects to Databricks Vector Search and performs similarity lookups

import hashlib
import json
import logging
import math
from typing import Any, Dict, Iterable, List, Optional

import urllib.error
import urllib.request
import importlib

logger = logging.getLogger(__name__)


class VectorSearchService:
    """Manage vector indexes and similarity search operations."""

    def __init__(
        self,
        databricks_host: Optional[str],
        token: Optional[str],
        index_name: str,
        endpoint_name: Optional[str] = None,
        openai_api_key: Optional[str] = None,
        embedding_model: str = "text-embedding-3-small",
        local_embedding_dim: int = 384,
    ) -> None:
        self.databricks_host = databricks_host.rstrip("/") if databricks_host else None
        self.token = token
        self.index_name = index_name
        self.endpoint_name = endpoint_name
        self.embedding_model = embedding_model
        self.local_embedding_dim = local_embedding_dim
        self.client = self._create_openai_client(openai_api_key)

    def ensure_index(self, dimension: int) -> None:
        """Create the vector search index if it does not exist."""
        if not (self.databricks_host and self.token and self.endpoint_name):
            logger.warning("Vector Search configuration missing; skipping index creation")
            return

        payload = {
            "name": self.index_name,
            "endpoint_name": self.endpoint_name,
            "type": "basic",
            "config": {"vector_dimension": dimension},
        }
        self._request("POST", "/api/2.0/ai/vector-search/indexes", json_payload=payload)
        logger.info("Ensured vector index %s exists", self.index_name)

    def upsert(self, chunks: Iterable[Dict[str, Any]]) -> None:
        """Embed and upsert chunks into vector search."""
        chunk_list = list(chunks)
        if not chunk_list:
            logger.info("No chunks provided for upsert")
            return

        vectors = []
        for chunk in chunk_list:
            embedding = self.embed(chunk.get("content", ""))
            vectors.append(
                {
                    "id": f"{chunk.get('file_name')}::{chunk.get('chunk_id')}",
                    "values": embedding,
                    "metadata": chunk,
                }
            )

        if not (self.databricks_host and self.token and self.endpoint_name):
            logger.warning("Vector Search not configured; using local mode only")
            return

        payload = {"index_name": self.index_name, "vectors": vectors}
        self._request("POST", "/api/2.0/ai/vector-search/indexes/upsert", json_payload=payload)
        logger.info("Upserted %s vectors to %s", len(vectors), self.index_name)

    def similarity_search(self, query: str, k: int = 5) -> List[Dict[str, Any]]:
        embedding = self.embed(query)
        if not (self.databricks_host and self.token and self.endpoint_name):
            logger.warning("Vector Search not configured; returning empty results")
            return []

        payload = {
            "index_name": self.index_name,
            "query_vector": embedding,
            "k": k,
        }
        response = self._request(
            "POST", "/api/2.0/ai/vector-search/indexes/query", json_payload=payload
        )
        return response.get("results", []) if isinstance(response, dict) else []

    def embed(self, text: str) -> List[float]:
        sanitized = text.strip()
        if not sanitized:
            return [0.0] * self.local_embedding_dim

        if self.client:
            response = self.client.embeddings.create(model=self.embedding_model, input=sanitized)
            return response.data[0].embedding

        # Local deterministic embedding as a fallback
        vector = [0.0 for _ in range(self.local_embedding_dim)]
        tokens = sanitized.lower().split(" ")
        for token in tokens:
            digest = hashlib.sha256(token.encode("utf-8")).digest()
            for i in range(self.local_embedding_dim):
                vector[i] += digest[i % len(digest)] / 255.0
        norm = math.sqrt(sum(value * value for value in vector))
        if norm == 0.0:
            return vector
        return [value / norm for value in vector]

    def _request(
        self,
        method: str,
        path: str,
        json_payload: Optional[Dict[str, Any]] = None,
    ) -> Any:
        if not (self.databricks_host and self.token):
            raise RuntimeError("Databricks configuration is missing")

        url = f"{self.databricks_host}{path}"
        headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
        }
        data = json.dumps(json_payload).encode("utf-8") if json_payload else None
        req = urllib.request.Request(url, data=data, headers=headers, method=method)
        try:
            with urllib.request.urlopen(req, timeout=60) as response:
                body = response.read().decode()
        except urllib.error.HTTPError as exc:  # noqa: BLE001
            raise RuntimeError(f"Vector search request failed: {exc.reason}") from exc
        if not body:
            return None
        try:
            return json.loads(body)
        except json.JSONDecodeError:
            return body

    def _create_openai_client(self, api_key: Optional[str]):
        if not api_key:
            return None
        spec = importlib.util.find_spec("openai")
        if not spec:
            logger.warning("openai package not installed; using local embeddings")
            return None
        openai_module = importlib.import_module("openai")
        return openai_module.OpenAI(api_key=api_key)
