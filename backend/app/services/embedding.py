import hashlib
import math
from typing import List, Optional

import importlib

from backend.app.core.config import settings


class EmbeddingService:
    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None, dim: Optional[int] = None) -> None:
        self.api_key = api_key or settings.openai_api_key
        self.model = model or settings.embedding_model
        self.dim = dim or settings.embedding_dim
        self.client = self._get_openai_client()

    def embed(self, text: str) -> List[float]:
        normalized = text.strip()
        if not normalized:
            return [0.0] * self.dim

        if self.client:
            response = self.client.embeddings.create(model=self.model, input=normalized)
            return response.data[0].embedding

        vector = [0.0 for _ in range(self.dim)]
        tokens = normalized.lower().split(" ")
        for token in tokens:
            digest = hashlib.sha256(token.encode("utf-8")).digest()
            for i in range(self.dim):
                vector[i] += digest[i % len(digest)] / 255.0
        norm = math.sqrt(sum(value * value for value in vector))
        if norm == 0.0:
            return vector
        return [value / norm for value in vector]

    def _get_openai_client(self):
        if not self.api_key:
            return None
        spec = importlib.util.find_spec("openai")
        if not spec:
            return None
        openai_module = importlib.import_module("openai")
        return openai_module.OpenAI(api_key=self.api_key)
